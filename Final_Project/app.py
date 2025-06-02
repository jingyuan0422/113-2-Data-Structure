import os
import asyncio
import pandas as pd
import threading
from dotenv import load_dotenv
import io
import gradio as gr
import streamlit as st
from utils.finance import fetch_stock_data
from utils.agent import analyze_stock, model_client, termination_condition, summarize_with_gemini
from utils.pdf_generator import generate_pdf_report
from utils.add_todolist import add_todolist


# 1. UI 輸入
st.title("📈 Stock Analysis Multi-Agent")
ticker = st.text_input("請輸入美股股票代碼（如 AAPL）")
days = st.number_input("請輸入想要繪製的股價圖天數（90–365）", min_value=90, max_value=365, value=180, step=1)
submit = st.button("開始分析")

# 預設 session_state
if "analysis_data" not in st.session_state:
    st.session_state.analysis_data = None

# 使用者按下分析按鈕
if submit:
    if not ticker:
        st.warning("請輸入完整資訊")
    else:
        with st.spinner("正在分析中..."):
            try:
                # 抓股票資料
                data = fetch_stock_data(ticker.upper(), days=days)

                # 取得 AI 分析訊息
                messages = asyncio.run(analyze_stock(
                    ticker=ticker.upper(),
                    indicators=data["indicators"],
                    model_client=model_client,
                    termination_condition=termination_condition
                ))

                # Gemini 模型整理成表格
                df = asyncio.run(summarize_with_gemini(messages))

                # ✅ 存入 session_state
                st.session_state.analysis_data = {
                    "ticker": ticker.upper(),
                    "days": days,
                    "stock_name": data["name"],
                    "indicators": data["indicators"],
                    "figure": data["figure"],
                    "df": df,
                }

                st.success("✅ 分析完成！請查看下方報告")

            except Exception as e:
                st.error(f"分析失敗：{e}")
                st.session_state.analysis_data = None

# 無論如何，只要有分析結果就顯示
if st.session_state.analysis_data:
    result = st.session_state.analysis_data

    st.subheader(f"{result['stock_name']} 的財務摘要")
    for k, v in result["indicators"].items():
        st.write(f"**{k}**: {v}")

    st.plotly_chart(result["figure"])
    st.subheader("📊 AI 分析報告")

    # 匯出 PDF
    pdf_path = generate_pdf_report(
        result["df"],
        {"ticker": result["ticker"], "days": result["days"]},
        result["indicators"],
        result["figure"]
    )

    # 並排兩個按鈕
    col1, col2 = st.columns([1, 1])

    with col1:
        with open(pdf_path, "rb") as f:
            st.download_button(
                label="📥 下載 PDF 報告",
                data=f,
                file_name=f"{result['ticker']}_AI_分析報告.pdf",
                mime="application/pdf"
            )

    with col2:
        if st.button("📌 加入追蹤清單"):
            try:
                add_todolist(result["ticker"])  # ✅ 呼叫你的任務函式
                st.success("✅ 已成功加入 Todoist 追蹤清單")
            except Exception as e:
                st.error(f"❌ 加入清單失敗：{e}")

    # 顯示報告章節
    section_titles = [
        "一、公司介紹",
        "二、產業介紹",
        "三、財務概況",
        "四、近期新聞整理",
        "五、投資建議"
    ]
    for i, section in enumerate(section_titles):
        st.markdown(f"### {section}")
        column_data = result["df"].iloc[:, i].dropna().tolist()
        for item in column_data:
            if item.strip():
                clean_item = item.lstrip("-• ").strip()
                st.markdown(f"- {clean_item}")