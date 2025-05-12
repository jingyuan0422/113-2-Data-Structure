def user_proxy_agent(ticker, email):
    # 接收使用者的輸入並做回應
    print(f"收到股票代碼：{ticker}, 收到信箱：{email}")

    # 可以將這些資料傳遞給後續的分析Agent或處理
    return f"已收到股票代碼 {ticker}，分析結果會發送至 {email}"