"""Core logic for the WJX AI Assistant."""
import json
import os
import random
import re
import time
from typing import Callable, Dict, List, Optional

import requests
from selenium import webdriver
from selenium.webdriver.common.by import By

CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "api_key": "",
    "api_url": "https://api.siliconflow.cn/v1/chat/completions",
    "model": "deepseek-ai/DeepSeek-V2.5",
    "wait_min": 80,
    "wait_max": 100,
    "screenshot_dir": "./screenshots",
    "browser_width": 550,
    "browser_height": 700,
}


def load_config() -> Dict:
    """Load config from config.json, creating a local template when missing."""
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    merged = DEFAULT_CONFIG.copy()
    merged.update(cfg)
    return merged


def save_config(cfg: Dict) -> None:
    """Persist runtime config to config.json."""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=4)


def init_driver(cfg: Dict, headless: bool = False) -> webdriver.Chrome:
    """Create a Chrome WebDriver instance."""
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    driver = webdriver.Chrome(options=options)
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'},
    )
    if not headless:
        driver.set_window_size(int(cfg["browser_width"]), int(cfg["browser_height"]))
        driver.set_window_position(x=100, y=50)
    return driver


def _click_entry_button(driver: webdriver.Chrome, log_cb: Callable[..., None] = print) -> bool:
    """Click a cover-page entry button when the questionnaire has one."""
    keywords = ["开始作答", "开始答题", "立即参与", "开始填写", "马上去答", "参加答题", "进入答题"]
    for keyword in keywords:
        xpath = f"//*[self::button or self::a or self::div or self::span][contains(normalize-space(.), '{keyword}')]"
        try:
            for elem in driver.find_elements(By.XPATH, xpath):
                if elem.is_displayed() and elem.is_enabled():
                    log_cb(f"点击入口按钮: {elem.text.strip() or keyword}")
                    elem.click()
                    time.sleep(2)
                    return True
        except Exception:
            continue
    return False


