from playwright.sync_api import sync_playwright
import os
from dotenv import load_dotenv

def add_todolist(task_name: str = "這是預設任務") -> None:

    # 讀取 .env 檔案
    load_dotenv()

    # 從 .env 讀取 Todoist 帳號和密碼
    TODOIST_EMAIL = os.getenv("TODOIST_EMAIL")
    TODOIST_PASSWORD = os.getenv("TODOIST_PASSWORD")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # 顯示瀏覽器
        page = browser.new_page()

        print("啟動瀏覽器，開始登入 Todoist...")

        # 進入 Todoist 登入頁面
        page.goto("https://todoist.com/users/showlogin")
        page.wait_for_timeout(3000)

        # 使用 .env 讀取帳號密碼
        page.fill("input[id='element-0']", TODOIST_EMAIL)  # 使用新的 ID 選擇器
        page.fill("input[id='element-2']", TODOIST_PASSWORD)  # 使用新的 ID 選擇器

        # 按下登入按鈕
        page.press("input[id='element-2']", "Enter")

        # 等待登入完成
        page.wait_for_timeout(5000)
        print("登入成功！")
        page.screenshot(path="debug_1_after_login.png")

        # 創建新的任務
        print("開始新增追蹤名單...")

        # 點選「長期追蹤清單」項目
        page.click("span:has-text('長期追蹤清單')", timeout=5000)
        page.wait_for_timeout(2000)

        # 點擊「添加任務」按鈕
        add_task_button = page.locator("button[aria-disabled='false'] span:has-text('添加任務')").first
        add_task_button.wait_for()
        add_task_button.click()
        page.wait_for_timeout(2000)

        # 輸入任務名稱
        try:
            task_name_input = page.locator("p[data-placeholder='任務名稱']").first
            task_name_input.wait_for(state="visible", timeout=10000)  # 增加等待時間
            task_name_input.fill(task_name)
            print("任務名稱已輸入！")
        except Exception as e:
            print(f"無法找到任務名稱輸入框: {e}")

        # 提交任務
        try:
            submit_button = page.locator("button[data-testid='task-editor-submit-button']").first
            submit_button.wait_for(state="visible", timeout=10000)  # 增加等待時間
            submit_button.click()
            print("任務已創建！")
        except Exception as e:
            print(f"無法提交任務: {e}")

        page.wait_for_timeout(3000)

        # 關閉瀏覽器
        browser.close()
        print("瀏覽器已關閉")