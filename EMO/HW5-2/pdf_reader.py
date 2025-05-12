import pdfplumber
import os

def extract_text_from_pdf(file):
    """
    讀取PDF檔案，提取文字並返回。

    Args:
        file: Streamlit 上傳的 file-like object 或檔案路徑

    Returns:
        text (str): 萃取出來的完整文字
    """
    text = ""
    try:
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        print(f"讀取PDF時發生錯誤: {e}")
        return None

    return text