def _wait_for_questions(driver: webdriver.Chrome, timeout: int = 10) -> bool:
    """Wait until WJX question nodes appear."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if driver.find_elements(By.CSS_SELECTOR, "#divQuestion [topic]"):
            return True
        time.sleep(0.5)
    return False


def _first_text(parent, selectors: List[str]) -> str:
    for selector in selectors:
        try:
            text = parent.find_element(By.CSS_SELECTOR, selector).text.strip()
            if text:
                return text
        except Exception:
            pass
    return ""


def _clean_question_text(text: str) -> str:
    return re.sub(r"^\s*\d+[.、．]?\s*", "", text or "").strip()


def _extract_choice_options(div) -> List[str]:
    selectors = [
        ".ui-controlgroup > div",
        ".ui-controlgroup .label",
        ".field-label",
        "li",
    ]
    seen = []
    for selector in selectors:
        for item in div.find_elements(By.CSS_SELECTOR, selector):
            text = item.text.strip()
            if text and text not in seen:
                seen.append(text)
        if seen:
            break
    return seen


def _extract_matrix_options(driver: webdriver.Chrome, qid: str, div) -> List[str]:
    table = None
    for finder in (
        lambda: driver.find_element(By.CSS_SELECTOR, f"#divRefTab{qid}"),
        lambda: div.find_element(By.TAG_NAME, "table"),
        lambda: driver.find_element(By.CSS_SELECTOR, f"#drv{qid}_1").find_element(By.XPATH, "./ancestor::table"),
    ):
        try:
            table = finder()
            break
        except Exception:
            pass
    if table is None:
        return []

    rows = []
    for row in table.find_elements(By.TAG_NAME, "tr"):
        cells = row.find_elements(By.TAG_NAME, "td")
        if len(cells) < 2:
            continue
        row_label = cells[0].text.strip()
        choices = [cell.text.strip() for cell in cells[1:] if cell.text.strip()]
        if row_label and choices:
            rows.append(f"{row_label} | 选项: {' / '.join(choices)}")
    return rows


def parse_questionnaire(driver: webdriver.Chrome) -> List[Dict]:
    """Parse visible WJX question nodes into structured data."""
    questions: List[Dict] = []
    for div in driver.find_elements(By.CSS_SELECTOR, "#divQuestion [topic]"):
        qid = div.get_attribute("topic")
        if not (qid and qid.isdigit()):
            continue
        q_type = div.get_attribute("type") or ""
        q_text = _clean_question_text(_first_text(div, [".field-label", ".field-title", ".topic-title", ".div_title_question"]))

        options: List[str] = []
        if q_type in {"3", "4"}:
            options = _extract_choice_options(div)
        elif q_type == "5":
            options = [item.text.strip() for item in div.find_elements(By.CSS_SELECTOR, ".scale-div li") if item.text.strip()]
        elif q_type == "6":
            options = _extract_matrix_options(driver, qid, div)
        elif q_type == "7":
            options = ["下拉选项"]
        elif q_type == "11":
            options = [item.text.strip() for item in div.find_elements(By.CSS_SELECTOR, "ul li") if item.text.strip()]

        questions.append({
            "id": qid,
            "type": q_type,
            "text": q_text,
            "options": options,
            "index": len(questions),
        })
    return questions


def format_questionnaire_for_ai(questions: List[Dict]) -> str:
    """Format parsed questions for the model prompt."""
    type_names = {
        "1": "填空题",
        "2": "填空题",
        "3": "单选题",
        "4": "多选题",
        "5": "量表题",
        "6": "矩阵题",
        "7": "下拉题",
        "8": "滑块题",
        "11": "排序题",
    }
    lines = []
    for q in questions:
        q_type = type_names.get(q["type"], f"未知题型 {q['type']}")
        options = " | ".join(q["options"]) if q["options"] else "无选项"
        lines.append(f"{q['id']}. [{q_type}] {q['text']} | 选项: {options}")
    return "\n".join(lines)


def call_ai_api(questionnaire_text: str, user_requirements: str, cfg: Dict, log_cb: Callable[..., None] = print) -> Dict:
    """Call the configured chat-completions API and parse a JSON answer map."""
    if not cfg.get("api_key"):
        raise RuntimeError("请先在 config.json 或 GUI 设置中配置 API Key。")

    prompt = f"""请根据下面的问卷内容和填写要求生成答案。仅用于本人创建或已获授权的测试问卷。

问卷内容:
{questionnaire_text}

填写要求:
{user_requirements}

请只返回 JSON，不要添加解释。格式示例:
{{
  "1": "B",
  "2": ["A", "C"],
  "3": "这是一段填空答案"
}}

