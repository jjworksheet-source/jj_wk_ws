"""
Spiral Learning System - Streamlit Version
Integration with Google Sheets API, PDF generation and AI functions
"""

# ==================== Import necessary packages ====================
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from reportlab.lib.pagesizes import A4, letter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.units import cm, mm
import requests
import json
import os
import tempfile
import zipfile
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import time
from io import BytesIO

# ==================== Page configuration ====================
st.set_page_config(
    page_title="Spiral Learning System",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== Initialize functions ====================
@st.cache_resource
def init_google_sheets():
    """Initialize Google Sheets connection"""
    try:
        # Read service account information from Streamlit Secrets
        service_account_info = {
            "type": st.secrets["gcp_service_account"]["type"],
            "project_id": st.secrets["gcp_service_account"]["project_id"],
            "private_key_id": st.secrets["gcp_service_account"]["private_key_id"],
            "private_key": st.secrets["gcp_service_account"]["private_key"].replace('\\n', '\n'),
            "client_email": st.secrets["gcp_service_account"]["client_email"],
            "client_id": st.secrets["gcp_service_account"]["client_id"],
            "auth_uri": st.secrets["gcp_service_account"]["auth_uri"],
            "token_uri": st.secrets["gcp_service_account"]["token_uri"],
            "auth_provider_x509_cert_url": st.secrets["gcp_service_account"]["auth_provider_x509_cert_url"],
            "client_x509_cert_url": st.secrets["gcp_service_account"]["client_x509_cert_url"]
        }
        
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        creds = Credentials.from_service_account_info(service_account_info, scopes=scopes)
        client = gspread.authorize(creds)
        
        # Read spreadsheet ID
        spreadsheet_id = st.secrets["app_config"]["spreadsheet_id"]
        spreadsheet = client.open_by_key(spreadsheet_id)
        
        return {
            "client": client,
            "spreadsheet": spreadsheet,
            "status": "connected"
        }
    except Exception as e:
        st.error(f"Google Sheets connection failed: {str(e)}")
        return {"status": "error", "message": str(e)}

@st.cache_resource
def init_pdf_generator():
    """Initialize PDF generator"""
    try:
        # Try to register KaiTi font
        font_path = "simkai.ttf"
        
        # Check if font file exists
        if os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont('KaiTi', font_path))
            return {"font_name": "KaiTi", "status": "success"}
        else:
            return {"font_name": "Helvetica", "status": "warning"}
    except Exception as e:
        return {"font_name": "Helvetica", "status": "error"}

# ==================== Google Sheets operations class ====================
class GoogleSheetsManager:
    """Google Sheets management class"""
    
    def __init__(self):
        self.connection = init_google_sheets()
        self.spreadsheet = self.connection.get("spreadsheet") if self.connection["status"] == "connected" else None
    
    def get_sheet_data(self, sheet_name: str) -> pd.DataFrame:
        """Read specified sheet as DataFrame"""
        if not self.spreadsheet:
            return pd.DataFrame()
        
        try:
            worksheet = self.spreadsheet.worksheet(sheet_name)
            data = worksheet.get_all_values()
            
            if data:
                # First row as headers
                headers = data[0]
                rows = data[1:] if len(data) > 1 else []
                df = pd.DataFrame(rows, columns=headers)
                return df
            return pd.DataFrame()
        except Exception as e:
            st.warning(f"Read {sheet_name} failed: {str(e)}")
            return pd.DataFrame()
    
    def write_to_sheet(self, sheet_name: str, data: List[List], clear: bool = True):
        """Write data to specified sheet"""
        if not self.spreadsheet:
            return False
        
        try:
            worksheet = self.spreadsheet.worksheet(sheet_name)
            
            if clear:
                worksheet.clear()
            
            if data:
                worksheet.update(data, value_input_option='USER_ENTERED')
            
            return True
        except Exception as e:
            st.error(f"Write to {sheet_name} failed: {str(e)}")
            return False
    
    def append_to_sheet(self, sheet_name: str, data: List[List]):
        """Append data to specified sheet"""
        if not self.spreadsheet:
            return False
        
        try:
            worksheet = self.spreadsheet.worksheet(sheet_name)
            worksheet.append_rows(data, value_input_option='USER_ENTERED')
            return True
        except Exception as e:
            st.error(f"Append to {sheet_name} failed: {str(e)}")
            return False
    
    def update_cell(self, sheet_name: str, cell: str, value):
        """Update specified cell"""
        if not self.spreadsheet:
            return False
        
        try:
            worksheet = self.spreadsheet.worksheet(sheet_name)
            worksheet.update(cell, value)
            return True
        except Exception as e:
            st.error(f"Update cell failed: {str(e)}")
            return False
    
    def get_all_sheet_names(self) -> List[str]:
        """Get all sheet names"""
        if not self.spreadsheet:
            return []
        
        try:
            worksheets = self.spreadsheet.worksheets()
            return [ws.title for ws in worksheets]
        except:
            return []

