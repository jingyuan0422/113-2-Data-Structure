import os
import asyncio
import pandas as pd
from dotenv import load_dotenv
import re
from autogen_core.models import UserMessage
from autogen_ext.models.openai import OpenAIChatCompletionClient
import plotly.express as px
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score

load_dotenv()

# gemini 針對履歷上的各項經歷做細項評分
async def analyze_resume(resume_text):
    api_key = os.getenv('GEMINI_API_KEY')

    # 呼叫 gemini 2.0 模型生成內容
    model_client = OpenAIChatCompletionClient(
        model="gemini-2.0-flash",
        api_key=api_key,
    )

    prompt = f"""
    請處理以下履歷文本，提取每一項經歷和活動，並按照以下格式輸出：
    經歷，並根據以下標準對每一項經歷進行客觀的評分：
    項目：領導能力、技術能力、溝通與協作能力、創新性、問題解決能力、專業知識、結果導向、時間管理與效率。每項評分範圍是0到10，請提供每項評分。

    格式範例（請每一項用換行分開）：
    經歷：富蘭克林證券投資顧問 研究部實習生
    領導能力：5
    技術能力：8
    溝通與協作能力：7
    創新性：6
    問題解決能力：7
    專業知識：8
    結果導向：7
    時間管理與效率：6

    開始處理以下履歷文本：
    {resume_text}
    """

    user_message = UserMessage(content=prompt, source="user")
    response = await model_client.create([user_message])

    extracted_text = response.content.strip()

    # 正則表達式提取每一筆資料
    experiences = []
    leadership_scores = []
    technical_scores = []
    communication_scores = []
    innovation_scores = []
    problem_solving_scores = []
    knowledge_scores = []
    results_scores = []
    time_management_scores = []

    # 用正則式分批提取
    pattern = re.compile(
        r"經歷：(.*?)\n領導能力：(.*?)\n技術能力：(.*?)\n溝通與協作能力：(.*?)\n創新性：(.*?)\n問題解決能力：(.*?)\n專業知識：(.*?)\n結果導向：(.*?)\n時間管理與效率：(.*?)\n",
        re.DOTALL
    )

    matches = pattern.findall(extracted_text)

    for match in matches:
        experience, leadership, technical, communication, innovation, problem_solving, knowledge, results, time_management = match
        experiences.append(experience.strip())
        leadership_scores.append(int(leadership.strip()))
        technical_scores.append(int(technical.strip()))
        communication_scores.append(int(communication.strip()))
        innovation_scores.append(int(innovation.strip()))
        problem_solving_scores.append(int(problem_solving.strip()))
        knowledge_scores.append(int(knowledge.strip()))
        results_scores.append(int(results.strip()))
        time_management_scores.append(int(time_management.strip()))

    # 整理成DataFrame
    df_experience = pd.DataFrame({
        '經歷': experiences,
        '領導能力': leadership_scores,
        '技術能力': technical_scores,
        '溝通與協作能力': communication_scores,
        '創新性': innovation_scores,
        '問題解決能力': problem_solving_scores,
        '專業知識': knowledge_scores,
        '結果導向': results_scores,
        '時間管理與效率': time_management_scores
    })
    print(df_experience)
    return df_experience

def analyze_with_kmeans_pca(df_experience):
    
    # 去掉'經歷' 欄位，因為不是數值型
    features = df_experience.drop(columns=["經歷"])

     # 標準化
    scaler = StandardScaler()
    scaled_features = scaler.fit_transform(features)

    # KMeans
    kmeans = KMeans(n_clusters=5, random_state=0)
    df_experience["cluster"] = kmeans.fit_predict(scaled_features)
    
    # PCA
    pca = PCA(n_components=2)
    pca_result = pca.fit_transform(scaled_features)
    df_experience['pca1'] = pca_result[:, 0]
    df_experience['pca2'] = pca_result[:, 1]

    # Visualization
    fig = px.scatter(
        df_experience,
        x='pca1',
        y='pca2',
        color='cluster',
        title="PCA of Resume Experiences",
        labels={'pca1': 'Principal Component 1', 'pca2': 'Principal Component 2', 'cluster': 'Cluster Group'},
        hover_data=['經歷', '領導能力', '技術能力', '溝通與協作能力', '創新性', '問題解決能力','專業知識', '結果導向', '時間管理與效率' ]
    )

    # Update chart layout
    fig.update_layout(
        xaxis_title="Principal Component 1",
        yaxis_title="Principal Component 2",
        legend_title="Group",
        title_x=0.5,  # Center the chart title
        height=600,
        width=800
    )

    return fig

async def analyze_clusters_with_gemini(df_experience):
    api_key = os.getenv('GEMINI_API_KEY')

    model_client = OpenAIChatCompletionClient(
        model="gemini-2.0-flash",
        api_key=api_key,
    )

    # 整理要輸入的分析資料
    cluster_summary = ""
    for cluster_num in sorted(df_experience["cluster"].unique()):
        cluster_data = df_experience[df_experience["cluster"] == cluster_num]
        cluster_summary += f"\n=== Cluster {cluster_num} ===\n"
        cluster_summary += cluster_data[[
            '經歷', '領導能力', '技術能力', '溝通與協作能力', '創新性',
            '問題解決能力', '專業知識', '結果導向', '時間管理與效率'
        ]].to_string(index=False)
        cluster_summary += "\n"

    prompt = f"""
以下是履歷經歷資料經過 PCA 和 KMeans 聚類後的分析結果，請你根據 cluster 的整體特性，歸納使用者的主要職涯特質與優勢。不需要逐條描述每一段經歷，請直接綜合分析並提供有結構的中文結論。

請回應以下幾點：
1. 根據各 cluster 的特性，概括使用者的經歷重點與技能強項。
2. 提出整體職涯潛力的判斷，請在以下五種類型中，選出最符合使用者的1-2個類型，並說明理由：
   - 工程分析者（技術、專業知識、問題解決高，適合學術或技術導向工作）
   - 溝通型領導者（領導力與溝通強，適合團隊協作與活動規劃）
   - 創新驅動者（創新與結果導向高，擅長提出專案與新點子）
   - 全能均衡者（能力平均、表現穩定，具備通才潛力）
   - 實務行動者（重視執行與效率，實習與實作經驗豐富）

3. 點出使用者1–2項最具代表性的亮點經歷（不需詳述，只需點出特色與貢獻面向），說明為何值得關注，及其對職涯的發展潛力。

分析資料如下：
{cluster_summary}
"""


    user_message = UserMessage(content=prompt, source="user")
    response = await model_client.create([user_message])

    return response.content.strip()

# 合併 analyze_resume、analyze_with_kmeans_pca、analyze_clusters_with_gemini
async def run_analysis(resume_text):
    # 提取履歷數據
    df_experience = await analyze_resume(resume_text)

    # 執行 KMeans 與 PCA 分析
    fig = analyze_with_kmeans_pca(df_experience)

    # Gemini 對 cluster 結果進行解釋與分析
    cluster_analysis = await analyze_clusters_with_gemini(df_experience)

    # 返回所有分析結果
    return df_experience, fig, cluster_analysis