规则:
- 单选题、量表题、下拉题、滑块题返回选项字母或数字。
- 多选题返回选项字母数组。
- 填空题返回具体文本。
- 矩阵题返回每一行的选项字母，用英文逗号分隔。
"""

    payload = {
        "model": cfg["model"],
        "messages": [{"role": "user", "content": prompt}],
        "stream": True,
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Bearer {cfg['api_key']}",
    }

    log_cb("正在调用 AI 生成答案，请稍候...")
    response = requests.post(cfg["api_url"], json=payload, headers=headers, stream=True, timeout=120)
    if response.status_code != 200:
        raise RuntimeError(f"API 请求失败: {response.status_code} {response.text}")

    content = ""
    streamed_len = 0
    for chunk in response.iter_lines():
        if not chunk:
            continue
        chunk_text = chunk.decode("utf-8", errors="ignore").removeprefix("data: ").strip()
        if chunk_text == "[DONE]":
            break
        try:
            delta = json.loads(chunk_text).get("choices", [{}])[0].get("delta", {})
        except json.JSONDecodeError:
            continue
        piece = delta.get("content", "")
        if piece:
            content += piece
            if len(content) > streamed_len:
                log_cb(content[streamed_len:], add_newline=False)
                streamed_len = len(content)

    log_cb("")
    answers = parse_ai_json_response(content)
    log_cb(f"AI 答案解析结果: {answers}")
    return answers


def parse_ai_json_response(content: str) -> Dict:
    """Extract the first JSON object from model output."""
    if not content or not content.strip():
        raise RuntimeError("AI 返回内容为空。")
    cleaned = re.sub(r"```(?:json)?|```", "", content, flags=re.IGNORECASE).strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start >= 0 and end > start:
        try:
            parsed = json.loads(cleaned[start:end + 1])
            return {str(k).strip(): v for k, v in parsed.items()}
        except json.JSONDecodeError:
            pass
    raise RuntimeError(f"无法解析 AI 返回的 JSON: {content[:300]}")


def option_letter_to_index(value: str) -> int:
    """Convert A/B/C or 1/2/3 to a one-based index."""
    text = str(value).strip()
    if not text:
        return 1
    if text.isdigit():
        return max(1, int(text))
    first = text[0].upper()
    if "A" <= first <= "Z":
        return ord(first) - ord("A") + 1
    return 1


def _click_by_index(elements, idx: int) -> bool:
    if not elements:
        return False
    safe_idx = max(1, min(idx, len(elements)))
    elements[safe_idx - 1].click()
    return True


def fill_questionnaire(driver: webdriver.Chrome, questions: List[Dict], answers: Dict, log_cb: Callable[..., None] = print) -> None:
    """Fill parsed questions with answer values."""
    for q in questions:
        qid = q["id"]
        q_type = q["type"]
        answer = answers.get(qid, "")
        try:
            if q_type in {"1", "2"}:
                elem = driver.find_element(By.CSS_SELECTOR, f"#q{qid}")
                elem.clear()
                elem.send_keys(str(answer))
                log_cb(f"题 {qid}: 已填写文本")

            elif q_type in {"3", "5"}:
                idx = option_letter_to_index(answer or random.randint(1, max(1, len(q["options"]))))
                selector = f"#div{qid} > div.ui-controlgroup > div" if q_type == "3" else f"#div{qid} .scale-div li"
                _click_by_index(driver.find_elements(By.CSS_SELECTOR, selector), idx)
                log_cb(f"题 {qid}: 选择第 {idx} 项")

            elif q_type == "4":
                values = answer if isinstance(answer, list) else str(answer).split(",")
                opts = driver.find_elements(By.CSS_SELECTOR, f"#div{qid} > div.ui-controlgroup > div")
                for value in values:
                    _click_by_index(opts, option_letter_to_index(value))
                    time.sleep(0.1)
                log_cb(f"题 {qid}: 已选择多选项")

            elif q_type == "6":
                values = answer if isinstance(answer, list) else str(answer).split(",")
                rows = driver.find_elements(By.CSS_SELECTOR, f"#divRefTab{qid} tr[rowindex]")
                for pos, row in enumerate(rows, 1):
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) < 2:
                        continue
                    raw = values[pos - 1] if pos - 1 < len(values) else "A"
                    idx = option_letter_to_index(raw)
                    idx = max(1, min(idx, len(cells) - 1))
                    cells[idx].click()
                    time.sleep(0.1)
                log_cb(f"题 {qid}: 已填写矩阵题")

            elif q_type == "7":
                idx = option_letter_to_index(answer)
                driver.find_element(By.CSS_SELECTOR, f"#select2-q{qid}-container").click()
                time.sleep(0.3)
                items = driver.find_elements(By.CSS_SELECTOR, f"#select2-q{qid}-results > li")
                _click_by_index(items, idx + 1)
                log_cb(f"题 {qid}: 已选择下拉项")

            elif q_type == "8":
                value = int(answer) if str(answer).strip().isdigit() else random.randint(1, 100)
                driver.find_element(By.CSS_SELECTOR, f"#q{qid}").send_keys(str(value))
                log_cb(f"题 {qid}: 已设置滑块值 {value}")

            else:
                log_cb(f"题 {qid}: 暂不支持题型 {q_type}，已跳过")
        except Exception as exc:
            log_cb(f"题 {qid}: 填写失败 - {exc}")
        time.sleep(0.2)


def handle_page_navigation(driver: webdriver.Chrome) -> bool:
    """Click the next-page button when present."""
    try:
        next_btn = driver.find_element(By.CSS_SELECTOR, "#divNext")
        if next_btn.is_displayed():
            next_btn.click()
            time.sleep(0.8)
            return True
    except Exception:
        pass
    return False


def submit(driver: webdriver.Chrome, log_cb: Callable[..., None] = print) -> bool:
    """Submit the questionnaire and report manual verification when required."""
    try:
        driver.find_element(By.CSS_SELECTOR, "#ctlNext").click()
        time.sleep(3)
    except Exception as exc:
        log_cb(f"点击提交按钮失败: {exc}")
        return False

    page_text = driver.page_source
    if any(keyword in page_text for keyword in ["请完成", "请填写", "请回答", "验证码", "滑块"]):
        log_cb("检测到未完成提示或人工验证，请在浏览器中手动确认。")
        return False
    return True


def save_screenshot(driver: webdriver.Chrome, answers: Dict, questionnaire_text: str, save_dir: str, log_cb: Callable[..., None] = print) -> str:
    """Save screenshot and generated answers under the runtime output directory."""
    os.makedirs(save_dir, exist_ok=True)
    run_dir = os.path.join(save_dir, time.strftime("%Y%m%d_%H%M%S", time.localtime()))
    os.makedirs(run_dir, exist_ok=True)

    screenshot_path = os.path.join(run_dir, "result.png")
    driver.save_screenshot(screenshot_path)
    info_path = os.path.join(run_dir, "answers.json")
    with open(info_path, "w", encoding="utf-8") as f:
        json.dump({"answers": answers, "questionnaire_snapshot": questionnaire_text}, f, ensure_ascii=False, indent=2)
    log_cb(f"结果已保存到: {run_dir}")
    return run_dir


def run_task(
    url: str,
    requirements: str,
    cfg: Dict,
    log_cb: Callable[..., None] = print,
    progress_cb: Optional[Callable[..., None]] = None,
    headless: bool = False,
) -> bool:
    """Run one questionnaire task for CLI or GUI callers."""
    driver = None
    try:
        driver = init_driver(cfg, headless=headless)
        log_cb(f"正在访问: {url}")
        driver.get(url)
        time.sleep(3)

        if _click_entry_button(driver, log_cb):
            log_cb("已进入问卷页面。")
        _wait_for_questions(driver, timeout=10)

        log_cb("正在解析问卷内容...")
        questions = parse_questionnaire(driver)
        if not questions:
            log_cb("未能解析到问卷题目，请检查链接或页面结构。")
            return False
        log_cb(f"共解析到 {len(questions)} 道题。")

        if progress_cb:
            for q in questions:
                progress_cb(f"题 {q['id']}: [{q['type']}] {q['text'][:40]}")

        questionnaire_text = format_questionnaire_for_ai(questions)
        answers = call_ai_api(questionnaire_text, requirements, cfg, log_cb)

        log_cb("正在填写问卷...")
        fill_questionnaire(driver, questions, answers, log_cb)
        while handle_page_navigation(driver):
            log_cb("已翻到下一页。")

        wait_min = int(cfg.get("wait_min", 0))
        wait_max = int(cfg.get("wait_max", wait_min))
        wait_time = random.randint(min(wait_min, wait_max), max(wait_min, wait_max))
        if wait_time > 0:
            log_cb(f"等待 {wait_time} 秒后提交...")
            time.sleep(wait_time)

        log_cb("正在提交...")
        ok = submit(driver, log_cb)
        save_screenshot(driver, answers, questionnaire_text, cfg["screenshot_dir"], log_cb)
        return ok
    except Exception as exc:
        log_cb(f"任务执行出错: {exc}")
        return False
    finally:
        if driver:
            driver.quit()