import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import requests
from datetime import datetime
from fpdf import FPDF
import os

# ==================== 1. 初始化與連線 (必須放在最前面) ====================

def init_connection():
    """初始化 Google Sheets 連線"""
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    try:
        creds_info = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_info, scopes=scope)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"連線初始化失敗: {e}")
        return None

def get_spreadsheet(client):
    """取得試算表物件"""
    try:
        spreadsheet_id = st.secrets["google_sheets"]["spreadsheet_id"]
        return client.open_by_key(spreadsheet_id)
    except Exception as e:
        st.error(f"無法開啟試算表: {e}")
        return None

# ==================== 2. PDF 生成類別 ====================

class WorksheetPDF(FPDF):
    def header(self):
        if hasattr(self, 'kaiti_loaded'):
            self.set_font("KaiTi", "", 16)
        else:
            self.set_font("Helvetica", "B", 16)
        self.cell(0, 10, "螺旋式學習工作紙", ln=True, align="C")
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        if hasattr(self, 'kaiti_loaded'):
            self.set_font("KaiTi", "", 10)
        else:
            self.set_font("Helvetica", "", 10)
        self.cell(0, 10, f"頁碼 {self.page_no()}", align="C")

def pdf_generator_file(df):
    """生成 PDF 檔案"""
    pdf = WorksheetPDF()
    font_path = "simkai.ttf"
    
    if os.path.exists(font_path):
        pdf.add_font("KaiTi", "", font_path)
        pdf.kaiti_loaded = True
        pdf.set_font("KaiTi", "", 12)
    else:
        st.warning("找不到 simkai.ttf，將使用預設字型（不支援中文）")
        pdf.set_font("Helvetica", "", 12)

    pdf.add_page()
    for i, row in df.iterrows():
        school = row.get("學校", "通用")
        word = row.get("詞語", "")
        question = row.get("題目", "")
        text = f"{i+1}. ({school}) {word}: {question}"
        pdf.multi_cell(0, 10, txt=text)
        pdf.ln(2)
    
    return pdf.output()

# ==================== 3. 資料處理函數 ====================

def get_worksheet_safe(sh, name_list):
    """安全地取得工作表，嘗試多種大小寫組合"""
    all_ws = [ws.title for ws in sh.worksheets()]
    for name in name_list:
        if name in all_ws:
            return sh.worksheet(name)
    return None

# ==================== 4. 主程式 UI ====================

def main():
    st.set_page_config(page_title="螺旋式學習教材管理系統", layout="wide")
    st.title("🚀 JJ 螺旋式學習教材管理系統")

    # 檢查 Secrets 結構
    if "google_sheets" not in st.secrets:
        st.error("❌ Secrets 中缺少 [google_sheets] 區塊。請檢查 Streamlit Cloud 設定。")
        st.info("目前的 Secrets Keys: " + str(list(st.secrets.keys())))
        return

    # 初始化連線
    gc = init_connection()
    if not gc: 
        return
    
    sh = get_spreadsheet(gc)
    if not sh: 
        return

    st.sidebar.success("✅ 已連線至 Google Sheets")
    
    menu = ["📋 儀表板 (Review)", "📦 Standby 管理", "🖨️ 生成 PDF 工作紙"]
    choice = st.sidebar.selectbox("功能選單", menu)

    if choice == "📋 儀表板 (Review)":
        st.subheader("📋 待處理審核項目 (Review)")
        ws = get_worksheet_safe(sh, ["Review", "review"])
        if ws:
            df = pd.DataFrame(ws.get_all_records())
            st.dataframe(df)
        else:
            st.error("找不到 'Review' 工作表")

    elif choice == "📦 Standby 管理":
        st.subheader("📦 Standby 項目")
        ws = get_worksheet_safe(sh, ["standby", "Standby"])
        if ws:
            df = pd.DataFrame(ws.get_all_records())
            st.dataframe(df)
        else:
            st.error("找不到 'standby' 工作表")

    elif choice == "🖨️ 生成 PDF 工作紙":
        st.subheader("🖨️ PDF 工作紙生成器")
        ws = get_worksheet_safe(sh, ["standby", "Standby"])
        if ws:
            df = pd.DataFrame(ws.get_all_records())
            if not df.empty:
                st.write("預覽題目：")
                st.dataframe(df[["學校", "詞語", "題目"]].head())
                if st.button("生成 PDF"):
                    pdf_output = pdf_generator_file(df)
                    st.download_button(
                        label="下載 PDF",
                        data=bytes(pdf_output),
                        file_name=f"worksheet_{datetime.now().strftime('%Y%m%d')}.pdf",
                        mime="application/pdf"
                    )
            else:
                st.warning("Standby 表格是空的")
        else:
            st.error("找不到 'standby' 工作表")

if __name__ == "__main__":
    main()
