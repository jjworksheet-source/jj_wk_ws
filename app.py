# app.py
# -*- coding: utf-8 -*-
"""
Streamlit 工作紙生成系統 (標楷體版本)
讀取 Google Sheets Review 表，產生 PDF 並上傳至 Google Drive
"""

import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io
import datetime
import re
import random

# ===== 設定區 =====
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file'
]

# ===== 註冊標楷體 =====
@st.cache_resource
def register_font():
    try:
        pdfmetrics.registerFont(TTFont('KaiU', 'fonts/kaiu.ttf'))
        return 'KaiU'
    except Exception as e:
        st.error(f"字型載入失敗：{e}")
        return 'Helvetica'

# ===== 連接 Google Sheets =====
@st.cache_resource
def get_gspread_client():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=SCOPES
    )
    return gspread.authorize(creds), creds

# ===== 連接 Google Drive =====
def get_drive_service(creds):
    return build('drive', 'v3', credentials=creds)

# ===== 讀取 Review 表 =====
def read_review_sheet(gc, spreadsheet_id):
    try:
        sh = gc.open_by_key(spreadsheet_id)
        worksheet = sh.worksheet('Review')
        data = worksheet.get_all_records()
        return data
    except Exception as e:
        st.error(f"讀取 Review 表失敗：{e}")
        return []

# ===== PDF 生成函數 =====
def create_pdf_with_kaiu(words_and_sentences, school, level, font_name):
    """
    產生標楷體 PDF (本週題目)
    words_and_sentences: list of dict [{"詞語": "...", "句子": "..."}]
    """
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    page_w, page_h = A4
    
    # 樣式設定
    title_size = 18
    body_size = 16
    line_height = 30
    margin_left = 60
    margin_right = 60
    cur_y = page_h - 80
    
    # 標題
    c.setFont(font_name, title_size)
    header1 = f"{school} {level}"
    text_width = pdfmetrics.stringWidth(header1, font_name, title_size)
    x_center = (page_w - text_width) / 2
    c.drawString(x_center, cur_y, header1)
    cur_y -= line_height
    
    c.setFont(font_name, body_size)
    header2 = "童學童樂詞語填充"
    text_width = pdfmetrics.stringWidth(header2, font_name, body_size)
    x_center = (page_w - text_width) / 2
    c.drawString(x_center, cur_y, header2)
    cur_y -= line_height
    
    # 學生姓名與日期
    today_str = datetime.date.today().isoformat()
    left_str = "學生姓名：____"
    right_str = f"日期：{today_str}"
    c.drawString(margin_left, cur_y, left_str)
    right_text_width = pdfmetrics.stringWidth(right_str, font_name, body_size)
    right_x = page_w - margin_right - right_text_width
    c.drawString(right_x, cur_y, right_str)
    cur_y -= line_height * 2
    
    # 題目
    for idx, item in enumerate(words_and_sentences, start=1):
        word = item["詞語"]
        sentence = item["句子"]
        
        # 處理句子：把詞語替換成底線
        blank = '＿' * max(len(word) * 2, 4)
        if word in sentence:
            processed = sentence.replace(word, blank, 1)
        else:
            processed = sentence + " " + blank
        
        # 檢查是否需要換頁
        if cur_y - line_height < 60:
            c.showPage()
            cur_y = page_h - 80
            c.setFont(font_name, body_size)
        
        # 繪製題號與句子
        c.drawString(margin_left, cur_y, f"{idx}. {processed}")
        cur_y -= line_height
    
    # 詞語清單頁
    c.showPage()
    cur_y = page_h - 80
    c.setFont(font_name, title_size)
    c.drawString(margin_left, cur_y, "詞語清單")
    cur_y -= line_height
    c.setFont(font_name, body_size)
    
    for idx, item in enumerate(words_and_sentences, start=1):
        if cur_y - line_height < 60:
            c.showPage()
            cur_y = page_h - 80
            c.setFont(font_name, body_size)
        c.drawString(margin_left, cur_y, f"{idx}. {item['詞語']}")
        cur_y -= line_height
    
    c.save()
    buffer.seek(0)
    return buffer

