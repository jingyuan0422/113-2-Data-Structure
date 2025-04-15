import os
from datetime import datetime
import requests
import gradio as gr
import pandas as pd
from dotenv import load_dotenv
from fpdf import FPDF
from google import genai
import re

# 載入環境變數並設定 API 金鑰
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

def get_chinese_font_file() -> str:
    """
    只檢查 Windows 系統字型資料夾中是否存在候選中文字型（TTF 格式）。
    若找到則回傳完整路徑；否則回傳 None。
    """
    # HW4 字體路徑更改
    fonts_path = "/Users/jennis/Library/Fonts"
    candidates = ["NotoSansTC-VariableFont_wght.ttf"]  # 這裡以楷體為例，可依需要修改
    for font in candidates:
        font_path = os.path.join(fonts_path, font)
        if os.path.exists(font_path):
            print("找到系統中文字型：", font_path)
            return os.path.abspath(font_path)
    print("未在系統中找到候選中文字型檔案。")
    return None

# HW4 欄寬設定、自動換行
def create_table(pdf: FPDF, df: pd.DataFrame):
    """
    使用 FPDF 將 DataFrame 以漂亮的表格形式繪製至 PDF，
    使用交替背景色與標題區塊，並自動處理分頁。
    """
    # 取得 PDF 可用寬度
    available_width = pdf.w - 2 * pdf.l_margin
    
    # 設定固定寬度
    fixed_width_time = 2 * 10  # 2 cm轉換為毫米（2 cm = 20 mm）
    fixed_width_last = 5 * 10
    
    # 計算剩餘空間
    remaining_width = available_width - 2 * fixed_width_time - fixed_width_last # 三個固定寬度的總和
    third_col_width = remaining_width  # 剩餘寬度分配給第三欄
    
    # 欄寬設定（第一、二、四欄設為固定寬度 2 cm，其餘分配給第三欄）
    col_widths = [fixed_width_time, fixed_width_time, third_col_width, fixed_width_last]
    cell_height = 10  # 單元格的高度
    
    # 表頭
    pdf.set_fill_color(200, 200, 200)
    pdf.set_font("ChineseFont", "", 12)
    for i, col in enumerate(df.columns):
        pdf.cell(col_widths[i], cell_height, str(col), border=1, align="C", fill=True)
    pdf.ln(cell_height)

    # HW4 儲存方式
    # 資料列處理
    fill = False
    for index, row in df.iterrows():
        y_start = pdf.get_y()
        x_start = pdf.get_x()

        # 計算每欄的行數
        max_lines = 1
        col_text_lines = []
        for i, item in enumerate(row):
            text = str(item)
            lines = pdf.multi_cell(col_widths[i], cell_height, text, border=0, align="C", split_only=True)
            col_text_lines.append(lines)
            max_lines = max(max_lines, len(lines))

        total_height = cell_height * max_lines

        # 換頁判斷
        if y_start + total_height > pdf.h - pdf.b_margin:
            pdf.add_page()
            pdf.set_fill_color(200, 200, 200)
            pdf.set_font("ChineseFont", "", 12)
            for i, col in enumerate(df.columns):
                pdf.cell(col_widths[i], cell_height, str(col), border=1, align="C", fill=True)
            pdf.ln(cell_height)
            y_start = pdf.get_y()

        # 背景色切換
        if fill:
            pdf.set_fill_color(230, 240, 255)
        else:
            pdf.set_fill_color(255, 255, 255)

        # 畫出每欄格子
        x = x_start
        for i, lines in enumerate(col_text_lines):
            pdf.set_xy(x, y_start)
            content = '\n'.join(lines + [''] * (max_lines - len(lines)) + [''])
            pdf.multi_cell(col_widths[i], cell_height, content, border=1, align="C", fill=True)
            x += col_widths[i]

        # 換到下一列
        pdf.set_y(y_start + total_height)
        fill = not fill


def parse_markdown_table(markdown_text: str) -> pd.DataFrame:
    """
    從 Markdown 格式的表格文字提取資料，返回一個 pandas DataFrame。
    例如，輸入：
      | start | end | text | 分類 |
      |-------|-----|------|------|
      | 00:00 | 00:01 | 開始拍攝喔 | 備註 |
    會返回包含該資料的 DataFrame。
    """
    lines = markdown_text.strip().splitlines()
    # 過濾掉空行
    lines = [line.strip() for line in lines if line.strip()]
    # 找到包含 '|' 的行，假設這就是表格
    table_lines = [line for line in lines if line.startswith("|")]
    if not table_lines:
        return None
    # 忽略第二行（分隔線）
    header_line = table_lines[0]
    headers = [h.strip() for h in header_line.strip("|").split("|")]
    data = []
    for line in table_lines[2:]:
        row = [cell.strip() for cell in line.strip("|").split("|")]
        if len(row) == len(headers):
            data.append(row)
    df = pd.DataFrame(data, columns=headers)
    return df

