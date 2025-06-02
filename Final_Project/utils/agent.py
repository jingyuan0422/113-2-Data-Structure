import os
import asyncio
import pandas as pd
from dotenv import load_dotenv
import io
import re

from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.messages import TextMessage
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.agents.web_surfer import MultimodalWebSurfer
from autogen_core.models import UserMessage

# 載入環境變數
load_dotenv()
gemini_api_key = os.getenv("GEMINI_API_KEY")

# 初始化模型用戶端
model_client = OpenAIChatCompletionClient(
    model="gemini-2.0-flash",
    api_key=gemini_api_key,
)

termination_condition = TextMentionTermination("exit")

async def analyze_stock(ticker: str, indicators: dict, model_client, termination_condition) -> dict:
    formatted_indicators = "\n".join([f"- {k}: {v}" for k, v in indicators.items()])

    # 建立代理人群組
    user_proxy = UserProxyAgent("user_proxy")
    financial_analyst = AssistantAgent("financial_analyst", model_client)
    news_analyst = MultimodalWebSurfer("news_analyst", model_client)
    strategy_advisor = AssistantAgent("strategy_advisor", model_client)

    team = RoundRobinGroupChat(
        [user_proxy, financial_analyst, news_analyst, strategy_advisor],
        termination_condition=termination_condition
    )

    # prompt 指令
    prompt = f"""
    請針對股票代碼 {ticker} 撰寫一份完整且具深度的投資研究分析報告，
    報告內容請先幫我整理公司介紹、產業介紹、近期新聞整理。
    請整合內部財務數據與外部資訊，確保分析詳盡、資料具時效性。具體要求如下：

    1. 請 MultimodalWebSurfer 搜尋外部網站，蒐集該公司基本資訊，包括其公司介紹、主要產品、主要客戶與合作夥伴
    以及其產業介紹，包括公司所屬產業、競爭對手等等
    2. 請根據以下財務指標：
    {formatted_indicators}
    深入說明該公司的財務狀況，具體分析該公司財務狀況，包括財務比率、營收變化、成本結構、獲利能力等等
    此段以段落文字提出，摘要其財務優勢，300字左右即可

    3. 請 MultimodalWebSurfer 搜尋並彙整過去三至六個月內與該公司相關的重要新聞 3-5 則，
    內容可以包含業務擴張或收縮、產品更新、跨國合作、政策變動影響（如監管、新稅制、補助等）、宏觀經濟與地緣政治因素對公司之潛在影響等等
    
    請所有代理人務必回傳整體報告內容，請使用繁體中文，並避免產出重複內容。
    """

    # 收集所有回覆
    messages = []
    async for event in team.run_stream(task=prompt):
        if isinstance(event, TextMessage):
            # 印出目前哪個 agent 正在運作，方便追蹤
            print(f"[{event.source}] => {event.content}\n")
            messages.append({
                "source": event.source,
                "content": event.content,
                "type": event.type,
                "prompt_tokens": event.models_usage.prompt_tokens if event.models_usage else None,
                "completion_tokens": event.models_usage.completion_tokens if event.models_usage else None
            })
    return messages


async def summarize_with_gemini(messages: list) -> pd.DataFrame:
    api_key = os.getenv('GEMINI_API_KEY')

    # 呼叫 gemini 2.0 模型生成內容
    model_client = OpenAIChatCompletionClient(
        model="gemini-2.0-flash",
        api_key=api_key,
    )

    # 將所有 message 合併成文字
    full_text = "\n".join([msg["content"] for msg in messages if "content" in msg])


    # prompt
    prompt = f"""
    你將收到一段由 AI 代理人生成的投資分析內容，其中可能包含原始指令、冗長敘述、重複資訊或格式不一致之處。
    請你依照以下分類格式進行**內容清理、重新組織與條列，並以[ ]:格式分類儲存，如下**，
    確保資訊清晰、段落正確，方便後續直接使用於正式報告中。

    請輸出以下五個分類段落，並保持標題格式不變：
    [公司介紹]：請以列點方式呈現，整理與公司背景、主要產品與服務、商業模式、地區布局、主要客戶與合作夥伴等有關之內容。
    [產業介紹]：請以列點式方式呈現，整理與該公司所屬產業、市場趨勢、競爭對手等有關資訊。
    [財務概況]：請彙整有關財務指標、營收、獲利、財務比率、現金流等資訊。
    [新聞整理]： 請以條列式將與該公司有關的重要新聞整理，(格式請參考 - 新聞標題：摘要說明)
    [投資建議]： 綜合上述所有資訊，請明確提出對該公司的投資建議，並擇一標示為「買進」、「持有」或「賣出」。請具體說明評估理由，包括但不限於：  
    - 短中長期成長潛力與風險  
    - 財務穩健性與市場競爭力  
    - 市場情緒與估值合理性  
    - 外部環境的機會與威脅

    請僅回傳整理後的內容，請使用**繁體中文**。

    原始內容如下：  
    {full_text}

    """

    user_message = UserMessage(content=prompt, source="user")
    response = await model_client.create([user_message])

    cleaned_text = response.content.strip()

    # 初始化區塊
    company_introduction = []
    industry_introduction = []
    financial_summary = []
    news_collection = []
    investing_suggestion = []

    # 分割並清除空行與空白
    lines = [line.strip() for line in cleaned_text.splitlines() if line.strip()]

    # 初始化狀態
    current_section = None

    for line in lines:
        if "[公司介紹]" in line:
            current_section = "company"
            continue
        elif "[產業介紹]" in line:
            current_section = "industry"
            continue
        elif "[財務概況]" in line:
            current_section = "financial"
            continue
        elif "[新聞整理]" in line:
            current_section = "news"
            continue
        elif "[投資建議]" in line:
            current_section = "suggestion"
            continue

        # 根據目前段落狀態加入對應 list
        if current_section == "company":
            company_introduction.append(line)
        elif current_section == "industry":
            industry_introduction.append(line)
        elif current_section == "financial":
            financial_summary.append(line)
        elif current_section == "news":
            news_collection.append(line)
        elif current_section == "suggestion":
            investing_suggestion.append(line)



    # 整理成 DataFrame
    max_len = max(len(financial_summary), len(news_collection), len(investing_suggestion))
    data = {
        "company": company_introduction + [""] * (max_len - len(company_introduction)),
        "industry": industry_introduction + [""] * (max_len - len(industry_introduction)),
        "financial": financial_summary + [""] * (max_len - len(financial_summary)),
        "news": news_collection + [""] * (max_len - len(news_collection)),
        "suggestion": investing_suggestion + [""] * (max_len - len(investing_suggestion)),
    }

    df = pd.DataFrame(data)
    print(df)
    
    return df