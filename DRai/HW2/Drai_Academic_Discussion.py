import os
import json
import time
import pandas as pd
import sys
from dotenv import load_dotenv
from google import genai
from google.genai.errors import ServerError

# 載入 .env 中的 GEMINI_API_KEY
load_dotenv()

# HW2 Items change info
# 定義評分項目（依據原始 xlsx 編碼規則）
ITEMS = [
    "論點清晰",
    "邏輯性（易於理解）",
    "互動性",
    "延伸議題深度與廣度",
    "延伸問題",
    "不確定性",
    "批判性思維",
    "引用其他著作",
    "開放式問題",
    "總結"
]

def parse_response(response_text):
    """
    嘗試解析 Gemini API 回傳的 JSON 格式結果。
    如果回傳內容被 markdown 的反引號包圍，則先移除這些標記。
    若解析失敗，則回傳所有項目皆為空的字典。
    """
    cleaned = response_text.strip()
    # 如果回傳內容以三個反引號開始，則移除第一行和最後一行
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    
    try:
        result = json.loads(cleaned)
        for item in ITEMS:
            if item not in result:
                result[item] = ""
        return result
    except Exception as e:
        print(f"解析 JSON 失敗：{e}")
        print("原始回傳內容：", response_text)
        return {item: "" for item in ITEMS}

def select_dialogue_column(chunk: pd.DataFrame) -> str:
    """
    根據 CSV 欄位內容自動選取存放逐字稿的欄位。
    優先檢查常見欄位名稱："text", "utterance", "content", "dialogue"
    若都不存在，則回傳第一個欄位。
    """
    preferred = ["text", "utterance", "content", "dialogue", "Dialogue"]
    for col in preferred:
        if col in chunk.columns:
            return col
    print("CSV 欄位：", list(chunk.columns))
    return chunk.columns[0]

def process_batch_dialogue(client, dialogues: list, delimiter="-----"):
    """
    將多筆逐字稿合併成一個批次請求。
    提示中要求模型對每筆逐字稿產生 JSON 格式回覆，
    並以指定的 delimiter 分隔各筆結果。
    """
    # HW2 Prompt change info
    prompt = (
        "你是一位學術會議討論分析專家，請根據以下編碼規則評估每位發言者在會議中的表現：\n"
        + "\n".join(ITEMS) +
        "\n\n請依據以下標準對每個項目進行評分：\n"
        "- 論點清晰：發言者是否能夠清楚地表達其觀點？\n"
        "- 邏輯性（易於理解）：發言者是否以易理解的方式解釋學術名詞？\n"
        "- 互動性：與會者之間是否積極互動？是否有啟發性的提問和回應？\n"
        "- 延伸議題深度與廣度：討論是否深入探討問題的多個層面？\n"
        "- 延伸問題：是否有對話題進行延伸，提出了新的問題或視角？\n"
        "- 不確定性：發言中是否表現出自我立場不確定或模糊的地方？\n"
        "- 批判性思維：發言者是否能夠提出批判性思維，質疑現有觀點或解決方案？\n"
        "- 引用其他著作：發言中是否引用了其他相關的學術著作或研究？\n"
        "- 開放式問題：發言中是否包含開放式問題，鼓勵討論或思考？\n"
        "- 總結：發言是否有總結和結論部分，讓聽眾清楚理解核心觀點？\n"
    
        "\n請對每筆逐字稿產生 JSON 格式回覆，並在各筆結果間用下列分隔線隔開：\n"
        f"{delimiter}\n"
        "例如：\n"
        "```json\n"
        "{\n  \"論點清晰\": \"1\",\n  \"邏輯性（易於理解）\": \"1\",\n  \"互動性\": \"\",\n  "
        "\"延伸議題深度\": \"1\",\n  \"延伸議題廣度\": \"1\",\n  \"延伸問題\": \"\",\n  "
        "\"不確定性\": \"1\",\n  \"批判性思維\": \"1\",\n  \"引用其他著作\": \"1\",\n  "
        "\"開放式問題\": \"1\",\n  \"總結\": \"1\"\n}\n"
        f"{delimiter}\n"
        "{{...}}\n```"
)


    batch_text = f"\n{delimiter}\n".join(dialogues)
    content = prompt + "\n\n" + batch_text

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=content
        )
    except ServerError as e:
        print(f"API 呼叫失敗：{e}")
        return [{item: "" for item in ITEMS} for _ in dialogues]
    
    print("批次 API 回傳內容：", response.text)
    parts = response.text.split(delimiter)
    results = []
    for part in parts:
        part = part.strip()
        if part:
            results.append(parse_response(part))
    # 若結果數量多於原始筆數，僅取前面對應筆數；若不足則補足空結果
    if len(results) > len(dialogues):
        results = results[:len(dialogues)]
    elif len(results) < len(dialogues):
        results.extend([{item: "" for item in ITEMS}] * (len(dialogues) - len(results)))
    return results

def main():
    if len(sys.argv) < 2:
        print("Usage: python DRai.py <path_to_csv>")
        sys.exit(1)
    
    input_csv = sys.argv[1]
    output_csv = "Drai_result.csv"
    if os.path.exists(output_csv):
        os.remove(output_csv)
    
    df = pd.read_csv(input_csv)
    gemini_api_key = os.environ.get("GEMINI_API_KEY")
    if not gemini_api_key:
        raise ValueError("請設定環境變數 GEMINI_API_KEY")
    client = genai.Client(api_key=gemini_api_key)
    
    dialogue_col = select_dialogue_column(df)
    print(f"使用欄位作為逐字稿：{dialogue_col}")
    
    batch_size = 10
    total = len(df)
    for start_idx in range(0, total, batch_size):
        end_idx = min(start_idx + batch_size, total)
        batch = df.iloc[start_idx:end_idx]
        dialogues = batch[dialogue_col].tolist()
        dialogues = [str(d).strip() for d in dialogues]
        batch_results = process_batch_dialogue(client, dialogues)
        batch_df = batch.copy()
        for item in ITEMS:
            batch_df[item] = [res.get(item, "") for res in batch_results]
        if start_idx == 0:
            batch_df.to_csv(output_csv, index=False, encoding="utf-8-sig")
        else:
            batch_df.to_csv(output_csv, mode='a', index=False, header=False, encoding="utf-8-sig")
        print(f"已處理 {end_idx} 筆 / {total}")
        time.sleep(1)
    
    print("全部處理完成。最終結果已寫入：", output_csv)

if __name__ == "__main__":
    main()