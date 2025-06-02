import yfinance as yf
import plotly.graph_objs as go
import datetime

def fetch_stock_data(ticker: str, days: int = 180):
    stock = yf.Ticker(ticker)

    # 公司基本資訊
    info = stock.info
    name = info.get("longName", "N/A")

    indicators = {
        "公司名稱": name,
        "市值 (Market Cap)": f"{info.get('marketCap', 0):,}",
        "本益比 (PE Ratio)": info.get("trailingPE", "N/A"),
        "每股盈餘 (EPS)": info.get("trailingEps", "N/A"),
        "殖利率 (Dividend Yield)": f"{round(info.get('dividendYield', 0) * 100, 2)}%" if info.get("dividendYield") else "N/A",
        "Beta 值": info.get("beta", "N/A"),
        "52週最高價": info.get("fiftyTwoWeekHigh", "N/A"),
        "52週最低價": info.get("fiftyTwoWeekLow", "N/A")
    }

    # 時間範圍
    end = datetime.datetime.today()
    start = end - datetime.timedelta(days=days + 300)
    hist = stock.history(start=start, end=end)

    # 移動平均線
    hist["MA20"] = hist["Close"].rolling(window=20).mean()
    hist["MA60"] = hist["Close"].rolling(window=60).mean()

    # 畫圖
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hist.index, y=hist["Close"], name="收盤價", line=dict(color="blue")))
    fig.add_trace(go.Scatter(x=hist.index, y=hist["MA20"], name="20日均線", line=dict(color="orange")))
    fig.add_trace(go.Scatter(x=hist.index, y=hist["MA60"], name="60日均線", line=dict(color="green")))
    fig.update_layout(title=f"{ticker} 過去股價走勢", xaxis_title="日期", yaxis_title="價格", template="plotly_white")

    return {
        "name": name,
        "indicators": indicators,
        "figure": fig
    }
