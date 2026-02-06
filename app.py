import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import requests
from datetime import datetime

# ==================== 初始化與連線 ====================

def main():
    st.set_page_config(page_title="螺旋式學習教材管理系統", layout="wide")
    st.title("🚀 JJ 螺旋式學習教材管理系統")

    # === DEBUG: 顯示目前 secrets 的 key ===
    st.write("DEBUG - secrets keys:", list(st.secrets.keys()))def init_connection():
    """初始化 Google Sheets 連線"""
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    creds_info = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_info, scopes=scope)
    client = gspread.authorize(creds)
    return client

def get_spreadsheet(client):
    """取得試算表物件"""
    spreadsheet_id = st.secrets["google_sheets"]["spreadsheet_id"]
    return client.open_by_key(spreadsheet_id)

# ==================== 資料讀取函數 ====================

def get_review_data(client):
    """讀取 Review 工作表資料"""
    sh = get_spreadsheet(client)
    worksheet = sh.worksheet("Review")
    data = worksheet.get_all_records()
    return worksheet, pd.DataFrame(data)

def get_tm_data(client):
    """讀取 P2_TM 題庫資料"""
    sh = get_spreadsheet(client)
    worksheet = sh.worksheet("P2_TM")
    data = worksheet.get_all_records()
    return worksheet, pd.DataFrame(data)

def get_form_data(client):
    """讀取表單回應資料"""
    sh = get_spreadsheet(client)
    worksheet = sh.worksheet("Form responses 1")
    data = worksheet.get_all_values()
    return worksheet, data

def get_standby_data(client):
    """讀取 Standby 資料"""
    sh = get_spreadsheet(client)
    worksheet = sh.worksheet("Standby")
    data = worksheet.get_all_records()
    return worksheet, pd.DataFrame(data)

# ==================== AI 相關函數 ====================

AI_ICON = '🟨 '

def generate_sentence_by_ai(word):
    """使用 DeepSeek AI 生成句子"""
    api_key = st.secrets["api_keys"]["deepseek_key"]
    url = "https://api.deepseek.com/chat/completions"
    
    prompt = f"請用「{word}」造一個適合香港小學生的句子。句子中必須包含「{word}」。請直接回傳句子，不要有其他文字。"
    
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        json_data = response.json()
        
        if json_data.get("choices") and len(json_data["choices"]) > 0:
            return AI_ICON + json_data["choices"][0]["message"]["content"].strip()
        return AI_ICON + "AI Generation Failed"
    except Exception as e:
        return f"AI Error: {str(e)}"

def get_prompt_by_type(question_type, word, full_sentence):
    """根據題型生成 Prompt"""
    base_instruction = f"""
任務：請根據句子「{full_sentence}」和關鍵詞「{word}」，製作一道「{question_type}」。
回傳格式：JSON 物件 {{"question": "...", "answer": "..."}}。
"""

    specific_instructions = {
        "重組句子": """
1. 請將句子拆解為 **6 到 10 個** 短語區塊。
2. **長度限制**：每個區塊盡量控制在 **2 到 5 個字**，絕對不要出現長句子（例如超過 8 個字的區塊）。
3. **標點符號保留**：
   - **逗號 (，)**：必須保留！請將逗號附著在該分句的最後一個詞上（例如：「步驟，」），或者獨立成一個區塊。
   - **句號/驚嘆號**：請獨立成一個區塊，或附著在最後一個詞。
4. **嚴格保留專名號**：【】浩恆【】 不可拆分。
5. 區塊之間用 ' / ' 分隔，順序打亂。
6. "answer" 為完整原句。
""",
        "標點符號": """
1. 移除所有標點符號作為 "question"。
2. "answer" 為包含正確標點的完整句子。
""",
        "反義詞": f"""
1. "question" 格式：「{full_sentence}」\\n請寫出句子中「{word}」的反義詞。
2. "answer" 為該反義詞。
""",
        "同義詞": f"""
1. "question" 格式：「{full_sentence}」\\n請寫出句子中「{word}」的近義詞。
2. "answer" 為該近義詞。
""",
        "詞辨": f"""
1. 請針對「{word}」找兩個形近或音近的干擾選項。
2. "question" 顯示原句並挖空關鍵詞，後方附上 (A)(B)(C) 選項。
3. "answer" 只寫正確選項的代號與詞語。
""",
        "造句": f"""
1. "question" 格式：請用「{word}」造句。
2. "answer" 為參考句子：{full_sentence}
""",
        "續寫句子": f"""
1. "question" 格式：請續寫句子：{full_sentence[:len(full_sentence)//2]}...
2. "answer" 為完整句子：{full_sentence}
"""
    }
    
    specific = specific_instructions.get(question_type, "請製作適合小學生的題目。")
    return base_instruction + "\n" + specific