# ==================== AI functions class ====================
class AIProcessor:
    """AI processing class (mimics original GAS AI functions)"""
    
    def __init__(self):
        self.api_key = st.secrets["app_config"].get("deepseek_api_key", "")
        self.ai_icon = "🟨 "
    
    def generate_sentence(self, word: str) -> str:
        """Generate sentence (corresponds to GAS generateSentenceByAI)"""
        if not self.api_key:
            return f"{self.ai_icon}AI API key not set"
        
        url = "https://api.deepseek.com/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        prompt = f"請用「{word}」造一個適合香港小學生的句子。句子中必須包含「{word}」。請直接回傳句子，不要有其他文字。"
        
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "你是一位資深的香港小學中文科老師。請使用繁體中文。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                result = response.json()
                if result.get("choices") and len(result["choices"]) > 0:
                    content = result["choices"][0]["message"]["content"].strip()
                    return f"{self.ai_icon}{content}"
            return f"{self.ai_icon}AI generation failed"
        except Exception as e:
            return f"{self.ai_icon}AI error: {str(e)}"
    
    def generate_question(self, word: str, sentence: str, question_type: str) -> Dict:
        """Generate question (corresponds to GAS callDeepSeekForQuestion)"""
        if not self.api_key:
            return {"question": "AI API key not set", "answer": ""}
        
        url = "https://api.deepseek.com/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Generate different prompts based on question type
        prompts = {
            "重組句子": f"""
            任務：請根據句子「{sentence}」和關鍵詞「{word}」，製作一道「重組句子」題目。
            要求：
            1. 請將句子拆解為 **6 到 10 個** 短語區塊
            2. **長度限制**：每個區塊盡量控制在 **2 到 5 個字**
            3. **標點符號保留**：逗號必須保留，可以附著在詞上或獨立成區塊
            4. 區塊之間用 ' / ' 分隔，順序打亂
            回傳格式：JSON 物件 {{"question": "...", "answer": "..."}}
            """,
            "標點符號": f"""
            任務：請根據句子「{sentence}」，製作一道「標點符號」題目。
            要求：移除所有標點符號作為題目，答案為包含正確標點的完整句子
            回傳格式：JSON 物件 {{"question": "...", "answer": "..."}}
            """,
            "反義詞": f"""
            任務：請根據句子「{sentence}」和關鍵詞「{word}」，製作一道「反義詞」題目。
            要求：題目顯示句子並要求寫出詞語的反義詞
            回傳格式：JSON 物件 {{"question": "...", "answer": "..."}}
            """,
            "同義詞": f"""
            任務：請根據句子「{sentence}」和關鍵詞「{word}」，製作一道「同義詞」題目。
            要求：題目顯示句子並要求寫出詞語的近義詞
            回傳格式：JSON 物件 {{"question": "...", "answer": "..."}}
            """,
            "造句": f"""
            任務：請根據詞語「{word}」，製作一道「造句」題目。
            要求：請學生用該詞語造句
            回傳格式：JSON 物件 {{"question": "...", "answer": "..."}}
            """,
            "續寫句子": f"""
            任務：請根據句子「{sentence}」，製作一道「續寫句子」題目。
            要求：給出句子開頭，請學生續寫完整句子
            回傳格式：JSON 物件 {{"question": "...", "answer": "..."}}
            """,
            "詞辨": f"""
            任務：請根據詞語「{word}」，製作一道「詞辨」題目。
            要求：針對詞語找兩個形近或音近的干擾選項，製作選擇題
            回傳格式：JSON 物件 {{"question": "...", "answer": "..."}}
            """
        }
        
        prompt = prompts.get(question_type, f"請製作關於「{word}」的{question_type}題目")
        
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": "你是一位資深的香港小學中文科老師。請使用繁體中文。請務必以 JSON 格式回傳。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "response_format": {"type": "json_object"}
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                result = response.json()
                if result.get("choices") and len(result["choices"]) > 0:
                    content = result["choices"][0]["message"]["content"].strip()
                    return json.loads(content)
            return {"question": f"{self.ai_icon}AI generation failed", "answer": ""}
        except Exception as e:
            return {"question": f"{self.ai_icon}AI error: {str(e)}", "answer": ""}

