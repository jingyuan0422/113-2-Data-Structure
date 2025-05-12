import os
import yfinance as yf
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv

# Autogen agents
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.messages import TextMessage
from autogen_ext.agents.web_surfer import MultimodalWebSurfer


# 載入 API 金鑰
load_dotenv()

def get_api_key(key_name: str):
    api_key = os.getenv(key_name)
    if not api_key:
        raise ValueError(f"⚠️ 無法找到 {key_name}，請確認 .env 檔案中有正確設定。")
    return api_key

# 提取 GEMINI API 金鑰
gemini_api_key = get_api_key("GEMINI_API_KEY")

class ModelClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.model_info = self._get_model_info()

    def _get_model_info(self):
        # 確保 model_info 有正確返回模型信息
        return {"function_calling": True, "vision": True}  # 假設你會進行視覺操作


# 存檔路徑
CHART_DIR = os.path.join("Saving", "chart")
REPORT_DIR = os.path.join("Saving", "report")
os.makedirs(CHART_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

class StockAnalysisAssistant:
    def __init__(self, ticker, model_client):
        self.ticker = ticker.upper()
        self.model_client = model_client
        self.plot_path = None
        self.analysis_result = ""
        self.news_summary = ""

    async def run(self):
        # 確保在調用異步方法時，使用 await 等待其完成
        await self._analyze_stock_price()  # 在此處加上 await
        await self._analyze_news()  # 在此處加上 await
        self.save_to_csv()
        return {
            "chart_path": self.plot_path,
            "analysis_result": self.analysis_result,
            "news_summary": self.news_summary
        }

    async def _analyze_stock_price(self):
        end_date = datetime.now(pytz.timezone("UTC"))
        start_date = end_date - timedelta(days=730)
        stock = yf.Ticker(self.ticker)
        hist = stock.history(start=start_date, end=end_date)

        if hist.empty:
            self.analysis_result = "查無股價資料。"
            return

        # 計算指標
        current_price = stock.info.get("currentPrice", hist["Close"].iloc[-1])
        year_high = stock.info.get("fiftyTwoWeekHigh", hist["High"].max())
        year_low = stock.info.get("fiftyTwoWeekLow", hist["Low"].min())
        ma_50 = hist["Close"].rolling(window=50).mean().iloc[-1]
        ma_200 = hist["Close"].rolling(window=200).mean().iloc[-1]

        ytd_start = datetime(end_date.year, 1, 1, tzinfo=pytz.timezone("UTC"))
        ytd_data = hist.loc[ytd_start:]
        if not ytd_data.empty:
            price_change = ytd_data["Close"].iloc[-1] - ytd_data["Close"].iloc[0]
            percent_change = (price_change / ytd_data["Close"].iloc[0]) * 100
        else:
            price_change = percent_change = np.nan

        daily_returns = hist["Close"].pct_change().dropna()
        volatility = daily_returns.std() * np.sqrt(252)

        trend = "Upward" if ma_50 > ma_200 else "Downward" if ma_50 < ma_200 else "Neutral"

        # 輸出分析文字
        self.analysis_result = (
            f"當前股價：${current_price:.2f}\n"
            f"52週最高：${year_high:.2f}\n"
            f"52週最低：${year_low:.2f}\n"
            f"50日移動平均：${ma_50:.2f}\n"
            f"200日移動平均：${ma_200:.2f}\n"
            f"YTD變動：{price_change:.2f}（{percent_change:.2f}%）\n"
            f"波動率：{volatility:.2%}\n"
            f"趨勢：{trend}"
        )

        # 畫圖
        hist["MA_50"] = hist["Close"].rolling(window=50).mean()
        hist["MA_200"] = hist["Close"].rolling(window=200).mean()
        plot_hist = hist.loc[end_date - timedelta(days=365):]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=plot_hist.index, y=plot_hist["Close"], mode='lines', name='Close Price'))
        fig.add_trace(go.Scatter(x=plot_hist.index, y=plot_hist["MA_50"], mode='lines', name='50-Day MA'))
        fig.add_trace(go.Scatter(x=plot_hist.index, y=plot_hist["MA_200"], mode='lines', name='200-Day MA'))
        fig.update_layout(title=f'{self.ticker} Stock Price (Past Year)', xaxis_title="Date", yaxis_title="Price ($)", template="plotly_dark")
        
        self.plot_path = os.path.join(CHART_DIR, f"{self.ticker}_stock_chart.png")
        fig.write_image(self.plot_path)

    async def _analyze_news(self):
        prompt = f"Please search for important news articles related to {self.ticker} stock from the past year. Summarize the key news events."

        # 設置代理人
        news_analyzer = AssistantAgent("news_analyzer", self.model_client)
        web_searcher = MultimodalWebSurfer("news_web_searcher", self.model_client)
        assistant = AssistantAgent("news_summary_writer", self.model_client)
        user_proxy = UserProxyAgent("news_user_proxy")

        # 設置 RoundRobinGroupChat
        local_team = RoundRobinGroupChat(
            participants=[news_analyzer, web_searcher, assistant, user_proxy]
        )

        # 發送搜索請求並處理訊息
        messages = []
        async for event in local_team.run_stream(task=prompt):
            if isinstance(event, TextMessage):
                # 根據實際情況處理輸出
                print(f"[{event.source}] => {event.content}\n")
                messages.append({
                    "source": event.source,
                    "content": event.content,
                    "type": event.type,
                    "prompt_tokens": event.models_usage.prompt_tokens if event.models_usage else None,
                    "completion_tokens": event.models_usage.completion_tokens if event.models_usage else None
                })
        
        # 返回或處理結果
        self.news_summary = "\n".join([msg['content'] for msg in messages])  # 假設最後想用摘要
        return messages

    def save_to_csv(self):
        # 提取分析結果中的各個數據
        analysis_lines = self.analysis_result.split('\n')
        
        # 確保 analysis_lines 有足夠的內容
        stock_data = {
            "Ticker": self.ticker,
            "Current Price": analysis_lines[0].split('：')[1] if len(analysis_lines) > 0 and '：' in analysis_lines[0] else "",
            "52 Week High": analysis_lines[1].split('：')[1] if len(analysis_lines) > 1 and '：' in analysis_lines[1] else "",
            "52 Week Low": analysis_lines[2].split('：')[1] if len(analysis_lines) > 2 and '：' in analysis_lines[2] else "",
            "50 Day MA": analysis_lines[3].split('：')[1] if len(analysis_lines) > 3 and '：' in analysis_lines[3] else "",
            "200 Day MA": analysis_lines[4].split('：')[1] if len(analysis_lines) > 4 and '：' in analysis_lines[4] else "",
            "YTD Change": analysis_lines[5].split('：')[1] if len(analysis_lines) > 5 and '：' in analysis_lines[5] else "",
            "Volatility": analysis_lines[6].split('：')[1] if len(analysis_lines) > 6 and '：' in analysis_lines[6] else "",
            "Trend": analysis_lines[7].split('：')[1] if len(analysis_lines) > 7 and '：' in analysis_lines[7] else "",
            "News Summary": self.news_summary  # 使用從新聞摘要中獲得的結果
        }

        # 將字典轉換為 DataFrame
        df = pd.DataFrame([stock_data])

        # 設定 CSV 存檔路徑
        csv_path = os.path.join(REPORT_DIR, f"{self.ticker}_stock_analysis_report.csv")

        # 將 DataFrame 存為 CSV，不包含索引
        df.to_csv(csv_path, index=False)

        # 確認 CSV 檔案已成功保存
        print(f"Report saved to {csv_path}")


async def main():
    # 從 .env 檔案讀取 GEMINI_API_KEY
    gemini_api_key = os.environ.get("GEMINI_API_KEY")
    if not gemini_api_key:
        print("請檢查 .env 檔案中的 GEMINI_API_KEY。")
        return

    # 初始化模型用戶端
    model_client = ModelClient(gemini_api_key)

    # 初始化 StockAnalysisAssistant 並運行分析
    ticker = "AAPL"  # 這裡可以替換成你想分析的股票代碼
    assistant = StockAnalysisAssistant(ticker, model_client)
    result = await assistant.run()

    # 輸出結果
    print(f"結果已保存到：{result['chart_path']}")
    print(f"分析結果：\n{result['analysis_result']}")
    print(f"新聞摘要：\n{result['news_summary']}")

# 記得運行這個 main 函式
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