def call_deepseek_for_question(word, full_sentence, question_type):
    """呼叫 DeepSeek API 生成題目"""
    api_key = st.secrets["api_keys"]["deepseek_key"]
    url = "https://api.deepseek.com/chat/completions"
    
    prompt = get_prompt_by_type(question_type, word, full_sentence)
    
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "你是一位資深的香港小學中文科老師。請使用繁體中文。題目需符合香港小學格式。請務必以 JSON 格式回傳。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "response_format": {"type": "json_object"}
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        json_data = response.json()
        
        if json_data.get("choices") and len(json_data["choices"]) > 0:
            import json
            result = json.loads(json_data["choices"][0]["message"]["content"])
            return result
        return None
    except Exception as e:
        st.error(f"AI 生成錯誤: {str(e)}")
        return None

# ==================== 核心業務邏輯 ====================

def import_new_words_from_form(client):
    """步驟 1: 匯入新詞 (從表單)"""
    sh = get_spreadsheet(client)
    form_sheet = sh.worksheet("Form responses 1")
    review_sheet = sh.worksheet("Review")
    tm_sheet = sh.worksheet("P2_TM")
    
    # 讀取 TM 資料庫建立快取
    tm_data = tm_sheet.get_all_values()
    tm_map = {}
    for i in range(1, len(tm_data)):
        if len(tm_data[i]) >= 2:
            word = str(tm_data[i][0]).strip()
            sentence = tm_data[i][1]
            if word:
                tm_map[word] = sentence
    
    # 讀取表單資料
    form_data = form_sheet.get_all_values()
    new_review_rows = []
    form_rows_to_update = []
    
    for i in range(1, len(form_data)):
        row = form_data[i]
        if len(row) < 4:
            continue
            
        status = row[3] if len(row) > 3 else ""
        
        if status != "Done":
            timestamp = row[0] if len(row) > 0 else ""
            school = row[1] if len(row) > 1 else ""
            raw_words = row[2] if len(row) > 2 else ""
            
            if raw_words:
                import re
                words = re.split(r'[,，\s、]+', str(raw_words))
                
                for word in words:
                    word = word.strip()
                    if word:
                        # 優先查 TM 資料庫
                        if word in tm_map:
                            sentence = tm_map[word]
                        else:
                            # 呼叫 AI 生成
                            sentence = generate_sentence_by_ai(word)
                        
                        new_review_rows.append([
                            timestamp, school, word, sentence, '', '', '', ''
                        ])
                
                form_rows_to_update.append(i + 1)
    
    # 寫入 Review
    if new_review_rows:
        last_row = len(review_sheet.get_all_values())
        start_row = last_row + 1
        
        for row in new_review_rows:
            review_sheet.append_row(row)
        
        # 更新表單狀態
        for row_idx in form_rows_to_update:
            form_sheet.update_cell(row_idx, 4, "Done")
        
        return len(new_review_rows)
    
    return 0