# ==================== Decision processing class ====================
class DecisionProcessor:
    """Decision processing class (corresponds to GAS distribution logic)"""
    
    def __init__(self, sheets_manager):
        self.sm = sheets_manager
        self.ai = AIProcessor()
    
    def import_new_words(self):
        """Import new words function (corresponds to GAS importNewWordsFromForm)"""
        st.info("Starting import of new words...")
        
        # Read related sheets
        form_df = self.sm.get_sheet_data("Form responses 1")
        p2_tm_df = self.sm.get_sheet_data("P2_TM")
        review_df = self.sm.get_sheet_data("Review")
        
        if form_df.empty:
            st.warning("Form responses 1 sheet is empty")
            return 0
        
        # Build word lookup table
        word_to_sentence = {}
        if not p2_tm_df.empty and "詞語" in p2_tm_df.columns and "句子" in p2_tm_df.columns:
            for _, row in p2_tm_df.iterrows():
                word_to_sentence[str(row["詞語"]).strip()] = row["句子"]
        
        new_rows = []
        updated_form_rows = []
        
        # Process form data
        for idx, row in form_df.iterrows():
            # Check status column
            status_col = None
            for col in form_df.columns:
                if "status" in col.lower() or "狀態" in col:
                    status_col = col
                    break
            
            if status_col and row.get(status_col) != "Done":
                # Get words column
                words_col = None
                for col in form_df.columns:
                    if "word" in col.lower() or "詞語" in col or "詞彙" in col:
                        words_col = col
                        break
                
                if words_col and row.get(words_col):
                    raw_words = str(row[words_col])
                    # Split words
                    words = [w.strip() for w in raw_words.split(",") if w.strip()]
                    
                    for word in words:
                        # Find sentence
                        sentence = ""
                        if word in word_to_sentence:
                            sentence = word_to_sentence[word]
                        else:
                            # Use AI to generate sentence
                            sentence = self.ai.generate_sentence(word)
                        
                        # Prepare Review data
                        new_rows.append([
                            row.get("Timestamp", datetime.now().strftime("%Y/%m/%d %H:%M")),
                            row.get("School", row.get("學校", "")),
                            word,
                            sentence,
                            "",  # Next week question type
                            "",  # Next week question
                            "",  # Next week answer
                            "待處理"  # Decision
                        ])
                    
                    # Mark as processed
                    updated_form_rows.append(idx)
        
        # Write to Review sheet
        if new_rows:
            # Prepare header row
            headers = ["時間戳記", "學校", "詞語", "句子", "下週題型", "下週題目", "下週答案", "決策"]
            all_data = [headers] + new_rows
            
            # Write or append to Review
            if review_df.empty:
                success = self.sm.write_to_sheet("Review", all_data)
            else:
                success = self.sm.append_to_sheet("Review", new_rows)
            
            if success:
                # Update Form status
                for idx in updated_form_rows:
                    cell_addr = f"D{idx+2}"  # Assuming status is in column D
                    self.sm.update_cell("Form responses 1", cell_addr, "Done")
                
                st.success(f"✅ Successfully imported {len(new_rows)} new words!")
                return len(new_rows)
        
        st.info("No new words to import")
        return 0
    
    def generate_next_week_questions(self):
        """Generate next week questions (corresponds to GAS generateNextWeekContent)"""
        st.info("Starting generation of next week questions...")
        
        review_df = self.sm.get_sheet_data("Review")
        
        if review_df.empty:
            st.warning("Review sheet is empty")
            return 0
        
        # Filter rows that need processing
        mask = (
            review_df["詞語"].notna() &
            review_df["句子"].notna() &
            review_df["下週題型"].notna() &
            (review_df["下週題目"].isna() | (review_df["下週題目"] == "")) &
            (~review_df["句子"].astype(str).str.contains(self.ai.ai_icon))
        )
        
        to_process = review_df[mask]
        
        if to_process.empty:
            st.info("No items need question generation")
            return 0
        
        processed_count = 0
        
        # Progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for idx, (_, row) in enumerate(to_process.iterrows()):
            status_text.text(f"Processing: {row['詞語']} ({idx+1}/{len(to_process)})")
            
            # Generate question
            result = self.ai.generate_question(
                row["詞語"], 
                row["句子"], 
                row["下週題型"]
            )
            
            if result:
                # Find corresponding row number
                original_idx = review_df.index[review_df["詞語"] == row["詞語"]].tolist()
                if original_idx:
                    row_num = original_idx[0] + 2  # +1 for header, +1 for zero-based index
                    
                    # Update question and answer
                    self.sm.update_cell("Review", f"F{row_num}", f"{self.ai.ai_icon}{result.get('question', '')}")
                    self.sm.update_cell("Review", f"G{row_num}", result.get('answer', ''))
                    
                    processed_count += 1
            
            # Update progress
            progress_bar.progress((idx + 1) / len(to_process))
        
        status_text.empty()
        progress_bar.empty()
        
        if processed_count > 0:
            st.success(f"✅ Successfully generated {processed_count} questions!")
        else:
            st.warning("No questions were successfully generated")
        
        return processed_count
    
    def move_to_standby(self):
        """Move to Standby (corresponds to GAS moveToStandby)"""
        st.info("Starting move to Standby...")
        
        review_df = self.sm.get_sheet_data("Review")
        standby_df = self.sm.get_sheet_data("Standby")
        
        if review_df.empty:
            st.warning("Review sheet is empty")
            return 0
        
        standby_data = []
        rows_to_clear = []
        
        today = datetime.now().strftime("%Y/%m/%d")
        
        for idx, row in review_df.iterrows():
            # Check required fields
            required_fields = ["學校", "詞語", "句子"]
            if not all(row.get(field) for field in required_fields):
                continue
            
            # Check decision
            decision = row.get("決策", "")
            if decision not in ["即用及保留", "保留"]:
                continue
            
            school = row["學校"]
            word = row["詞語"]
            sentence = row["句子"]
            next_type = row.get("下週題型", "")
            next_question = row.get("下週題目", "")
            next_answer = row.get("下週答案", "")
            
            # If question type selected but no question generated, skip
            if next_type and not next_question:
                continue
            
            unique_base = f"{school}_{int(time.time()*1000)}_{idx}"
            
            # Twin 1: This week's fill-in-the-blank
            standby_data.append([
                f"{unique_base}_f",
                school,
                word,
                "填空題",
                sentence,
                word,
                "Ready",
                today
            ])
            
            # Twin 2: Next week's variation
            if next_question:
                standby_data.append([
                    f"{unique_base}_o",
                    school,
                    word,
                    next_type,
                    next_question,
                    next_answer,
                    "Waiting",
                    today
                ])
            
            rows_to_clear.append(idx)
        
        if standby_data:
            # Write to Standby
            headers = ["ID", "學校", "詞語", "題型", "題目", "答案", "狀態", "創建日期"]
            
            if standby_df.empty:
                all_data = [headers] + standby_data
                success = self.sm.write_to_sheet("Standby", all_data)
            else:
                success = self.sm.append_to_sheet("Standby", standby_data)
            
            if success:
                # Clear transferred items from Review sheet
                for idx in rows_to_clear:
                    row_num = idx + 2
                    # Clear columns A-G
                    for col in range(1, 8):
                        self.sm.update_cell("Review", f"{chr(64+col)}{row_num}", "")
                
                st.success(f"✅ Successfully transferred {len(standby_data)} items to Standby!")
                return len(standby_data)
        
        st.info("No items to transfer")
        return 0

