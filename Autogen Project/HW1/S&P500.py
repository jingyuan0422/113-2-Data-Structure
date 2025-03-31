import yfinance as yf
import os

# S&P 500 index and sector ETFs
sectors = {
    "S&P500": "^GSPC",
    "Technology": "XLK",
    "Financials": "XLF",
    "Healthcare": "XLV",
    "Consumer Discretionary": "XLY",
    "Energy": "XLE",
    "Utilities": "XLU",
    "Materials": "XLB",
    "Real Estate": "XLRE",
    "Communication Services": "XLC",
    "Industrials": "XLI",
    "Infrastructure": "XLI",
}

# Set the date range for downloading data
start_date = "2021-12-31"
end_date = "2024-12-31"

# Download data for each sector and S&P 500, then save as CSV
for sector, ticker in sectors.items():
    print(f"Downloading data for {sector} ({ticker})...")
    data = yf.download(ticker, start=start_date, end=end_date)
    
    # Save as a CSV file in the current directory
    csv_filename = f"{sector}_data.csv"
    
    # Show the file's save path
    print(f"CSV file will be saved at: {os.path.abspath(csv_filename)}")
    
    # Save the CSV file
    data.to_csv(csv_filename)
    print(f"{sector} data has been saved as {csv_filename} ✅\n")
