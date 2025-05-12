import pandas as pd
import streamlit as st
import asyncio
import plotly.express as px
from utils.pdf_reader import extract_text_from_pdf
from utils.resume_analyzer import run_analysis

# 顯示平台標題
st.title("🔍 ResuAI 智慧履歷分析平台")
st.markdown("上傳履歷，立即獲得個人專屬建議")

# 使用者上傳 PDF 檔案
uploaded_file = st.file_uploader("上傳履歷 PDF", type=["pdf"])

if uploaded_file is not None:
    # 提取 PDF 文字
    resume_text = extract_text_from_pdf(uploaded_file)
    
    # 顯示提取的文字（可選）
    st.write("履歷文字內容：")
    st.text(resume_text)


    if st.button("履歷屬性分析"):
        async def run():
            # 這裡直接呼叫整合好的分析函數
            df_experience, fig, cluster_analysis = await run_analysis(resume_text)

            st.write("履歷屬性分析結果：")
            st.dataframe(df_experience)

            st.plotly_chart(fig)

            st.markdown("### 履歷屬性分析結果說明")
            st.markdown(cluster_analysis)

        asyncio.run(run())