def generate_next_week_content(client):
    """步驟 2: 生成下週題目 (AI)"""
    sh = get_spreadsheet(client)
    review_sheet = sh.worksheet("Review")
    
    data = review_sheet.get_all_values()
    if len(data) < 2:
        return 0, 0
    
    processed_count = 0
    skipped_count = 0
    
    for i in range(1, len(data)):
        row = data[i]
        if len(row) < 7:
            continue
        
        word = row[2] if len(row) > 2 else ""
        sentence = row[3] if len(row) > 3 else ""
        next_type = row[4] if len(row) > 4 else ""
        next_q = row[5] if len(row) > 5 else ""
        
        # 檢查條件
        if not word or not sentence or not next_type:
            continue
        if next_q != "":
            continue
        if AI_ICON in sentence:
            skipped_count += 1
            continue
        
        # 還原完整句子
        import re
        full_sentence = re.sub(r'_+|＿+|【.*?】', lambda m: word if not m.group().startswith('【') else m.group(), sentence)
        
        # 呼叫 AI
        result = call_deepseek_for_question(word, full_sentence, next_type)
        
        if result:
            review_sheet.update_cell(i + 1, 6, AI_ICON + result.get("question", ""))
            review_sheet.update_cell(i + 1, 7, result.get("answer", ""))
            processed_count += 1
    
    return processed_count, skipped_count

def move_to_standby(client):
    """步驟 3: 移交至 Standby"""
    sh = get_spreadsheet(client)
    review_sheet = sh.worksheet("Review")
    standby_sheet = sh.worksheet("Standby")
    
    data = review_sheet.get_all_values()
    if len(data) < 2:
        return 0
    
    standby_data = []
    rows_to_clear = []
    today = datetime.now().strftime("%Y-%m-%d")
    
    for i in range(1, len(data)):
        row = data[i]
        if len(row) < 7:
            continue
        
        school = row[1] if len(row) > 1 else ""
        word = row[2] if len(row) > 2 else ""
        this_week_q = row[3] if len(row) > 3 else ""
        next_type = row[4] if len(row) > 4 else ""
        next_week_q = row[5] if len(row) > 5 else ""
        next_week_a = row[6] if len(row) > 6 else ""
        
        if not school or not word or not this_week_q:
            continue
        if next_type and next_week_q == "":
            continue
        
        unique_base = f"{school}_{datetime.now().timestamp()}_{i}"
        
        # 雙胞胎 1: 本週填空題
        standby_data.append([
            f"{unique_base}_f", school, word, "填空題", this_week_q, word, "Ready", today
        ])
        
        # 雙胞胎 2: 下週變化題
        if next_week_q:
            standby_data.append([
                f"{unique_base}_o", school, word, next_type, next_week_q, next_week_a, "Waiting", today
            ])
        
        rows_to_clear.append(i + 1)
    
    # 寫入 Standby
    if standby_data:
        for row in standby_data:
            standby_sheet.append_row(row)
        
        # 清除 Review (從後往前)
        for row_idx in sorted(rows_to_clear, reverse=True):
            review_sheet.delete_rows(row_idx)
        
        return len(standby_data)
    
    return 0

def process_decisions(client):
    """根據決策欄位分流資料"""
    sh = get_spreadsheet(client)
    review_sheet = sh.worksheet("Review")
    ws_sheet = sh.worksheet("P2_WS")
    tm_sheet = sh.worksheet("P2_TM")
    
    data = review_sheet.get_all_values()
    if len(data) < 2:
        return 0
    
    processed_rows = []
    
    for i in range(1, len(data)):
        row = data[i]
        if len(row) < 8:
            continue
        
        decision = str(row[7]).strip() if len(row) > 7 else ""
        
        word = row[2] if len(row) > 2 else ""
        sentence = row[3] if len(row) > 3 else ""
        school = row[1] if len(row) > 1 else ""
        next_q = row[5] if len(row) > 5 else ""
        next_a = row[6] if len(row) > 6 else ""
        
        if decision == "即用及保留":
            ws_sheet.append_row([school, word, next_q, next_a])
            tm_sheet.append_row([word, sentence])
            processed_rows.append(i + 1)
            
        elif decision == "保留":
            tm_sheet.append_row([word, sentence])
            processed_rows.append(i + 1)
    
    # 清除已處理的行
    for row_idx in sorted(processed_rows, reverse=True):
        review_sheet.delete_rows(row_idx)
    
    return len(processed_rows)

# ==================== Streamlit UI ====================