# ==================== PDF generation class ====================
class PDFGenerator:
    """PDF generation class"""
    
    def __init__(self):
        pdf_config = init_pdf_generator()
        self.font_name = pdf_config["font_name"]
    
    def create_worksheet(self, data: Dict, output_path: str = None) -> BytesIO:
        """Generate single worksheet"""
        if output_path is None:
            output = BytesIO()
        else:
            output = output_path
        
        # Create document
        doc = SimpleDocTemplate(
            output,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        
        # Styles
        styles = getSampleStyleSheet()
        
        # Custom KaiTi font styles
        if self.font_name == "KaiTi":
            for style_name in ['Normal', 'Title', 'Heading1', 'Heading2']:
                if style_name in styles:
                    styles[style_name].fontName = 'KaiTi'
        
        # Content
        content = []
        
        # Title
        title_style = styles["Title"]
        title_style.alignment = 1  # Center
        content.append(Paragraph("螺旋式學習工作紙", title_style))
        content.append(Spacer(1, 1*cm))
        
        # School information
        if "學校" in data:
            content.append(Paragraph(f"學校：{data['學校']}", styles["Normal"]))
        
        if "時間戳記" in data:
            content.append(Paragraph(f"日期：{data['時間戳記']}", styles["Normal"]))
        
        content.append(Spacer(1, 1*cm))
        
        # Word section
        if "詞語" in data:
            content.append(Paragraph(f"<b>學習詞語：</b>{data['詞語']}", styles["Normal"]))
        
        # Sentence section
        if "句子" in data:
            sentence_text = data['句子'].replace(self.font_name == "KaiTi" and "🟨 " or "", "")
            content.append(Paragraph(f"<b>例句：</b>{sentence_text}", styles["Normal"]))
        
        content.append(Spacer(1, 1.5*cm))
        
        # Question section
        if "下週題型" in data and "下週題目" in data:
            content.append(Paragraph(f"<b>題型：{data['下週題型']}</b>", styles["Heading2"]))
            content.append(Spacer(1, 0.5*cm))
            
            # Clean AI icon
            question_text = data['下週題目'].replace("🟨 ", "")
            content.append(Paragraph(f"<b>題目：</b>{question_text}", styles["Normal"]))
            
            # Answer line
            content.append(Spacer(1, 3*cm))
            content.append(Paragraph("答案：________________________________________________", styles["Normal"]))
        
        # Generate PDF
        doc.build(content)
        
        if isinstance(output, BytesIO):
            output.seek(0)
            return output
        
        return output_path
    
    def generate_weekly_pdfs(self, data_list: List[Dict]) -> BytesIO:
        """Generate ZIP file with multiple worksheets"""
        # Create temporary directory
        temp_dir = tempfile.mkdtemp()
        pdf_files = []
        
        # Generate each worksheet
        for i, data in enumerate(data_list):
            pdf_path = os.path.join(temp_dir, f"worksheet_{i+1}.pdf")
            self.create_worksheet(data, pdf_path)
            pdf_files.append(pdf_path)
        
        # Create ZIP file
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for pdf_file in pdf_files:
                zip_file.write(pdf_file, os.path.basename(pdf_file))
        
        zip_buffer.seek(0)
        
        # Clean up temporary files
        for pdf_file in pdf_files:
            try:
                os.remove(pdf_file)
            except:
                pass
        
        return zip_buffer

# ==================== Streamlit page functions ====================
def show_dashboard(sheets_manager):
    """Show dashboard"""
    st.header("📊 System Dashboard")
    
    # Get all sheet names
    sheet_names = sheets_manager.get_all_sheet_names()
    
    # Display sheet status
    col1, col2, col3 = st.columns(3)
    
    with col1:
        review_df = sheets_manager.get_sheet_data("Review")
        pending_count = len(review_df[review_df["決策"] == "待處理"]) if not review_df.empty and "決策" in review_df.columns else 0
        st.metric("Pending Items", pending_count)
    
    with col2:
        p2_ws_df = sheets_manager.get_sheet_data("P2_WS")
        ws_count = len(p2_ws_df) if not p2_ws_df.empty else 0
        st.metric("Worksheets", ws_count)
    
    with col3:
        p2_tm_df = sheets_manager.get_sheet_data("P2_TM")
        tm_count = len(p2_tm_df) if not p2_tm_df.empty else 0
        st.metric("Question Bank Words", tm_count)
    
    st.markdown("---")
    
    # Display pending items
    st.subheader("📋 Pending Items List")
    
    if not review_df.empty:
        # Filter pending items
        if "決策" in review_df.columns:
            to_process = review_df[review_df["決策"].isin(["", "待處理", "待審批"])]
        else:
            to_process = review_df
        
        if not to_process.empty:
            # Editable data table
            edited_df = st.data_editor(
                to_process.head(50),  # Limit display quantity
                use_container_width=True,
                num_rows="dynamic",
                column_config={
                    "決策": st.column_config.SelectboxColumn(
                        "Decision",
                        options=["", "待處理", "即用及保留", "保留", "待審批"],
                        required=False
                    ),
                    "下週題型": st.column_config.SelectboxColumn(
                        "Next Week Type",
                        options=["", "重組句子", "造句", "標點符號", "反義詞", "同義詞", "續寫句子", "詞辨"],
                        required=False
                    )
                }
            )
            
            # Save button
            if st.button("💾 Save Changes", use_container_width=True):
                # Implement save logic here
                st.success("Changes saved!")
        else:
            st.info("🎉 No pending items!")
    else:
        st.info("Review sheet is empty")
    
    # Quick action buttons
    st.markdown("---")
    st.subheader("⚡ Quick Actions")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📥 Import New Words", use_container_width=True):
            processor = DecisionProcessor(sheets_manager)
            count = processor.import_new_words()
            if count > 0:
                st.rerun()
    
    with col2:
        if st.button("✨ Generate Questions", use_container_width=True):
            processor = DecisionProcessor(sheets_manager)
            count = processor.generate_next_week_questions()
            if count > 0:
                st.rerun()
    
    with col3:
        if st.button("📤 Move to Standby", use_container_width=True):
            processor = DecisionProcessor(sheets_manager)
            count = processor.move_to_standby()
            if count > 0:
                st.rerun()

def show_decision_page(sheets_manager):
    """Show decision processing page"""
    st.header("🔄 Distribution System")
    
    processor = DecisionProcessor(sheets_manager)
    
    # Step-by-step interface
    st.subheader("Step 1: Check Pending Items")
    
    review_df = sheets_manager.get_sheet_data("Review")
    
    if not review_df.empty:
        # Decision distribution
        if "決策" in review_df.columns:
            st.write("**Decision Distribution:**")
            decision_counts = review_df["決策"].value_counts()
            st.bar_chart(decision_counts)
        
        # Filter items needing decision
        need_decision = review_df[review_df["決策"].isin(["", "待處理"])]
        
        if not need_decision.empty:
            st.write(f"**Items needing decision: {len(need_decision)}**")
            
            # Batch decision settings
            st.subheader("Step 2: Batch Decision Settings")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("🏷️ Set All to「即用及保留」", use_container_width=True):
                    # Batch update logic
                    for idx in need_decision.index:
                        row_num = idx + 2
                        sheets_manager.update_cell("Review", f"H{row_num}", "即用及保留")
                    st.success("Batch setting completed!")
                    st.rerun()
            
            with col2:
                if st.button("💾 Set All to「保留」", use_container_width=True):
                    for idx in need_decision.index:
                        row_num = idx + 2
                        sheets_manager.update_cell("Review", f"H{row_num}", "保留")
                    st.success("Batch setting completed!")
                    st.rerun()
            
            with col3:
                if st.button("⏳ Set All to「待審批」", use_container_width=True):
                    for idx in need_decision.index:
                        row_num = idx + 2
                        sheets_manager.update_cell("Review", f"H{row_num}", "待審批")
                    st.success("Batch setting completed!")
                    st.rerun()
        
        # Detailed editing
        st.subheader("Step 3: Detailed Editing")
        
        if st.checkbox("Show Detailed Editing Table"):
            edited_df = st.data_editor(
                review_df.head(100),
                use_container_width=True,
                column_config={
                    "決策": st.column_config.SelectboxColumn(
                        "Decision",
                        options=["", "待處理", "即用及保留", "保留", "待審批"],
                        required=False
                    )
                }
            )
    
    # Execute distribution
    st.markdown("---")
    st.subheader("Step 4: Execute Distribution")
    
    if st.button("🚀 Execute Distribution", type="primary", use_container_width=True):
        with st.spinner("Processing distribution..."):
            # Add more detailed processing logic here
            success_count = processor.move_to_standby()
            
            if success_count > 0:
                st.success(f"✅ Successfully processed {success_count} items!")
                st.rerun()
            else:
                st.info("No items to process")

def show_pdf_generation_page(sheets_manager):
    """Show PDF generation page"""
    st.header("📄 PDF Worksheet Generation")
    
    pdf_gen = PDFGenerator()
    
    # Select data source
    st.subheader("Select Data Source")
    
    source_option = st.radio(
        "Data Source",
        ["P2_WS (Worksheet List)", "Standby (Question Bank)", "Custom Data"],
        horizontal=True
    )
    
    if source_option == "P2_WS (Worksheet List)":
        data_df = sheets_manager.get_sheet_data("P2_WS")
    elif source_option == "Standby (Question Bank)":
        data_df = sheets_manager.get_sheet_data("Standby")
    else:
        data_df = pd.DataFrame()
    
    if not data_df.empty:
        st.success(f"✅ Loaded {len(data_df)} records")
        
        # Filter options
        st.subheader("Filter Conditions")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if "學校" in data_df.columns:
                schools = ["All"] + list(data_df["學校"].unique())
                selected_school = st.selectbox("Select School", schools)
        
        with col2:
            if "題型" in data_df.columns:
                question_types = ["All"] + list(data_df["題型"].unique())
                selected_type = st.selectbox("Select Question Type", question_types)
        
        # Apply filters
        filtered_df = data_df.copy()
        
        if "學校" in data_df.columns and selected_school != "All":
            filtered_df = filtered_df[filter_df["學校"] == selected_school]
        
        if "題型" in data_df.columns and selected_type != "All":
            filtered_df = filtered_df[filter_df["題型"] == selected_type]
        
        # Preview
        st.subheader("Preview Items to Generate")
        st.dataframe(filtered_df.head(20), use_container_width=True)
        
        # PDF settings
        st.subheader("PDF Settings")
        
        col1, col2 = st.columns(2)
        
        with col1:
            page_size = st.selectbox("Paper Size", ["A4", "Letter"])
            include_header = st.checkbox("Include Header", value=True)
        
        with col2:
            font_size = st.slider("Font Size", 10, 16, 12)
            include_answer_key = st.checkbox("Include Answer Key", value=False)
        
        # Generate button
        if st.button("🖨️ Generate PDF Worksheets", type="primary", use_container_width=True):
            if len(filtered_df) > 0:
                with st.spinner("Generating PDF..."):
                    # Convert data format
                    data_list = []
                    for _, row in filtered_df.iterrows():
                        data_dict = row.to_dict()
                        # Rename fields to match PDF generation expectations
                        if "詞語" in data_dict and "題目" in data_dict:
                            data_dict["下週題目"] = data_dict["題目"]
                            data_dict["下週題型"] = data_dict.get("題型", "")
                            data_dict["下週答案"] = data_dict.get("答案", "")
                        
                        data_list.append(data_dict)
                    
                    # Generate PDF
                    if len(data_list) == 1:
                        # Single PDF
                        pdf_bytes = pdf_gen.create_worksheet(data_list[0])
                        st.download_button(
                            label="📥 Download Worksheet",
                            data=pdf_bytes,
                            file_name=f"worksheet_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                            mime="application/pdf"
                        )
                    else:
                        # Multiple PDFs packaged
                        zip_bytes = pdf_gen.generate_weekly_pdfs(data_list)
                        st.download_button(
                            label="📥 Download All Worksheets (ZIP)",
                            data=zip_bytes,
                            file_name=f"worksheets_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                            mime="application/zip"
                        )
                        
                        st.success(f"✅ Generated {len(data_list)} worksheets")
            else:
                st.warning("No data to generate")
    else:
        st.warning("Selected data source is empty or does not exist")
    
    # Quick generation options
    st.markdown("---")
    st.subheader("Quick Generation Options")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 Generate This Week's Worksheets", use_container_width=True):
            # Implement specific logic here
            st.info("This feature is under development...")
    
    with col2:
        if st.button("📅 Generate Next Week's Preview", use_container_width=True):
            st.info("This feature is under development...")

def show_system_settings():
    """Show system settings page"""
    st.header("⚙️ System Settings")
    
    # Connection status
    st.subheader("Connection Status")
    
    sheets_status = init_google_sheets()["status"]
    pdf_status = init_pdf_generator()["status"]
    
    col1, col2 = st.columns(2)
    
    with col1:
        if sheets_status == "connected":
            st.success("✅ Google Sheets connected")
        else:
            st.error("❌ Google Sheets connection failed")
    
    with col2:
        if pdf_status == "success":
            st.success("✅ PDF generator ready")
        elif pdf_status == "warning":
            st.warning("⚠️ PDF generator using default font")
        else:
            st.error("❌ PDF generator initialization failed")
    
    # Spreadsheet information
    st.subheader("Spreadsheet Information")
    
    try:
        spreadsheet_id = st.secrets["app_config"]["spreadsheet_id"]
        st.info(f"Spreadsheet ID: `{spreadsheet_id}`")
        
        # Display available sheets
        sheets_manager = GoogleSheetsManager()
        sheet_names = sheets_manager.get_all_sheet_names()
        
        if sheet_names:
            st.write("Available Sheets:")
            for name in sheet_names:
                st.write(f"- {name}")
    except:
        st.warning("Cannot read spreadsheet information")
    
    # System functions
    st.subheader("System Functions")
    
    if st.button("🔄 Clear Cache", use_container_width=True):
        st.cache_resource.clear()
        st.success("Cache cleared!")
        st.rerun()
    
    if st.button("📊 Refresh Data", use_container_width=True):
        st.rerun()

# ==================== Main function ====================
def main():
    """Main function"""
    
    # Sidebar
    with st.sidebar:
        st.title("📚 Spiral Learning")
        st.markdown("---")
        
        # Navigation menu
        menu_option = st.radio(
            "Main Menu",
            ["📊 Dashboard", "🔄 Distribution", "📄 Generate Worksheets", "⚙️ System Settings"],
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        
        # System status
        st.caption("System Status")
        
        # Initialization check
        sheets_status = init_google_sheets()["status"]
        pdf_status = init_pdf_generator()["status"]
        
        status_emoji = "✅" if sheets_status == "connected" else "❌"
        st.write(f"{status_emoji} Google Sheets")
        
        if pdf_status == "success":
            st.write("✅ KaiTi PDF")
        elif pdf_status == "warning":
            st.write("⚠️ Default Font PDF")
        else:
            st.write("❌ PDF Generation")
        
        st.markdown("---")
        
        # Quick actions
        st.caption("Quick Actions")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔄 Refresh", use_container_width=True):
                st.rerun()
        
        with col2:
            if st.button("📖 Manual", use_container_width=True):
                st.info("System manual under development...")
        
        st.markdown("---")
        
        # Version information
        st.caption("Version v1.0")
        st.caption("Streamlit + Google Sheets Integration System")
    
    # Main content area
    try:
        # Initialize Google Sheets
        sheets_manager = GoogleSheetsManager()
        
        if menu_option == "📊 Dashboard":
            show_dashboard(sheets_manager)
        
        elif menu_option == "🔄 Distribution":
            show_decision_page(sheets_manager)
        
        elif menu_option == "📄 Generate Worksheets":
            show_pdf_generation_page(sheets_manager)
        
        elif menu_option == "⚙️ System Settings":
            show_system_settings()
    
    except Exception as e:
        st.error(f"System error: {str(e)}")
        st.info("Please check system settings and network connection")

# ==================== Run application ====================
if __name__ == "__main__":
    # Check required secrets
    required_secrets = ["gcp_service_account", "app_config"]
    missing_secrets = [s for s in required_secrets if s not in st.secrets]
    
    if missing_secrets:
        st.error(f"Missing required settings: {', '.join(missing_secrets)}")
        st.info("Please set in Streamlit Cloud Secrets:")
        st.code("""
[gcp_service_account]
type = "service_account"
project_id = "your_project_id"
private_key_id = "your_private_key_id"
private_key = "-----BEGIN PRIVATE KEY-----\nyour_private_key\n-----END PRIVATE KEY-----"
client_email = "your_service_account_email"
client_id = "your_client_id"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "your_cert_url"

[app_config]
spreadsheet_id = "your_spreadsheet_id"
deepseek_api_key = "your_deepseek_api_key"
        """)
    else:
        main()
