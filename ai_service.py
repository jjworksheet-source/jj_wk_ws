"""
AI 服務：處理 DeepSeek API 呼叫
"""

import requests
import streamlit as st
from config import DEEPSEEK_API_URL, DEEPSEEK_MODEL, AI_ICON
import json


def generate_sentence_by_ai(word):
    """使用 AI 生成例句"""
    prompt = f"請用「{word}」造一個適合香港小學生的句子。句子中必須包含「{word}」。請直接回傳句子，不要有其他文字。"
    
    try:
        response = call_deepseek(prompt, temperature=0.7, json_mode=False)
        return AI_ICON + response.strip()
    except Exception as e:
        return f"{AI_ICON}AI Error: {str(e)}"


def generate_question_by_ai(word, full_sentence, question_type):
    """使用 AI 生成題目 (JSON 格式)"""
    prompt = get_prompt_by_type(question_type, word, full_sentence)
    
    try:
        response = call_deepseek(prompt, temperature=0.7, json_mode=True)
        result = json.loads(response)
        return {
            'question': result.get('question', ''),
            'answer': result.get('answer', '')
        }
    except Exception as e:
        st.error(f"AI 生成失敗：{str(e)}")
        return None


def call_deepseek(prompt, temperature=0.7, json_mode=False):
    """呼叫 DeepSeek API"""
    api_key = st.secrets.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("未設定 DEEPSEEK_API_KEY")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    messages = [
        {"role": "system", "content": "你是一位資深的香港小學中文科老師。請使用繁體中文。"},
        {"role": "user", "content": prompt}
    ]
    
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": messages,
        "temperature": temperature
    }
    
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
        messages[0]["content"] += "請務必以 JSON 格式回傳。"
    
    response = requests.post(DEEPSEEK_API_URL, headers=headers, json=payload)
    response.raise_for_status()
    
    result = response.json()
    return result['choices'][0]['message']['content']


def get_prompt_by_type(question_type, word, full_sentence):
    """根據題型生成 Prompt"""
    base = f"""
任務：請根據句子「{full_sentence}」和關鍵詞「{word}」，製作一道「{question_type}」。
回傳格式：JSON 物件 {{"question": "...", "answer": "..."}}。
"""
    
    prompts = {
        "重組句子": """
1. 請將句子拆解為 **6 到 10 個** 短語區塊。
2. **長度限制**：每個區塊盡量控制在 **2 到 5 個字**。
3. **標點符號保留**：逗號附著在分句最後或獨立成區塊。
4. **嚴格保留專名號**：【】不可拆分。
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
"""
    }
    
    specific = prompts.get(question_type, "請製作適合小學生的題目。")
    return base + "\n" + specific
