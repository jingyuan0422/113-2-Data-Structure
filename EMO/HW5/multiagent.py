import os
import io
import asyncio
import json
import pandas as pd
from dotenv import load_dotenv, find_dotenv
from flask_socketio import SocketIO
from google import genai

# 根據你的專案結構調整下列 import
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.messages import TextMessage
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.agents.web_surfer import MultimodalWebSurfer


# ✅ 載入 .env 並啟用 Gemini 原生用法
dotenv_path = find_dotenv()
print(f"✅ 目前使用的 .env 路徑: {dotenv_path}")
load_dotenv(dotenv_path)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
print(GEMINI_API_KEY)

# ✅ 使用 Gemini 原生 client
client = genai.Client(api_key=GEMINI_API_KEY)

# ✅ 封裝成符合 autogen agentchat 的結構
class GeminiChatCompletionClient:
    def __init__(self, model="gemini-2.0-flash"):
        self.model = model
        self.model_info = {"vision": False}  # ✅ 避免 autogen 出錯

    async def create(self, messages, **kwargs):
        parts = []
        for m in messages:
            if hasattr(m, 'content'):
                parts.append(str(m.content))
            elif isinstance(m, dict) and 'content' in m:
                parts.append(str(m['content']))
        content = "\n".join(parts)
        response = client.models.generate_content(
            model=self.model,
            contents=content
        )
        #print("📨 Gemini 回應內容：", response)
        return type("Response", (), {
            "text": response.text,
            "content": response.text,
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0
            }
        })

# ✅ 初始化封裝後的 Gemini client
model_client = GeminiChatCompletionClient()

# HW5 程式修改
# ✅ Investment Insight 分析任務 - 單批次處理
async def process_chunk(socketio: SocketIO, chunk, start_idx, total_records, model_client, termination_condition):
    """
    Process a single data batch and generate investment insights based on historical S&P 500 data:
      - Convert the data into JSON format
      - Create a multi-layered prompt for analysis (including data analysis and integration of external sources)
      - Use multiple AI agents to collaborate and generate in-depth investment insights
      - Send the analysis process and final recommendations to the frontend in real-time
    """

    # 將資料轉為 dict 列表格式
    chunk_data = chunk.to_dict(orient='records')
    if len(chunk_data) > 5:
        preview_data = json.dumps(chunk_data[:5], ensure_ascii=False, indent=2, default=str) + "\n... (以下省略)"
    else:
        preview_data = json.dumps(chunk_data, ensure_ascii=False, indent=2, default=str)

    # 建立分析提示語句
    prompt = (
    f"Currently processing records {start_idx} to {start_idx + len(chunk) - 1} (out of {total_records}).\n"
    f"Here is the data for this batch:\n{chunk_data}\n\n"
    "Please analyze the given S&P 500 data (including S&P 500 and its 11 industry sectors from 2021 to 2024) and provide a comprehensive investment analysis. "
    "Specifically, focus on the following aspects:\n"
    "  1. Identify key factors driving the S&P 500's growth or decline over the given period, including macroeconomic trends, monetary policy, inflation, and geopolitical events.\n"
    "  2. Use MultimodalWebSurfer to search external sources for major economic events, government policies, and global financial trends that influenced the market each year, "
    "     such as interest rate changes, fiscal stimulus, supply chain disruptions, or major corporate earnings reports, and integrate these findings into your analysis.\n"
    "  3. Provide an asset allocation strategy based on the historical performance and risk profile of different industry sectors. "
    "     Consider factors such as sector rotation, market cycles, and risk-adjusted returns.\n"
    "  4. Assess potential risks associated with investing in specific industries or assets, explaining why these risks exist. "
    "     Consider economic downturns, regulatory changes, global crises, or sector-specific vulnerabilities.\n"
    "  5. If the user inquires about potential risks and major influencing events related to investing in specific assets, ensure the response is data-driven, incorporating "
    "     real-world statistics, historical trends, and expert opinions.\n"
    "  6. Provide a market sentiment analysis, assessing the overall mood of the market, including investor sentiment, market outlook, and major influencing factors that could impact future investment decisions.\n"
    "All agents should collaborate to deliver a thorough and valuable investment analysis, ensuring that recommendations are well-supported by data and market insights."
)

    # 設定代理人角色
    data_agent = AssistantAgent(
        name="data_agent",
        model_client=model_client,
        system_message="You are a data analysis expert, skilled at identifying trends and key changes from historical financial data."
    )
    web_surfer = MultimodalWebSurfer(
        name="web_surfer",
        model_client=model_client,
        system_message="You are a market intelligence expert, specializing in searching for external sources to supplement the analysis with real-time market information."
    )
    strategist = AssistantAgent(
        name="assistant",
        model_client=model_client,
        system_message="You are an asset allocation strategist, skilled at synthesizing various inputs to provide actionable investment advice."
    )
    sentiment_analyzer = AssistantAgent(
        name="sentiment_analyzer",
        model_client=model_client,
        system_message="You are a market sentiment analyst, focused on evaluating the psychological and emotional factors driving market movements."
    )
    user_proxy = UserProxyAgent(name="user_proxy")

    display_names = {
        "data_agent": "Data Analyst",
        "web_surfer": "Market Intelligence",
        "assistant": "Strategy Consultant",
        "sentiment_analyzer": "Sentiment Analyst",
        "user_proxy": "User"
    }

    # 建立對話小組
    team = RoundRobinGroupChat(
        [data_agent, web_surfer, strategist, sentiment_analyzer, user_proxy],
        termination_condition=termination_condition
    )

    messages = []
    try:
        async for event in team.run_stream(task=prompt):
            if isinstance(event, TextMessage):
                display_name = display_names.get(event.source, event.source)
                message_text = f"🤖 [{display_name}]：{event.content}"

                if len(message_text) > 1500:
                    formatted_text = message_text[:1500] + "... (Content too long)"
                else:
                    formatted_text = message_text

                # 傳送至前端
                socketio.emit('update', {
                    'message': formatted_text,
                    'source': event.source,
                    'tag': 'analysis'
                })

                messages.append({
                    "batch_start": start_idx,
                    "batch_end": start_idx + len(chunk) - 1,
                    "source": event.source,
                    "content": event.content,
                    "type": event.type,
                    "prompt_tokens": event.models_usage.prompt_tokens if event.models_usage else None,
                    "completion_tokens": event.models_usage.completion_tokens if event.models_usage else None
                })
    except asyncio.exceptions.CancelledError:
        pass

    return messages

# HW5 程式修改
async def run_multiagent_analysis(socketio: SocketIO, user_id, user_entries, model_client, termination_condition):
    socketio.emit('update', {
        'message': '🤖 System: Starting collaboration between analysis expert and AI coach...',
        'tag': 'analysis'
    })
    
    await process_chunk(socketio, user_entries, 0, len(user_entries), model_client, termination_condition)
