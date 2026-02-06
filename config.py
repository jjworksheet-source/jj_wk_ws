"""
配置檔案：集中管理工作表名稱、欄位名稱、狀態值等
"""

# Google Sheets 工作表名稱
SHEET_NAMES = {
    'form': '家長申請',
    'review': 'Review',
    'tm': 'P2_TM',
    'ws': 'P2_WS',
    'standby': 'Standby'
}

# 家長申請表欄位 (使用欄位名稱，不依賴位置)
FORM_COLUMNS = {
    'timestamp': 'Timestamp',
    'school': '學',
    'words': '請輸入詞語',
    'status': '狀態'
}

# Review 表欄位
REVIEW_COLUMNS = {
    'timestamp': 'Timestamp',
    'school': '學校',
    'word': '詞語',
    'sentence': '句子 (本週題目)',
    'next_type': '下週題型',
    'next_question': '下週題目 (AI)',
    'next_answer': '下週答案 (AI)',
    'decision': '決策'  # H 欄 (未來使用)
}

# P2_TM 題庫欄位
TM_COLUMNS = {
    'word': '詞語',
    'sentence': '句子'
}

# 狀態值
STATUS = {
    'done': 'Done',
    'ready': 'Ready',
    'waiting': 'Waiting'
}

# AI 標記
AI_ICON = '🟨 '

# 題型選項 (用於下拉選單)
QUESTION_TYPES = [
    '重組句子',
    '造句',
    '標點符號',
    '反義詞',
    '同義詞',
    '續寫句子',
    '詞辨'
]

# DeepSeek API 設定
DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
DEEPSEEK_MODEL = "deepseek-chat"
