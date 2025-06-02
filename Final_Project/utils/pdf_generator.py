import os
import textwrap
from fpdf import FPDF
from datetime import datetime
from tempfile import NamedTemporaryFile

def find_chinese_font():
    # 優先使用本地相對路徑的字體
    local_font_path = "./fonts/Arial Unicode.ttf"
    if os.path.exists(local_font_path):
        print("✅ 找到本地中文字型：", os.path.abspath(local_font_path))
        return os.path.abspath(local_font_path)

    # macOS 系統字體備援
    system_font_path = "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"
    if os.path.exists(system_font_path):
        print("✅ 找到系統中文字型：", system_font_path)
        return system_font_path

    print("❌ 無法找到中文字型。")
    return None

def wrap_text(text, width=50):
    return "\n".join(textwrap.wrap(text, width))

class PDFReport(FPDF):
    def __init__(self, font_path):
        super().__init__()
        self.font_path = font_path
        self.set_auto_page_break(auto=True, margin=15)

        # 載入中文字型
        self.add_font('CustomFont', '', font_path, uni=True)
        self.set_font('CustomFont', '', 14)

        self.add_page()
        print("✅ PDF 初始化完成")

    def header(self):
        self.set_font('CustomFont', '', 18)
        self.cell(0, 10, '投資研究分析報告', ln=True, align='C')
        self.ln(5)

    def add_text(self, title, text_list):
        self.set_font('CustomFont', '', 14)
        self.cell(0, 10, title, ln=True)
        self.set_font('CustomFont', '', 10)
        for text in text_list:
            self.multi_cell(0, 8, f"- {text}")
        self.ln(5)

    def add_paragraph(self, text):
        self.set_font('CustomFont', '', 10)
        self.multi_cell(0, 8, text)
        self.ln(5)

    def insert_image(self, image_path, width=180):
        self.image(image_path, w=width)
        self.ln(5)

def generate_pdf_report(df, user_inputs, indicators_dict, figure):
    font_path = find_chinese_font()
    if not font_path:
        raise FileNotFoundError("❌ 找不到中文字型檔案，請確認字體已安裝或路徑正確")

    pdf = PDFReport(font_path)

    # 使用者資訊
    pdf.set_font('CustomFont', '', 14)
    pdf.cell(0, 10, f"股票代碼：{user_inputs['ticker']}", ln=True)
    pdf.ln(5)

    # 公司指標摘要
    pdf.set_font('CustomFont', '', 14)
    pdf.cell(0, 10, "公司財務摘要", ln=True)
    pdf.set_font('CustomFont', '', 10)
    for k, v in indicators_dict.items():
        text = f"- {k}: {v}"
        wrapped_text = wrap_text(text)
        pdf.multi_cell(0, 8, wrapped_text)

    # 插入圖表圖片
    with NamedTemporaryFile(delete=False, suffix=".png") as tmpfile:
        figure.write_image(tmpfile.name)
        pdf.insert_image(tmpfile.name)
        os.unlink(tmpfile.name)

    # 分析報告區塊
    section_titles = [
        "一、公司介紹",
        "二、產業介紹",
        "三、財務概況",
        "四、近期新聞整理",
        "五、投資建議"
    ]
    for i, section in enumerate(section_titles):
        column_data = df.iloc[:, i].dropna().tolist()
        if column_data:
            pdf.add_text(section, column_data)

    # 儲存
    if not os.path.exists("output"):
        os.makedirs("output")
    filename = f"output/report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf.output(filename)

    return filename