# app.py
import streamlit as st
from src.sheets_client import SheetsClient
from src.pipeline import Pipeline
from src.config import SHEET_NAMES

def main():
    st.set_page_config(page_title="JJ 螺旋式學習系統", layout="wide")
    st.title("🚀 JJ 螺旋式學習教材管理系統")

    # 初始化客戶端與管道
    client = SheetsClient()
    pipeline = Pipeline(client)

    # 側邊欄選單
    menu = ["📊 儀表板", "📥 1. 匯入新詞", "✨ 2. 生成 AI 題目", "📤 3. 移交 Standby"]
    choice = st.sidebar.selectbox("功能選單", menu)

    if choice == "📊 儀表板":
        show_dashboard(client)
    elif choice == "📥 1. 匯入新詞":
        if st.button("開始匯入"):
            pipeline.import_new_words()
    elif choice == "✨ 2. 生成 AI 題目":
        if st.button("開始生成"):
            pipeline.generate_questions()
    elif choice == "📤 3. 移交 Standby":
        if st.button("開始移交"):
            pipeline.move_to_standby()

def show_dashboard(client):
    st.subheader("📋 Review 表預覽")
    df = client.read_sheet_as_df(SHEET_NAMES['review'])
    if not df.empty:
        st.dataframe(df, use_container_width=True)
    else:
        st.info("目前沒有待審核資料。")

if __name__ == "__main__":
    main()
