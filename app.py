import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

# --- 1. 初始化連線函數 ---
def init_connection():
    # 定義權限範圍
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    # 從 Streamlit Secrets 讀取 Service Account 資訊
    creds_info = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(creds_info, scopes=scope)
    
    # 建立 gspread 客戶端
    client = gspread.authorize(creds)
    return client

# --- 2. 取得工作表函數 ---
def get_sheet_data(client, sheet_id, tab_name):
    sh = client.open_by_key(sheet_id)
    worksheet = sh.worksheet(tab_name)
    return worksheet

# --- 3. 主程式 UI ---
def main():
    st.set_page_config(page_title="螺旋式學習教材管理系統", layout="wide")
    st.title("🚀 JJ 螺旋式學習教材管理系統")

    # 初始化連線
    try:
        gc = init_connection()
        st.success("✅ 已成功連線至 Google Sheets")
    except Exception as e:
        st.error(f"❌ 連線失敗: {e}")
        return

    # 側邊欄導覽
    menu = ["儀表板 (Review)", "題庫管理 (P2_TM)", "生成 PDF 工作紙"]
    choice = st.sidebar.selectbox("功能選單", menu)

    spreadsheet_id = st.secrets["google_sheets"]["spreadsheet_id"]

    if choice == "儀表板 (Review)":
        st.subheader("📋 待處理審核項目 (Review)")
        # 這裡之後會寫讀取 Review 表的邏輯
        st.info("正在開發中：將顯示 Review 表中待處理的項目...")

    elif choice == "題庫管理 (P2_TM)":
        st.subheader("📚 題庫內容 (P2_TM)")
        # 這裡之後會寫讀取 P2_TM 的邏輯
        
    elif choice == "生成 PDF 工作紙":
        st.subheader("🖨️ PDF 工作紙生成器")
        st.write("使用字體：標楷體 (simkai.ttf)")

if __name__ == "__main__":
    main()
