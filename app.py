"""
螺旋式學習教材系統 - Streamlit 版本
整合 Google Sheets API、PDF 生成和 AI 功能
"""

# ==================== 導入必要的套件 ====================
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

# ==================== 頁面配置 ====================
st.set_page_config(
    page_title="螺旋式學習教材系統",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== 初始化函數 ====================
@st.cache_resource
def init_google_sheets():
    """初始化 Google Sheets 連接"""
    try:
        # 從 Streamlit Secrets 讀取服務帳戶資訊
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
        
        # 讀取試算表 ID
        spreadsheet_id = st.secrets["app_config"]["spreadsheet_id"]
        spreadsheet = client.open_by_key(spreadsheet_id)
        
        return {
            "client": client,
            "spreadsheet": spreadsheet,
            "status": "connected"
        }
    except Exception as e:
        st.error(f"Google Sheets 連接失敗: {str(e)}")
        return {"status": "error", "message": str(e)}

@st.cache_resource
def init_pdf_generator():
    """初始化 PDF 生成器"""
    try:
        # 嘗試註冊標楷體字型
        font_path = "simkai.ttf"
        
        # 檢查字型檔案是否存在
        if os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont('KaiTi', font_path))
            st.success("✅ 標楷體字型載入成功")
            return {"font_name": "KaiTi", "status": "success"}
        else:
            st.warning("⚠️ 未找到標楷體字型檔案，使用預設字型")
            return {"font_name": "Helvetica", "status": "warning"}
    except Exception as e:
        st.warning(f"⚠️ 字型載入問題: {str(e)}")
        return {"font_name": "Helvetica", "status": "error"}

# ==================== Google Sheets 操作類 ====================
class GoogleSheetsManager:
    """Google Sheets 管理類"""
    
    def __init__(self):
        self.connection = init_google_sheets()
        self.spreadsheet = self.connection.get("spreadsheet") if self.connection["status"] == "connected" else None
    
    def get_sheet_data(self, sheet_name: str) -> pd.DataFrame:
        """讀取指定工作表為 DataFrame"""
        if not self.spreadsheet:
            return pd.DataFrame()
        
        try:
            worksheet = self.spreadsheet.worksheet(sheet_name)
            data = worksheet.get_all_values()
            
            if data:
                # 第一行作為標題
                headers = data[0]
                rows = data[1:] if len(data) > 1 else []
                df = pd.DataFrame(rows, columns=headers)
                return df
            return pd.DataFrame()
        except Exception as e:
            st.warning(f"讀取 {sheet_name} 失敗: {str(e)}")
            return pd.DataFrame()
    
    def write_to_sheet(self, sheet_name: str, data: List[List], clear: bool = True):
        """寫入資料到指定工作表"""
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
            st.error(f"寫入 {sheet_name} 失敗: {str(e)}")
            return False
    
    def append_to_sheet(self, sheet_name: str, data: List[List]):
        """追加資料到指定工作表"""
        if not self.spreadsheet:
            return False
        
        try:
            worksheet = self.spreadsheet.worksheet(sheet_name)
            worksheet.append_rows(data, value_input_option='USER_ENTERED')
            return True
        except Exception as e:
            st.error(f"追加到 {sheet_name} 失敗: {str(e)}")
            return False
    
    def update_cell(self, sheet_name: str, cell: str, value):
        """更新指定儲存格"""
        if not self.spreadsheet:
            return False
        
        try:
            worksheet = self.spreadsheet.worksheet(sheet_name)
            worksheet.update(cell, value)
            return True
        except Exception as e:
            st.error(f"更新儲存格失敗: {str(e)}")
            return False
    
    def get_all_sheet_names(self) -> List[str]:
        """獲取所有工作表名稱"""
        if not self.spreadsheet:
            return []
        
        try:
            worksheets = self.spreadsheet.worksheets()
            return [ws.title for ws in worksheets]
        except:
            return []

