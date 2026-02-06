"""
核心業務邏輯：匯入詞語、生成題目、分流搬移
"""

import streamlit as st
import pandas as pd
from config import *
from ai_service import generate_sentence_by_ai, generate_question_by_ai
import re
from datetime import datetime


class Pipeline:
    def __init__(self, sheets_client):
        self.client = sheets_client
    
    def import_new_words(self):
        """步驟 1：從家長申請匯入新詞"""
        st.info("🔄 開始匯入新詞...")
        
        # 讀取表單與題庫
        form_df = self.client.read_sheet_as_df(SHEET_NAMES['form'])
        tm_df = self.client.read_sheet_as_df(SHEET_NAMES['tm'])
        
        # 建立題庫查詢字典
        tm_dict = dict(zip(tm_df[TM_COLUMNS['word']], tm_df[TM_COLUMNS['sentence']]))
        
        # 篩選未處理的資料
        pending = form_df[form_df[FORM_COLUMNS['status']] != STATUS['done']]
        
        if pending.empty:
            st.warning("沒有發現新的表單回應。")
            return
        
        new_review_rows = []
        rows_to_update = []
        
        for idx, row in pending.iterrows():
            timestamp = row[FORM_COLUMNS['timestamp']]
            school = row[FORM_COLUMNS['school']]
            raw_words = str(row[FORM_COLUMNS['words']])
            
            # 分割詞語
            words = re.split(r'[,，\s、]+', raw_words)
            
            for word in words:
                word = word.strip()
                if not word:
                    continue
                
                # 查詢或生成例句
                if word in tm_dict:
                    sentence = tm_dict[word]
                else:
                    sentence = generate_sentence_by_ai(word)
                
                new_review_rows.append([
                    timestamp, school, word, sentence, '', '', ''
                ])
            
            rows_to_update.append(idx)
        
        # 寫入 Review
        if new_review_rows:
            self.client.append_rows(SHEET_NAMES['review'], new_review_rows)
            
            # 更新表單狀態為 Done
            status_col = self.client.get_column_index(
                SHEET_NAMES['form'], 
                FORM_COLUMNS['status']
            )
            
            for idx in rows_to_update:
                row_num = idx + 2  # DataFrame index + header
                self.client.update_cell(
                    SHEET_NAMES['form'], 
                    row_num, 
                    status_col, 
                    STATUS['done']
                )
            
            st.success(f"✅ 成功匯入 {len(new_review_rows)} 個新詞彙！")
        else:
            st.warning("沒有有效的詞語可匯入。")
    
    def generate_questions(self):
        """步驟 2：生成下週題目 (AI)"""
        st.info("🤖 開始生成 AI 題目...")
        
        review_df = self.client.read_sheet_as_df(SHEET_NAMES['review'])
        
        # 篩選條件：有題型 + 題目欄空白 + 句子不含 AI 圖示
        mask = (
            (review_df[REVIEW_COLUMNS['next_type']] != '') &
            (review_df[REVIEW_COLUMNS['next_question']] == '') &
            (~review_df[REVIEW_COLUMNS['sentence']].str.contains(AI_ICON, na=False))
        )
        
        to_process = review_df[mask]
        
        if to_process.empty:
            st.warning("沒有需要處理的題目。")
            return
        
        progress_bar = st.progress(0)
        total = len(to_process)
        processed = 0
        
        for idx, row in to_process.iterrows():
            word = row[REVIEW_COLUMNS['word']]
            sentence = row[REVIEW_COLUMNS['sentence']]
            q_type = row[REVIEW_COLUMNS['next_type']]
            
            # 還原完整句子
            full_sentence = re.sub(r'_+|＿+|【.*?】', word, sentence)
            
            # 呼叫 AI
            result = generate_question_by_ai(word, full_sentence, q_type)
            
            if result:
                row_num = idx + 2
                q_col = self.client.get_column_index(SHEET_NAMES['review'], REVIEW_COLUMNS['next_question'])
                a_col = self.client.get_column_index(SHEET_NAMES['review'], REVIEW_COLUMNS['next_answer'])
                
                self.client.update_cell(SHEET_NAMES['review'], row_num, q_col, AI_ICON + result['question'])
                self.client.update_cell(SHEET_NAMES['review'], row_num, a_col, result['answer'])
            
            processed += 1
            progress_bar.progress(processed / total)
        
        st.success(f"✅ 成功生成 {processed} 題！")
    
    def move_to_standby(self):
        """步驟 3：移交至 Standby"""
        st.info("📤 開始移交至 Standby...")
        
        review_df = self.client.read_sheet_as_df(SHEET_NAMES['review'])
        
        # 篩選條件：有學校、詞語、本週題目
        mask = (
            (review_df[REVIEW_COLUMNS['school']] != '') &
            (review_df[REVIEW_COLUMNS['word']] != '') &
            (review_df[REVIEW_COLUMNS['sentence']] != '')
        )
        
        # 如果有選題型，必須已生成題目
        has_type = review_df[REVIEW_COLUMNS['next_type']] != ''
        has_question = review_df[REVIEW_COLUMNS['next_question']] != ''
        mask = mask & (~has_type | has_question)
        
        to_move = review_df[mask]
        
        if to_move.empty:
            st.warning("沒有可移交的資料。")
            return
        
        standby_rows = []
        rows_to_clear = []
        today = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        for idx, row in to_move.iterrows():
            school = row[REVIEW_COLUMNS['school']]
            word = row[REVIEW_COLUMNS['word']]
            sentence = row[REVIEW_COLUMNS['sentence']]
            next_type = row[REVIEW_COLUMNS['next_type']]
            next_q = row[REVIEW_COLUMNS['next_question']]
            next_a = row[REVIEW_COLUMNS['next_answer']]
            
            unique_base = f"{school}_{int(datetime.now().timestamp())}_{idx}"
            
            # 雙胞胎 1：本週填空題
            standby_rows.append([
                f"{unique_base}_f", school, word, '填空題', 
                sentence, word, STATUS['ready'], today
            ])
            
            # 雙胞胎 2：下週變化題 (若有)
            if next_q:
                standby_rows.append([
                    f"{unique_base}_o", school, word, next_type,
                    next_q, next_a, STATUS['waiting'], today
                ])
            
            rows_to_clear.append(idx + 2)
        
        # 寫入 Standby
        self.client.append_rows(SHEET_NAMES['standby'], standby_rows)
        
        # 清空 Review
        for row_num in rows_to_clear:
            self.client.clear_rows(SHEET_NAMES['review'], row_num, row_num)
        
        st.success(f"✅ 成功移交 {len(standby_rows)} 筆題目至 Standby！")
