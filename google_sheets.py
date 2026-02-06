import gspread
from google.oauth2.service_account import Credentials
import streamlit as st
import pandas as pd

class GoogleSheetsManager:
    def __init__(self):
        self.scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        self._init_client()
    
    def _init_client(self):
        """初始化 Google Sheets 客戶端"""
        try:
            # 從 Streamlit secrets 讀取服務帳戶資訊
            service_account_info = dict(st.secrets["gcp_service_account"])
            
            creds = Credentials.from_service_account_info(
                service_account_info,
                scopes=self.scopes
            )
            self.client = gspread.authorize(creds)
            self.spreadsheet_id = st.secrets["app_config"]["spreadsheet_id"]
            self.spreadsheet = self.client.open_by_key(self.spreadsheet_id)
            st.success("✅ Google Sheets 連接成功！")
        except Exception as e:
            st.error(f"❌ Google Sheets 連接失敗: {e}")
            self.client = None
    
    def get_sheet_data(self, sheet_name: str) -> pd.DataFrame:
        """讀取指定工作表為 DataFrame"""
        try:
            worksheet = self.spreadsheet.worksheet(sheet_name)
            data = worksheet.get_all_values()
            if data:
                df = pd.DataFrame(data[1:], columns=data[0])
                return df
            return pd.DataFrame()
        except Exception as e:
            st.error(f"讀取 {sheet_name} 失敗: {e}")
            return pd.DataFrame()
    
    def write_to_sheet(self, sheet_name: str, data: list):
        """寫入資料到指定工作表"""
        try:
            worksheet = self.spreadsheet.worksheet(sheet_name)
            worksheet.clear()
            if data:
                worksheet.update([data[0]] + data[1:])
            return True
        except Exception as e:
            st.error(f"寫入 {sheet_name} 失敗: {e}")
            return False
    
    def append_to_sheet(self, sheet_name: str, data: list):
        """追加資料到指定工作表"""
        try:
            worksheet = self.spreadsheet.worksheet(sheet_name)
            worksheet.append_rows(data)
            return True
        except Exception as e:
            st.error(f"追加到 {sheet_name} 失敗: {e}")
            return False