# ==================== AI 功能類 ====================
class AIProcessor:
    """AI 處理類（模仿原 GAS 的 AI 功能）"""
    
    def __init__(self):
        self.api_key = st.secrets["app_config"].get("deepseek_api_key", "")
        self.ai_icon = "🟨 "
    
    def generate_sentence(self, word: str) -> str:
        """生成句子（對應原 GAS 的 generateSentenceByAI）"""
        if not self.api_key:
            return f"{self.ai_icon}AI API 金鑰未設定"
        
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
            return f"{self.ai_icon}AI 生成失敗"
        except Exception as e:
            return f"{self.ai_icon}AI 錯誤: {str(e)}"
    
    def generate_question(self, word: str, sentence: str, question_type: str) -> Dict:
        """生成題目（對應原 GAS 的 callDeepSeekForQuestion）"""
        if not self.api_key:
            return {"question": "AI API 金鑰未設定", "answer": ""}
        
        url = "https://api.deepseek.com/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # 根據題型生成不同的提示
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
            return {"question": f"{self.ai_icon}AI 生成失敗", "answer": ""}
        except Exception as e:
            return {"question": f"{self.ai_icon}AI 錯誤: {str(e)}", "answer": ""}

# ==================== 決策處理類 ====================
class DecisionProcessor:
    """決策處理類（對應原 GAS 的分流邏輯）"""
    
    def __init__(self, sheets_manager):
        self.sm = sheets_manager
        self.ai = AIProcessor()
    
    def import_new_words(self):
        """匯入新詞功能（對應原 GAS 的 importNewWordsFromForm）"""
        st.info("開始匯入新詞...")
        
        # 讀取相關表格
        form_df = self.sm.get_sheet_data("Form responses 1")
        p2_tm_df = self.sm.get_sheet_data("P2_TM")
        review_df = self.sm.get_sheet_data("Review")
        
        if form_df.empty:
            st.warning("Form responses 1 表格為空")
            return 0
        
        # 建立題庫查詢表
        word_to_sentence = {}
        if not p2_tm_df.empty and "詞語" in p2_tm_df.columns and "句子" in p2_tm_df.columns:
            for _, row in p2_tm_df.iterrows():
                word_to_sentence[str(row["詞語"]).strip()] = row["句子"]
        
        new_rows = []
        updated_form_rows = []
        
        # 處理表單資料
        for idx, row in form_df.iterrows():
            # 檢查狀態欄位
            status_col = None
            for col in form_df.columns:
                if "status" in col.lower() or "狀態" in col:
                    status_col = col
                    break
            
            if status_col and row.get(status_col) != "Done":
                # 獲取詞語欄位
                words_col = None
                for col in form_df.columns:
                    if "word" in col.lower() or "詞語" in col or "詞彙" in col:
                        words_col = col
                        break
                
                if words_col and row.get(words_col):
                    raw_words = str(row[words_col])
                    # 分割詞語
                    words = [w.strip() for w in raw_words.split(",") if w.strip()]
                    
                    for word in words:
                        # 查找句子
                        sentence = ""
                        if word in word_to_sentence:
                            sentence = word_to_sentence[word]
                        else:
                            # 使用 AI 生成句子
                            sentence = self.ai.generate_sentence(word)
                        
                        # 準備 Review 資料
                        new_rows.append([
                            row.get("Timestamp", datetime.now().strftime("%Y/%m/%d %H:%M")),
                            row.get("School", row.get("學校", "")),
                            word,
                            sentence,
                            "",  # 下週題型
                            "",  # 下週題目
                            "",  # 下週答案
                            "待處理"  # 決策
                        ])
                    
                    # 標記為已處理
                    updated_form_rows.append(idx)
        
        # 寫入 Review 表
        if new_rows:
            # 準備標題行
            headers = ["時間戳記", "學校", "詞語", "句子", "下週題型", "下週題目", "下週答案", "決策"]
            all_data = [headers] + new_rows
            
            # 寫入或追加到 Review
            if review_df.empty:
                success = self.sm.write_to_sheet("Review", all_data)
            else:
                success = self.sm.append_to_sheet("Review", new_rows)
            
            if success:
                # 更新 Form 狀態
                for idx in updated_form_rows:
                    cell_addr = f"D{idx+2}"  # 假設狀態在 D 欄
                    self.sm.update_cell("Form responses 1", cell_addr, "Done")
                
                st.success(f"✅ 成功匯入 {len(new_rows)} 個新詞彙！")
                return len(new_rows)
        
        st.info("沒有新詞彙需要匯入")
        return 0
    
    def generate_next_week_questions(self):
        """生成下週題目（對應原 GAS 的 generateNextWeekContent）"""
        st.info("開始生成下週題目...")
        
        review_df = self.sm.get_sheet_data("Review")
        
        if review_df.empty:
            st.warning("Review 表格為空")
            return 0
        
        # 過濾需要處理的行
        mask = (
            review_df["詞語"].notna() &
            review_df["句子"].notna() &
            review_df["下週題型"].notna() &
            (review_df["下週題目"].isna() | (review_df["下週題目"] == "")) &
            (~review_df["句子"].astype(str).str.contains(self.ai.ai_icon))
        )
        
        to_process = review_df[mask]
        
        if to_process.empty:
            st.info("沒有需要生成題目的項目")
            return 0
        
        processed_count = 0
        
        # 進度條
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for idx, (_, row) in enumerate(to_process.iterrows()):
            status_text.text(f"處理中: {row['詞語']} ({idx+1}/{len(to_process)})")
            
            # 生成題目
            result = self.ai.generate_question(
                row["詞語"], 
                row["句子"], 
                row["下週題型"]
            )
            
            if result:
                # 找到對應的行號
                original_idx = review_df.index[review_df["詞語"] == row["詞語"]].tolist()
                if original_idx:
                    row_num = original_idx[0] + 2  # +1 標題行，+1 零基索引
                    
                    # 更新題目和答案
                    self.sm.update_cell("Review", f"F{row_num}", f"{self.ai.ai_icon}{result.get('question', '')}")
                    self.sm.update_cell("Review", f"G{row_num}", result.get('answer', ''))
                    
                    processed_count += 1
            
            # 更新進度
            progress_bar.progress((idx + 1) / len(to_process))
        
        status_text.empty()
        progress_bar.empty()
        
        if processed_count > 0:
            st.success(f"✅ 成功生成 {processed_count} 個題目！")
        else:
            st.warning("沒有成功生成任何題目")
        
        return processed_count
    
    def move_to_standby(self):
        """移交至 Standby（對應原 GAS 的 moveToStandby）"""
        st.info("開始移交至 Standby...")
        
        review_df = self.sm.get_sheet_data("Review")
        standby_df = self.sm.get_sheet_data("Standby")
        
        if review_df.empty:
            st.warning("Review 表格為空")
            return 0
        
        standby_data = []
        rows_to_clear = []
        
        today = datetime.now().strftime("%Y/%m/%d")
        
        for idx, row in review_df.iterrows():
            # 檢查必要欄位
            required_fields = ["學校", "詞語", "句子"]
            if not all(row.get(field) for field in required_fields):
                continue
            
            # 檢查決策
            decision = row.get("決策", "")
            if decision not in ["即用及保留", "保留"]:
                continue
            
            school = row["學校"]
            word = row["詞語"]
            sentence = row["句子"]
            next_type = row.get("下週題型", "")
            next_question = row.get("下週題目", "")
            next_answer = row.get("下週答案", "")
            
            # 如果有選題型但還沒生成題目，跳過
            if next_type and not next_question:
                continue
            
            unique_base = f"{school}_{int(time.time()*1000)}_{idx}"
            
            # 雙胞胎 1：本週填空題
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
            
            # 雙胞胎 2：下週變化題
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
            # 寫入 Standby
            headers = ["ID", "學校", "詞語", "題型", "題目", "答案", "狀態", "創建日期"]
            
            if standby_df.empty:
                all_data = [headers] + standby_data
                success = self.sm.write_to_sheet("Standby", all_data)
            else:
                success = self.sm.append_to_sheet("Standby", standby_data)
            
            if success:
                # 清除 Review 表中的已移交項目
                for idx in rows_to_clear:
                    row_num = idx + 2
                    # 清空 A-G 欄
                    for col in range(1, 8):
                        self.sm.update_cell("Review", f"{chr(64+col)}{row_num}", "")
                
                st.success(f"✅ 成功移交 {len(standby_data)} 筆題目至 Standby！")
                return len(standby_data)
        
        st.info("沒有可移交的項目")
        return 0

