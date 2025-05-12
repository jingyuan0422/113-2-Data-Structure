import os
import asyncio
import pandas as pd
from dotenv import load_dotenv
import io
import gradio as gr
from dotenv import load_dotenv
from Utils.api_utils import get_api_key
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.messages import TextMessage
from autogen_ext.agents.web_surfer import MultimodalWebSurfer
from Agents.user_proxy import user_proxy_agent
from Agents.stock_analysis import StockAnalysisAssistant, ModelClient

# 載入 API 金鑰
load_dotenv()
gemini_api_key = get_api_key("GEMINI_API_KEY")

# 初始化 ModelClient，這個步驟假設 ModelClient 需要被初始化
model_client = ModelClient(gemini_api_key)

# 暫時只做基本輸入畫面
async def handle_user_input(ticker, email):
    # User Proxy Agent
    user_response = user_proxy_agent(ticker, email)
    
    # StockAnalysisAssistant 進行分析，並傳遞 model_client 參數
    # stock_analysis = StockAnalysisAssistant(ticker, model_client=model_client)
    # analysis_result = await stock_analysis.run()
    
    # 回傳結合結果（股價分析結果 + 用戶代理回應）
    return user_response
# f"股價分析結果:\n{analysis_result['analysis_result']}\n\n" + f"代理回應:\n{user_response}"


# Gradio UI 設計
with gr.Blocks() as demo:
    gr.Markdown("# 📈 股票自動分析系統")
    stock_input = gr.Textbox(label="請輸入美股代碼（如 AAPL）")
    email_input = gr.Textbox(label="請輸入您的信箱")
    submit_btn = gr.Button("送出查詢")
    output_text = gr.Textbox(label="系統回覆")

    # 使用 async 函數處理回應
    submit_btn.click(fn=handle_user_input, inputs=[stock_input, email_input], outputs=output_text)

# 執行
if __name__ == "__main__":
    demo.launch()