def generate_pdf(text: str = None, df: pd.DataFrame = None) -> str:
    print("開始生成 PDF")
    pdf = FPDF(format="A4")
    pdf.add_page()
    
    # 取得中文字型
    chinese_font_path = get_chinese_font_file()
    if not chinese_font_path:
        error_msg = "錯誤：無法取得中文字型檔，請先安裝合適的中文字型！"
        print(error_msg)
        return error_msg
    
    pdf.add_font("ChineseFont", "", chinese_font_path, uni=True)
    pdf.set_font("ChineseFont", "", 12)
    
    if df is not None:
        create_table(pdf, df)
    elif text is not None:
        # 嘗試檢查 text 是否包含 Markdown 表格格式
        if "|" in text:
            # 找出可能的表格部分（假設從第一個 '|' 開始到最後一個 '|'）
            table_part = "\n".join([line for line in text.splitlines() if line.strip().startswith("|")])
            parsed_df = parse_markdown_table(table_part)
            if parsed_df is not None:
                create_table(pdf, parsed_df)
            else:
                pdf.multi_cell(0, 10, text)
        else:
            pdf.multi_cell(0, 10, text)
    else:
        pdf.cell(0, 10, "沒有可呈現的內容")
    
    pdf_filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    print("輸出 PDF 至檔案：", pdf_filename)
    pdf.output(pdf_filename)
    print("PDF 生成完成")
    return pdf_filename

def gradio_handler(csv_file, user_prompt):
    print("進入 gradio_handler")
    if csv_file is not None:
        print("讀取 CSV 檔案")
        df = pd.read_csv(csv_file.name)
        total_rows = df.shape[0]
        block_size = 30
        cumulative_response = ""
        block_responses = []

        for i in range(0, total_rows, block_size):
            block = df.iloc[i:i+block_size]
            block_csv = block.to_csv(index=False)

            prompt = (
                f"以下是CSV資料第 {i+1} 到 {min(i+block_size, total_rows)} 筆：\n"
                f"{block_csv}\n\n請根據以下規則進行分析並產出報表：\n{user_prompt}"
            )

            print("完整 prompt for block:")
            print(prompt)

            response = client.models.generate_content(
                model="gemini-2.5-pro-exp-03-25",
                contents=[{"role": "user", "parts": [prompt]}]
            )

            block_response = response.text.strip()
            cumulative_response += f"區塊 {i//block_size+1}:\n{block_response}\n\n"
            block_responses.append(block_response)

        pdf_path = generate_pdf(text=cumulative_response)
        return cumulative_response, pdf_path

    else:
        context = "未上傳 CSV 檔案。"
        full_prompt = f"{context}\n\n{user_prompt}"
        print("完整 prompt：")
        print(full_prompt)

        response = client.models.generate_content(
            model="gemini-2.5-pro-exp-03-25",
            contents=[{"role": "user", "parts": [full_prompt]}]
        )
        response_text = response.text.strip()
        print("AI 回應：")
        print(response_text)

        pdf_path = generate_pdf(text=response_text)
        return response_text, pdf_path


default_prompt = """請根據以下的規則將每句對話進行分類：

"論點清晰",
"邏輯性（易於理解）",
"互動性",
"延伸議題深度與廣度",
"延伸問題",
"不確定性",
"批判性思維",
"引用其他著作",
"開放式問題",
"總結"

並將所有類別進行統計後產出報表。"""

with gr.Blocks() as demo:
    gr.Markdown("# CSV 報表生成器")
    with gr.Row():
        csv_input = gr.File(label="上傳 CSV 檔案")
        user_input = gr.Textbox(label="請輸入分析指令", lines=10, value=default_prompt)
    output_text = gr.Textbox(label="回應內容", interactive=False)
    output_pdf = gr.File(label="下載 PDF 報表")
    submit_button = gr.Button("生成報表")
    submit_button.click(fn=gradio_handler, inputs=[csv_input, user_input],
                        outputs=[output_text, output_pdf])

demo.launch()