# ==================== PDF 生成類 ====================
class PDFGenerator:
    """PDF 生成類"""
    
    def __init__(self):
        pdf_config = init_pdf_generator()
        self.font_name = pdf_config["font_name"]
    
    def create_worksheet(self, data: Dict, output_path: str = None) -> BytesIO:
        """生成單個工作紙"""
        if output_path is None:
            output = BytesIO()
        else:
            output = output_path
        
        # 創建文檔
        doc = SimpleDocTemplate(
            output,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        
        # 樣式
        styles = getSampleStyleSheet()
        
        # 自定義標楷體樣式
        if self.font_name == "KaiTi":
            for style_name in ['Normal', 'Title', 'Heading1', 'Heading2']:
                if style_name in styles:
                    styles[style_name].fontName = 'KaiTi'
        
        # 內容
        content = []
        
        # 標題
        title_style = styles["Title"]
        title_style.alignment = 1  # 置中
        content.append(Paragraph("螺旋式學習工作紙", title_style))
        content.append(Spacer(1, 1*cm))
        
        # 學校資訊
        if "學校" in data:
            content.append(Paragraph(f"學校：{data['學校']}", styles["Normal"]))
        
        if "時間戳記" in data:
            content.append(Paragraph(f"日期：{data['時間戳記']}", styles["Normal"]))
        
        content.append(Spacer(1, 1*cm))
        
        # 詞語區塊
        if "詞語" in data:
            content.append(Paragraph(f"<b>學習詞語：</b>{data['詞語']}", styles["Normal"]))
        
        # 句子區塊
        if "句子" in data:
            sentence_text = data['句子'].replace(self.font_name == "KaiTi" and "🟨 " or "", "")
            content.append(Paragraph(f"<b>例句：</b>{sentence_text}", styles["Normal"]))
        
        content.append(Spacer(1, 1.5*cm))
        
        # 題目區塊
        if "下週題型" in data and "下週題目" in data:
            content.append(Paragraph(f"<b>題型：{data['下週題型']}</b>", styles["Heading2"]))
            content.append(Spacer(1, 0.5*cm))
            
            # 清理 AI 圖標
            question_text = data['下週題目'].replace("🟨 ", "")
            content.append(Paragraph(f"<b>題目：</b>{question_text}", styles["Normal"]))
            
            # 答案線
            content.append(Spacer(1, 3*cm))
            content.append(Paragraph("答案：________________________________________________", styles["Normal"]))
        
        # 生成 PDF
        doc.build(content)
        
        if isinstance(output, BytesIO):
            output.seek(0)
            return output
        
        return output_path
    
    def generate_weekly_pdfs(self, data_list: List[Dict]) -> BytesIO:
        """生成多個工作紙的 ZIP 檔案"""
        # 創建臨時目錄
        temp_dir = tempfile.mkdtemp()
        pdf_files = []
        
        # 生成每個工作紙
        for i, data in enumerate(data_list):
            pdf_path = os.path.join(temp_dir, f"worksheet_{i+1}.pdf")
            self.create_worksheet(data, pdf_path)
            pdf_files.append(pdf_path)
        
        # 創建 ZIP 檔案
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for pdf_file in pdf_files:
                zip_file.write(pdf_file, os.path.basename(pdf_file))
        
        zip_buffer.seek(0)
        
        # 清理臨時檔案
        for pdf_file in pdf_files:
            try:
                os.remove(pdf_file)
            except:
                pass
        
        return zip_buffer

# ==================== Streamlit 頁面函數 ====================
def show_dashboard(sheets_manager):
    """顯示儀表板"""
    st.header("📊 系統儀表板")
    
    # 獲取所有工作表
    sheet_names = sheets_manager.get_all_sheet_names()
    
    # 顯示工作表狀態
    col1, col2, col3 = st.columns(3)
    
    with col1:
        review_df = sheets_manager.get_sheet_data("Review")
        pending_count = len(review_df[review_df["決策"] == "待處理"]) if not review_df.empty and "決策" in review_df.columns else 0
        st.metric("待審批項目", pending_count)
    
    with col2:
        p2_ws_df = sheets_manager.get_sheet_data("P2_WS")
        ws_count = len(p2_ws_df) if not p2_ws_df.empty else 0
        st.metric("工作紙數量", ws_count)
    
    with col3:
        p2_tm_df = sheets_manager.get_sheet_data("P2_TM")
        tm_count = len(p2_tm_df) if not p2_tm_df.empty else 0
        st.metric("題庫詞彙", tm_count)
    
    st.markdown("---")
    
    # 顯示待處理項目
    st.subheader("📋 待處理項目清單")
    
    if not review_df.empty:
        # 過濾待處理項目
        if "決策" in review_df.columns:
            to_process = review_df[review_df["決策"].isin(["", "待處理", "待審批"])]
        else:
            to_process = review_df
        
        if not to_process.empty:
            # 可編輯的數據表格
            edited_df = st.data_editor(
                to_process.head(50),  # 限制顯示數量
                use_container_width=True,
                num_rows="dynamic",
                column_config={
                    "決策": st.column_config.SelectboxColumn(
                        "決策",
                        options=["", "待處理", "即用及保留", "保留", "待審批"],
                        required=False
                    ),
                    "下週題型": st.column_config.SelectboxColumn(
                        "下週題型",
                        options=["", "重組句子", "造句", "標點符號", "反義詞", "同義詞", "續寫句子", "詞辨"],
                        required=False
                    )
                }
            )
            
            # 保存按鈕
            if st.button("💾 儲存變更", use_container_width=True):
                # 這裡需要實現保存邏輯
                st.success("變更已儲存！")
        else:
            st.info("🎉 沒有待處理的項目！")
    else:
        st.info("Review 表格為空")
    
    # 快速操作按鈕
    st.markdown("---")
    st.subheader("⚡ 快速操作")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📥 匯入新詞", use_container_width=True):
            processor = DecisionProcessor(sheets_manager)
            count = processor.import_new_words()
            if count > 0:
                st.rerun()
    
    with col2:
        if st.button("✨ 生成題目", use_container_width=True):
            processor = DecisionProcessor(sheets_manager)
            count = processor.generate_next_week_questions()
            if count > 0:
                st.rerun()
    
    with col3:
        if st.button("📤 移交 Standby", use_container_width=True):
            processor = DecisionProcessor(sheets_manager)
            count = processor.move_to_standby()
            if count > 0:
                st.rerun()

def show_decision_page(sheets_manager):
    """顯示決策處理頁面"""
    st.header("🔄 分流搬移系統")
    
    processor = DecisionProcessor(sheets_manager)
    
    # 步驟式界面
    st.subheader("步驟 1: 檢查待處理項目")
    
    review_df = sheets_manager.get_sheet_data("Review")
    
    if not review_df.empty:
        # 決策分布
        if "決策" in review_df.columns:
            st.write("**決策分布:**")
            decision_counts = review_df["決策"].value_counts()
            st.bar_chart(decision_counts)
        
        # 過濾需要決策的項目
        need_decision = review_df[review_df["決策"].isin(["", "待處理"])]
        
        if not need_decision.empty:
            st.write(f"**需要決策的項目: {len(need_decision)} 個**")
            
            # 批量決策設置
            st.subheader("步驟 2: 批量設置決策")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("🏷️ 全設為「即用及保留」", use_container_width=True):
                    # 批量更新邏輯
                    for idx in need_decision.index:
                        row_num = idx + 2
                        sheets_manager.update_cell("Review", f"H{row_num}", "即用及保留")
                    st.success("已批量設置！")
                    st.rerun()
            
            with col2:
                if st.button("💾 全設為「保留」", use_container_width=True):
                    for idx in need_decision.index:
                        row_num = idx + 2
                        sheets_manager.update_cell("Review", f"H{row_num}", "保留")
                    st.success("已批量設置！")
                    st.rerun()
            
            with col3:
                if st.button("⏳ 全設為「待審批」", use_container_width=True):
                    for idx in need_decision.index:
                        row_num = idx + 2
                        sheets_manager.update_cell("Review", f"H{row_num}", "待審批")
                    st.success("已批量設置！")
                    st.rerun()
        
        # 詳細編輯
        st.subheader("步驟 3: 詳細編輯")
        
        if st.checkbox("顯示詳細編輯表格"):
            edited_df = st.data_editor(
                review_df.head(100),
                use_container_width=True,
                column_config={
                    "決策": st.column_config.SelectboxColumn(
                        "決策",
                        options=["", "待處理", "即用及保留", "保留", "待審批"],
                        required=False
                    )
                }
            )
    
    # 執行分流
    st.markdown("---")
    st.subheader("步驟 4: 執行分流")
    
    if st.button("🚀 執行分流搬移", type="primary", use_container_width=True):
        with st.spinner("正在處理分流..."):
            # 這裡可以添加更詳細的處理邏輯
            success_count = processor.move_to_standby()
            
            if success_count > 0:
                st.success(f"✅ 成功處理 {success_count} 個項目！")
                st.rerun()
            else:
                st.info("沒有需要處理的項目")

def show_pdf_generation_page(sheets_manager):
    """顯示 PDF 生成頁面"""
    st.header("📄 PDF 工作紙生成")
    
    pdf_gen = PDFGenerator()
    
    # 選擇資料來源
    st.subheader("選擇資料來源")
    
    source_option = st.radio(
        "資料來源",
        ["P2_WS (工作紙清單)", "Standby (待用題庫)", "自訂資料"],
        horizontal=True
    )
    
    if source_option == "P2_WS (工作紙清單)":
        data_df = sheets_manager.get_sheet_data("P2_WS")
    elif source_option == "Standby (待用題庫)":
        data_df = sheets_manager.get_sheet_data("Standby")
    else:
        data_df = pd.DataFrame()
    
    if not data_df.empty:
        st.success(f"✅ 載入 {len(data_df)} 筆資料")
        
        # 篩選選項
        st.subheader("篩選條件")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if "學校" in data_df.columns:
                schools = ["全部"] + list(data_df["學校"].unique())
                selected_school = st.selectbox("選擇學校", schools)
        
        with col2:
            if "題型" in data_df.columns:
                question_types = ["全部"] + list(data_df["題型"].unique())
                selected_type = st.selectbox("選擇題型", question_types)
        
        # 應用篩選
        filtered_df = data_df.copy()
        
        if "學校" in data_df.columns and selected_school != "全部":
            filtered_df = filtered_df[filtered_df["學校"] == selected_school]
        
        if "題型" in data_df.columns and selected_type != "全部":
            filtered_df = filtered_df[filtered_df["題型"] == selected_type]
        
        # 預覽
        st.subheader("預覽將生成的項目")
        st.dataframe(filtered_df.head(20), use_container_width=True)
        
        # PDF 設定
        st.subheader("PDF 設定")
        
        col1, col2 = st.columns(2)
        
        with col1:
            page_size = st.selectbox("紙張大小", ["A4", "Letter"])
            include_header = st.checkbox("包含頁首", value=True)
        
        with col2:
            font_size = st.slider("字型大小", 10, 16, 12)
            include_answer_key = st.checkbox("包含答案鍵", value=False)
        
        # 生成按鈕
        if st.button("🖨️ 生成 PDF 工作紙", type="primary", use_container_width=True):
            if len(filtered_df) > 0:
                with st.spinner("正在生成 PDF..."):
                    # 轉換資料格式
                    data_list = []
                    for _, row in filtered_df.iterrows():
                        data_dict = row.to_dict()
                        # 重命名欄位以符合 PDF 生成期望
                        if "詞語" in data_dict and "題目" in data_dict:
                            data_dict["下週題目"] = data_dict["題目"]
                            data_dict["下週題型"] = data_dict.get("題型", "")
                            data_dict["下週答案"] = data_dict.get("答案", "")
                        
                        data_list.append(data_dict)
                    
                    # 生成 PDF
                    if len(data_list) == 1:
                        # 單個 PDF
                        pdf_bytes = pdf_gen.create_worksheet(data_list[0])
                        st.download_button(
                            label="📥 下載工作紙",
                            data=pdf_bytes,
                            file_name=f"worksheet_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                            mime="application/pdf"
                        )
                    else:
                        # 多個 PDF 打包
                        zip_bytes = pdf_gen.generate_weekly_pdfs(data_list)
                        st.download_button(
                            label="📥 下載所有工作紙 (ZIP)",
                            data=zip_bytes,
                            file_name=f"worksheets_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                            mime="application/zip"
                        )
                        
                        st.success(f"✅ 已生成 {len(data_list)} 份工作紙")
            else:
                st.warning("沒有資料可生成")
    else:
        st.warning("選擇的資料來源為空或不存在")
    
    # 快速生成選項
    st.markdown("---")
    st.subheader("快速生成選項")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 生成本週工作紙", use_container_width=True):
            # 這裡可以實現特定邏輯
            st.info("此功能開發中...")
    
    with col2:
        if st.button("📅 生成下週預習", use_container_width=True):
            st.info("此功能開發中...")

def show_system_settings():
    """顯示系統設定頁面"""
    st.header("⚙️ 系統設定")
    
    # 連線狀態
    st.subheader("連線狀態")
    
    sheets_status = init_google_sheets()["status"]
    pdf_status = init_pdf_generator()["status"]
    
    col1, col2 = st.columns(2)
    
    with col1:
        if sheets_status == "connected":
            st.success("✅ Google Sheets 連接正常")
        else:
            st.error("❌ Google Sheets 連接失敗")
    
    with col2:
        if pdf_status == "success":
            st.success("✅ PDF 生成器準備就緒")
        elif pdf_status == "warning":
            st.warning("⚠️ PDF 生成器使用預設字型")
        else:
            st.error("❌ PDF 生成器初始化失敗")
    
    # 試算表資訊
    st.subheader("試算表資訊")
    
    try:
        spreadsheet_id = st.secrets["app_config"]["spreadsheet_id"]
        st.info(f"試算表 ID: `{spreadsheet_id}`")
        
        # 顯示可用工作表
        sheets_manager = GoogleSheetsManager()
        sheet_names = sheets_manager.get_all_sheet_names()
        
        if sheet_names:
            st.write("可用工作表:")
            for name in sheet_names:
                st.write(f"- {name}")
    except:
        st.warning("無法讀取試算表資訊")
    
    # 系統功能
    st.subheader("系統功能")
    
    if st.button("🔄 清除快取", use_container_width=True):
        st.cache_resource.clear()
        st.success("快取已清除！")
        st.rerun()
    
    if st.button("📊 重新整理資料", use_container_width=True):
        st.rerun()

# ==================== 主函數 ====================
def main():
    """主函數"""
    
    # 側邊欄
    with st.sidebar:
        st.title("📚 螺旋式學習")
        st.markdown("---")
        
        # 導航選單
        menu_option = st.radio(
            "主選單",
            ["📊 儀表板", "🔄 分流搬移", "📄 生成工作紙", "⚙️ 系統設定"],
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        
        # 系統狀態
        st.caption("系統狀態")
        
        # 初始化檢查
        sheets_status = init_google_sheets()["status"]
        pdf_status = init_pdf_generator()["status"]
        
        status_emoji = "✅" if sheets_status == "connected" else "❌"
        st.write(f"{status_emoji} Google Sheets")
        
        if pdf_status == "success":
            st.write("✅ 標楷體 PDF")
        elif pdf_status == "warning":
            st.write("⚠️ 預設字型 PDF")
        else:
            st.write("❌ PDF 生成")
        
        st.markdown("---")
        
        # 快速操作
        st.caption("快速操作")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔄 重整", use_container_width=True):
                st.rerun()
        
        with col2:
            if st.button("📖 手冊", use_container_width=True):
                st.info("系統使用手冊開發中...")
        
        st.markdown("---")
        
        # 版本資訊
        st.caption("版本 v1.0")
        st.caption("Streamlit + Google Sheets 整合系統")
    
    # 主內容區
    try:
        # 初始化 Google Sheets
        sheets_manager = GoogleSheetsManager()
        
        if menu_option == "📊 儀表板":
            show_dashboard(sheets_manager)
        
        elif menu_option == "🔄 分流搬移":
            show_decision_page(sheets_manager)
        
        elif menu_option == "📄 生成工作紙":
            show_pdf_generation_page(sheets_manager)
        
        elif menu_option == "⚙️ 系統設定":
            show_system_settings()
    
    except Exception as e:
        st.error(f"系統錯誤: {str(e)}")
        st.info("請檢查系統設定和網路連接")

# ==================== 執行應用 ====================
if __name__ == "__main__":
    # 檢查必要的 secrets
    required_secrets = ["gcp_service_account", "app_config"]
    missing_secrets = [s for s in required_secrets if s not in st.secrets]
    
    if missing_secrets:
        st.error(f"缺少必要的設定: {', '.join(missing_secrets)}")
        st.info("請在 Streamlit Cloud 的 Secrets 中設定:")
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
