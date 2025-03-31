import os
import asyncio
import pandas as pd
from dotenv import load_dotenv
import io

# 根據你的專案結構調整下列 import
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.messages import TextMessage
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.agents.web_surfer import MultimodalWebSurfer


load_dotenv()

# HW1 指令修改
async def process_chunk(chunk, start_idx, total_records, model_client, termination_condition):
    """
    Process a single batch of data:
      - Convert the batch data into a dictionary format.
      - Generate a prompt for agents to analyze the given data and provide investment insights.
      - Use the MultimodalWebSurfer agent to search external sources for relevant market news,
        including major economic events, government policies, and financial trends, and integrate the findings into the analysis.
      - Collect and return all agent responses.
    """


    # 將資料轉成 dict 格式
    chunk_data = chunk.to_dict(orient='records')
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
    "All agents should collaborate to deliver a thorough and valuable investment analysis, ensuring that recommendations are well-supported by data and market insights."
)


    
    # 為每個批次建立新的 agent 與 team 實例
    local_data_agent = AssistantAgent("data_agent", model_client)
    local_web_surfer = MultimodalWebSurfer("web_surfer", model_client)
    local_assistant = AssistantAgent("assistant", model_client)
    local_user_proxy = UserProxyAgent("user_proxy")
    local_team = RoundRobinGroupChat(
        [local_data_agent, local_web_surfer, local_assistant, local_user_proxy],
        termination_condition=termination_condition
    )
    
    messages = []
    async for event in local_team.run_stream(task=prompt):
        if isinstance(event, TextMessage):
            # 印出目前哪個 agent 正在運作，方便追蹤
            print(f"[{event.source}] => {event.content}\n")
            messages.append({
                "batch_start": start_idx,
                "batch_end": start_idx + len(chunk) - 1,
                "source": event.source,
                "content": event.content,
                "type": event.type,
                "prompt_tokens": event.models_usage.prompt_tokens if event.models_usage else None,
                "completion_tokens": event.models_usage.completion_tokens if event.models_usage else None
            })
    return messages

async def main():
    gemini_api_key = os.environ.get("GEMINI_API_KEY")
    if not gemini_api_key:
        print("請檢查 .env 檔案中的 GEMINI_API_KEY。")
        return

    # 初始化模型用戶端 (此處示範使用 gemini-2.0-flash)
    model_client = OpenAIChatCompletionClient(
        model="gemini-2.0-flash",
        api_key=gemini_api_key,
    )
    
    termination_condition = TextMentionTermination("exit")
    
    # HW1 CSV 檔案修改
    # 使用 pandas 以 chunksize 方式讀取 CSV 檔案
    csv_file_path = "S&P500_and_Sectors.csv"
    chunk_size = 10000
    chunks = list(pd.read_csv(csv_file_path, chunksize=chunk_size))
    total_records = sum(chunk.shape[0] for chunk in chunks)
    
    # 利用 map 與 asyncio.gather 同時處理所有批次（避免使用傳統 for 迴圈）
    tasks = list(map(
        lambda idx_chunk: process_chunk(
            idx_chunk[1],
            idx_chunk[0] * chunk_size,
            total_records,
            model_client,
            termination_condition
        ),
        enumerate(chunks)
    ))
    
    results = await asyncio.gather(*tasks)
    # 將所有批次的訊息平坦化成一個清單
    all_messages = [msg for batch in results for msg in batch]
    
    # 將對話紀錄整理成 DataFrame 並存成 CSV
    df_log = pd.DataFrame(all_messages)
    output_file = "all_conversation_log.csv"
    df_log.to_csv(output_file, index=False, encoding="utf-8-sig")
    print(f"已將所有對話紀錄輸出為 {output_file}")

def new_func():
    return 1000

if __name__ == '__main__':
    asyncio.run(main())