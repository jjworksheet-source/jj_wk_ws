"""
Google Sheets 客戶端：處理所有與試算表的互動
"""

import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from config import SHEET_NAMES
import pandas as pd


class SheetsClient:
    def __init__(self):
        """初始化 Google Sheets 連接"""
        self.gc = self._authenticate()
        self.spreadsheet_id = st.secrets["SPREADSHEET_ID"]
        self.spreadsheet = self.gc.open_by_key(self.spreadsheet_id)
    
    def _authenticate(self):
        """使用 Service Account 認證"""
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        credentials = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=scopes
        )
        
        return gspread.authorize(credentials)
    
    def get_sheet(self, sheet_name):
        """取得指定工作表"""
        try:
            return self.spreadsheet.worksheet(sheet_name)
        except gspread.exceptions.WorksheetNotFound:
            st.error(f"找不到工作表：{sheet_name}")
            return None
    
    def read_sheet_as_df(self, sheet_name, header_row=1):
        """讀取工作表為 DataFrame (使用欄位名稱)"""
        sheet = self.get_sheet(sheet_name)
        if not sheet:
            return pd.DataFrame()
        
        data = sheet.get_all_records(head=header_row)
        return pd.DataFrame(data)
    
    def append_rows(self, sheet_name, rows):
        """批次新增多列資料"""
        sheet = self.get_sheet(sheet_name)
        if sheet and rows:
            sheet.append_rows(rows, value_input_option='USER_ENTERED')
    
    def update_cell(self, sheet_name, row, col, value):
        """更新單一儲存格 (row/col 從 1 開始)"""
        sheet = self.get_sheet(sheet_name)
        if sheet:
            sheet.update_cell(row, col, value)
    
    def update_range(self, sheet_name, range_a1, values):
        """更新指定範圍 (A1 notation)"""
        sheet = self.get_sheet(sheet_name)
        if sheet:
            sheet.update(range_a1, values, value_input_option='USER_ENTERED')
    
    def clear_rows(self, sheet_name, start_row, end_row):
        """清空指定列範圍"""
        sheet = self.get_sheet(sheet_name)
        if sheet:
            range_a1 = f"A{start_row}:Z{end_row}"
            sheet.batch_clear([range_a1])
    
    def get_column_index(self, sheet_name, column_name):
        """根據欄位名稱取得欄位索引 (從 1 開始)"""
        sheet = self.get_sheet(sheet_name)
        if not sheet:
            return None
        
        headers = sheet.row_values(1)
        try:
            return headers.index(column_name) + 1
        except ValueError:
            st.error(f"找不到欄位：{column_name}")
            return None
