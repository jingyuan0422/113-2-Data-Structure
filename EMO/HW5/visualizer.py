import os
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import seaborn as sns
from snownlp import SnowNLP

matplotlib.use('Agg')
matplotlib.rc('font', family='Microsoft JhengHei')

def visualize_data(data):
    # Convert JSON to DataFrame for easier plotting
    df = pd.DataFrame(data)

    # Plot Sentiment Score and S&P 500 Index
    fig, ax1 = plt.subplots(figsize=(10, 6))

    ax1.set_xlabel('Date')
    ax1.set_ylabel('Sentiment Score', color='tab:blue')
    ax1.plot(df['date'], df['sentiment_score'], color='tab:blue', label='Sentiment Score')

    ax2 = ax1.twinx()
    ax2.set_ylabel('S&P 500 Index', color='tab:red')
    ax2.plot(df['date'], df['sp500_index'], color='tab:red', label='S&P 500 Index')

    fig.tight_layout()
    plt.title('Sentiment Analysis vs S&P 500 Index')
    plt.show()