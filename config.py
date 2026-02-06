# config.py
import streamlit as st

# 試算表設定
SPREADSHEET_ID = st.secrets.get("SPREADSHEET_ID", "1CedBSZFj5OjY2hglpiJjtBC57NyxQMfVSZxmlDbA3aU")

SHEET_NAMES = {
    'form': '家長申請',
    'review': 'Review',
    'tm': 'P2_TM',
    'ws': 'P2_WS',
    'standby': 'Standby'
}

# 欄位名稱 (精確對應你的截圖)
REVIEW_COLUMNS = {
    'timestamp': 'Timestamp',
    'school': '學校',
    'word': '詞語',
    'sentence': '句子 (本週題目)',
    'next_type': '下週題型',
    'next_q': '下週題目 (AI)',
    'next_a': 'G: 下週答案 (AI)'  # 這裡要包含 G:
}

# AI 標記
AI_ICON = '🟨 '