# ===== 上傳到 Google Drive =====
def upload_to_drive(drive_service, file_buffer, filename, folder_id):
    try:
        file_metadata = {
            'name': filename,
            'parents': [folder_id]
        }
        media = MediaIoBaseUpload(file_buffer, mimetype='application/pdf', resumable=True)
        file = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        return file.get('id')
    except Exception as e:
        st.error(f"上傳失敗：{e}")
        return None

# ===== 記錄到 Usage_Log =====
def log_to_sheet(gc, spreadsheet_id, school, words, file_id, status):
    try:
        sh = gc.open_by_key(spreadsheet_id)
        try:
            worksheet = sh.worksheet('Usage_Log')
        except:
            worksheet = sh.add_worksheet(title='Usage_Log', rows=100, cols=6)
            worksheet.append_row(['Timestamp', 'School', 'Words', 'Drive_File_ID', 'Status', 'Parent_Email'])
        
        timestamp = datetime.datetime.now().isoformat()
        worksheet.append_row([timestamp, school, words, file_id, status, ''])
        return True
    except Exception as e:
        st.error(f"記錄失敗：{e}")
        return False

# ===== Streamlit UI =====
def main():
    st.set_page_config(page_title="JJ 工作紙系統", page_icon="📝")
    
    st.title("📝 童學童樂工作紙生成系統")
    st.markdown("---")
    
    # 註冊字型
    font_name = register_font()
    
    # 連接服務
    gc, creds = get_gspread_client()
    drive_service = get_drive_service(creds)
    
    spreadsheet_id = st.secrets["SPREADSHEET_ID"]
    folder_id = st.secrets["DRIVE_FOLDER_ID"]
    
    # 讀取 Review 資料
    with st.spinner("正在讀取題庫..."):
        review_data = read_review_sheet(gc, spreadsheet_id)
    
    if not review_data:
        st.warning("Review 表中沒有資料")
        return
    
    # 顯示可用的學校
    schools = list(set([row['學校'] for row in review_data if row.get('學校')]))
    
    st.subheader("請選擇學校")
    selected_school = st.selectbox("學校", schools)
    
    if selected_school:
        # 篩選該學校的資料
        school_data = [row for row in review_data if row['學校'] == selected_school]
        
        if school_data:
            st.success(f"找到 {len(school_data)} 個詞語")
            
            # 顯示詞語清單
            words_list = [row['詞語'] for row in school_data if row.get('詞語')]
            st.write("**詞語清單：**", ", ".join(words_list))
            
            # 生成按鈕
            if st.button("🖨️ 生成 PDF 工作紙", type="primary"):
                with st.spinner("正在生成 PDF..."):
                    # 準備資料
                    words_and_sentences = []
                    for row in school_data:
                        if row.get('詞語') and row.get('句子 (本週題目)'):
                            words_and_sentences.append({
                                "詞語": row['詞語'],
                                "句子": row['句子 (本週題目)']
                            })
                    
                    if not words_and_sentences:
                        st.error("沒有有效的題目資料")
                        return
                    
                    # 打亂順序
                    random.shuffle(words_and_sentences)
                    
                    # 生成 PDF
                    level = school_data[0].get('年級', 'P3')  # 假設同一學校同年級
                    pdf_buffer = create_pdf_with_kaiu(words_and_sentences, selected_school, level, font_name)
                    
                    # 上傳到 Drive
                    filename = f"worksheet_{selected_school}_{datetime.date.today()}.pdf"
                    file_id = upload_to_drive(drive_service, pdf_buffer, filename, folder_id)
                    
                    if file_id:
                        st.success("✅ PDF 已生成並上傳至 Google Drive！")
                        st.info(f"檔案 ID: {file_id}")
                        
                        # 記錄到 Usage_Log
                        words_str = ", ".join(words_list)
                        log_to_sheet(gc, spreadsheet_id, selected_school, words_str, file_id, 'Pending')
                        
                        st.balloons()
                        st.markdown("**系統將於今晚 19:00 自動寄送至家長信箱。**")
                    else:
                        st.error("上傳失敗，請檢查 Drive 權限")

if __name__ == "__main__":
    main()