def main():
    st.set_page_config(page_title="螺旋式學習教材管理系統", layout="wide")
    st.title("🚀 JJ 螺旋式學習教材管理系統")
    
    # 初始化連線
    try:
        gc = init_connection()
        st.sidebar.success("✅ 已連線至 Google Sheets")
    except Exception as e:
        st.error(f"❌ 連線失敗: {e}")
        return
    
    # 側邊欄選單
    menu = ["📋 儀表板 (Review)", "📚 題庫管理 (P2_TM)", "📦 Standby 管理", "🖨️ 生成 PDF 工作紙"]
    choice = st.sidebar.selectbox("功能選單", menu)
    
    # ==================== 儀表板 (Review) ====================
    if choice == "📋 儀表板 (Review)":
        st.subheader("📋 待處理審核項目 (Review)")
        
        try:
            ws, df = get_review_data(gc)
            
            if df.empty:
                st.info("✨ 目前沒有待處理的項目。")
            else:
                st.dataframe(df, use_container_width=True)
                
                st.divider()
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    if st.button("📥 1. 匯入新詞 (Form)", use_container_width=True):
                        with st.spinner("正在匯入新詞..."):
                            count = import_new_words_from_form(gc)
                            if count > 0:
                                st.success(f"✅ 成功匯入 {count} 個新詞彙！")
                                st.rerun()
                            else:
                                st.info("沒有發現新的表單回應。")
                
                with col2:
                    if st.button("✨ 2. 生成下週題目 (AI)", use_container_width=True):
                        with st.spinner("正在生成題目..."):
                            processed, skipped = generate_next_week_content(gc)
                            msg = f"✅ 成功生成 {processed} 題！"
                            if skipped > 0:
                                msg += f"\n(跳過了 {skipped} 題，因為原句是 AI 生成的)"
                            st.success(msg)
                            st.rerun()
                
                with col3:
                    if st.button("📤 3. 移交 Standby", use_container_width=True):
                        with st.spinner("正在移交資料..."):
                            count = move_to_standby(gc)
                            if count > 0:
                                st.success(f"✅ 成功移交 {count} 筆題目至 Standby！")
                                st.rerun()
                            else:
                                st.info("沒有發現可移交的資料。")
                
                with col4:
                    if st.button("🔄 執行決策分流", use_container_width=True):
                        with st.spinner("正在分流資料..."):
                            count = process_decisions(gc)
                            if count > 0:
                                st.success(f"✅ 成功分流 {count} 筆項目！")
                                st.rerun()
                            else:
                                st.info("沒有發現需要分流的資料。")
        
        except Exception as e:
            st.error(f"讀取資料時發生錯誤: {e}")
    
    # ==================== 題庫管理 ====================
    elif choice == "📚 題庫管理 (P2_TM)":
        st.subheader("📚 題庫內容 (P2_TM)")
        
        try:
            ws, df = get_tm_data(gc)
            
            if df.empty:
                st.info("題庫目前是空的。")
            else:
                st.dataframe(df, use_container_width=True)
                st.info(f"共有 {len(df)} 筆詞彙資料")
        
        except Exception as e:
            st.error(f"讀取資料時發生錯誤: {e}")
    
    # ==================== Standby 管理 ====================
    elif choice == "📦 Standby 管理":
        st.subheader("📦 Standby 題目清單")
        
        try:
            ws, df = get_standby_data(gc)
            
            if df.empty:
                st.info("Standby 目前沒有題目。")
            else:
                st.dataframe(df, use_container_width=True)
                st.info(f"共有 {len(df)} 筆待處理題目")
        
        except Exception as e:
            st.error(f"讀取資料時發生錯誤: {e}")
    
    # ==================== PDF 生成 ====================
    elif choice == "🖨️ 生成 PDF 工作紙":
        st.subheader("🖨️ PDF 工作紙生成器")
        st.write("使用字體：標楷體 (simkai.ttf)")
        st.info("🚧 此功能正在開發中...")
        st.write("下一步將整合 FPDF2 + simkai.ttf 生成 A4 格式的工作紙。")

if __name__ == "__main__":
    main()
