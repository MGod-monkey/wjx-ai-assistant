"""
闂嵎鏄?AI 鑷姩濉啓绯荤粺 (GUI 鐗堟湰)
鍩轰簬 SiliconFlow API (DeepSeek-V2.5) 鑷姩鐢熸垚闂嵎绛旀骞跺～鍐?"""
import json
import os
import random
import re
import threading
import time
from typing import Callable, Dict, List, Optional

import requests
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By

# ==================== 閰嶇疆绠＄悊 ====================
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
    """鍔犺浇閰嶇疆锛屼笉瀛樺湪鍒欏垱寤洪粯璁ら厤缃?""
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(cfg: Dict) -> None:
    """淇濆瓨閰嶇疆鍒版枃浠?""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=4)


# ==================== 娴忚鍣ㄥ垵濮嬪寲 ====================
def init_driver(cfg: Dict) -> webdriver.Chrome:
    """鏍规嵁閰嶇疆鍒濆鍖?Chrome 娴忚鍣?""
    option = webdriver.ChromeOptions()
    option.add_experimental_option("excludeSwitches", ["enable-automation"])
    option.add_experimental_option("useAutomationExtension", False)
    driver = webdriver.Chrome(options=option)
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'},
    )
    driver.set_window_size(cfg["browser_width"], cfg["browser_height"])
    driver.set_window_position(x=100, y=50)
    return driver


# ==================== 闂嵎瑙ｆ瀽妯″潡 ====================
def parse_questionnaire(driver: webdriver.Chrome) -> List[Dict]:
    """
    瑙ｆ瀽闂嵎椤甸潰锛岃繑鍥炵粨鏋勫寲鐨勯鐩垪琛ㄣ€?    澶嶇敤 wjx2.py 鐨?detect() 鍜岄鍨嬪垽鏂€昏緫銆?    """
    questions: List[Dict] = []
    current_qid = 0

    page_num = len(driver.find_elements(By.XPATH, '//*[@id="divQuestion"]/fieldset'))

    for page_idx in range(1, page_num + 1):
        fieldset_id = f"fieldset{page_idx}"
        fieldset = driver.find_element(By.XPATH, f'//*[@id="{fieldset_id}"]')
        topic_divs = fieldset.find_elements(By.XPATH, f'//*[@id="{fieldset_id}"]/div')

        for div in topic_divs:
            topic_attr = div.get_attribute("topic")
            if not (topic_attr and topic_attr.isdigit()):
                continue

            current_qid += 1
            q_type = div.get_attribute("type")
            qid = topic_attr

            # 鎻愬彇棰樼洰鏂囨湰
            try:
                title_elem = div.find_element(By.CLASS_NAME, "field-label")
                q_text = title_elem.text.strip()
            except Exception:
                try:
                    title_elem = div.find_element(By.CSS_SELECTOR, ".field-title")
                    q_text = title_elem.text.strip()
                except Exception:
                    q_text = ""

            q_text = re.sub(r"^\d+[.銆?]\s*", "", q_text).strip()

            # 鎻愬彇閫夐」
            options: List[str] = []
            if q_type == "1" or q_type == "2":
                pass  # 濉┖棰樻棤閫夐」
            elif q_type == "3":
                opts = div.find_elements(By.CSS_SELECTOR, ".ui-controlgroup > div")
                options = [opt.text.strip() for opt in opts if opt.text.strip()]
            elif q_type == "4":
                opts = div.find_elements(By.CSS_SELECTOR, ".ui-controlgroup > div")
                options = [opt.text.strip() for opt in opts if opt.text.strip()]
            elif q_type == "5":
                try:
                    opts = div.find_elements(By.CSS_SELECTOR, ".scale-div ul li")
                    options = [opt.text.strip() for opt in opts if opt.text.strip()]
                except Exception:
                    opts = []
            elif q_type == "6":
                try:
                    # 浼樺厛閫氳繃 divRefTab{qid} 瀹氫綅
                    try:
                        tbl = driver.find_element(By.CSS_SELECTOR, f"#divRefTab{qid}")
                    except Exception:
                        tbl = div.find_element(By.TAG_NAME, "table")
                    rows = tbl.find_elements(By.TAG_NAME, "tr")
                    for row_el in rows:
                        rowindex = row_el.get_attribute("rowindex")
                        if rowindex is None:
                            continue
                        tds = row_el.find_elements(By.TAG_NAME, "td")
                        if not tds:
                            continue
                        row_label = tds[0].text.strip()
                        if not row_label:
                            continue
                        option_cols = [c for c in tds[1:] if c.text.strip()]
                        if not option_cols:
                            continue
                        col_texts = [c.text.strip() for c in option_cols]
                        options.append(f"{row_label} | 閫夐」: {' / '.join(col_texts)}")
                except Exception:
                    pass
            elif q_type == "7":
                options = ["涓嬫媺閫夐」 (闇€鎵嬪姩澶勭悊)"]
            elif q_type == "8":
                pass  # 婊戝潡棰?
            questions.append({
                "id": qid,
                "type": q_type,
                "text": q_text,
                "options": options,
                "index": len(questions),
            })

    return questions


def format_questionnaire_for_ai(questions: List[Dict]) -> str:
    """灏嗛鐩垪琛ㄦ牸寮忓寲涓哄彂閫佺粰 AI 鐨勬枃鏈?""
    type_names = {
        "1": "濉┖棰?, "2": "濉┖棰?, "3": "鍗曢€夐",
        "4": "澶氶€夐", "5": "閲忚〃棰?, "6": "鐭╅樀棰?,
        "7": "涓嬫媺妗嗛", "8": "婊戝潡棰?, "11": "鎺掑簭棰?,
    }
    lines = []
    for q in questions:
        type_name = type_names.get(q["type"], "鏈煡棰樺瀷")
        opt_str = " | ".join(q["options"]) if q["options"] else "(鏃犻€夐」)"
        lines.append(f'{q["id"]}. [{type_name}] {q["text"]} | 閫夐」: {opt_str}')
    return "\n".join(lines)


# ==================== SiliconFlow API 璋冪敤妯″潡 ====================
def call_ai_api(
    questionnaire_text: str,
    user_requirements: str,
    cfg: Dict,
    log_cb: Callable[[str], None] = print,
) -> Dict:
    """
    璋冪敤 SiliconFlow API (DeepSeek-V2.5)锛岃繑鍥?AI 鐢熸垚鐨勭瓟妗堝瓧鍏搞€?    """
    prompt = f"""璇锋牴鎹互涓嬮棶鍗峰唴瀹瑰拰鐢ㄦ埛鐨勫～鍐欒姹傦紝鐢熸垚姣忛亾棰樼殑绛旀銆?
銆愰棶鍗峰唴瀹广€?{questionnaire_text}

銆愮敤鎴峰～鍐欒姹傘€?{user_requirements}

銆愯緭鍑烘牸寮忚姹傘€?璇蜂弗鏍间互绾?JSON 鏍煎紡杩斿洖绛旀锛屼笉瑕佸寘鍚换浣曞叾浠栨枃瀛楄鏄庛€傛牸寮忓涓嬶細
{{
    "1": "B",
    "2": ["A", "C"],
    "3": "杩欐槸涓€涓～鍐欑殑绛旀",
    ...
}}
璇存槑锛?- 鍗曢€夐銆侀噺琛ㄩ銆佷笅鎷夋棰樸€佹粦鍧楅锛氬€煎繀椤讳负閫夐」瀛楁瘝锛堝 "A", "B", "C"锛夛紝涓嶈杩斿洖閫夐」鏂囨湰锛?- 澶氶€夐锛氬€煎繀椤讳负閫夐」瀛楁瘝鍒楄〃锛堝 ["A", "C"]锛夛紝涓嶈杩斿洖閫夐」鏂囨湰锛?- 濉┖棰橈細鍊间负瑕佸～鍐欑殑鍏蜂綋鏂囨湰
- 鐭╅樀棰橈細鍊间负姣忎釜灏忛鐨勯€夐」瀛楁瘝锛岄€楀彿鍒嗛殧锛堝 "A,B,C"锛?- 鎺掑簭棰橈細鍊间负閫夐」瀛楁瘝鐨勬帓鍒楅『搴忥紝閫楀彿鍒嗛殧锛堝 "B,A,C"锛?- 棰樺彿璇蜂笌闂嵎涓殑棰樺彿淇濇寔涓€鑷?- 涓ユ牸鎸夌収鐢ㄦ埛瑕佹眰鐢熸垚绛旀
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

    log_cb("姝ｅ湪璋冪敤 AI 鐢熸垚绛旀锛岃绋嶅€?..")
    response = requests.post(cfg["api_url"], json=payload, headers=headers, stream=True)

    if response.status_code != 200:
        raise Exception(f"API 璇锋眰澶辫触锛岀姸鎬佺爜锛歿response.status_code}锛屽搷搴旓細{response.text}")

    full_content = ""
    for chunk in response.iter_lines():
        if chunk:
            chunk_str = chunk.decode("utf-8").replace("data: ", "")
            if chunk_str == "[DONE]":
                break
            try:
                chunk_data = json.loads(chunk_str)
                delta = chunk_data.get("choices", [{}])[0].get("delta", {})
                content = delta.get("content", "")
                if content:
                    log_cb(content, end="", flush=True)
                    full_content += content
            except json.JSONDecodeError:
                continue

    log_cb("")

    answers = parse_ai_json_response(full_content)
    log_cb(f"\nAI 杩斿洖鐨勭瓟妗堣В鏋愮粨鏋滐細{answers}")
    return answers


def parse_ai_json_response(content: str) -> Dict:
    """浠?AI 杩斿洖鍐呭涓彁鍙?JSON"""
    start = content.find("{")
    end = content.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(content[start:end + 1])
        except json.JSONDecodeError:
            pass
    raise Exception(f"鏃犳硶瑙ｆ瀽 AI 杩斿洖鐨?JSON 鍐呭锛歿content[:500]}")


# ==================== 闂嵎濉啓妯″潡 ====================
def option_letter_to_index(letter: str) -> int:
    """灏嗛€夐」瀛楁瘝 A/B/C... 杞崲涓?1-based 绱㈠紩"""
    letter = letter.strip().upper()
    if len(letter) == 1 and letter.isalpha():
        return ord(letter) - ord("A") + 1
    return int(letter) if letter.isdigit() else 0


def match_option_by_text(answer, options: List[str]) -> int:
    """
    灏?AI 杩斿洖鐨勯€夐」鏂囨湰鍖归厤鍒板疄闄呴€夐」鍒楄〃锛岃繑鍥?1-based 绱㈠紩銆?    """
    answer_str = str(answer).strip()
    for idx, opt in enumerate(options, 1):
        opt_clean = opt.strip()
        if answer_str in opt_clean or opt_clean in answer_str:
            return idx
        answer_upper = answer_str.upper()
        if len(answer_upper) == 1 and answer_upper.isalpha():
            if answer_upper == chr(ord("A") + idx - 1):
                return idx
    return 0


def fill_questionnaire(
    driver: webdriver.Chrome,
    questions: List[Dict],
    answers: Dict,
    log_cb: Callable[[str], None] = print,
) -> None:
    """鏍规嵁 AI 杩斿洖鐨勭瓟妗堝～鍐欓棶鍗?""
    for q in questions:
        qid = q["id"]
        q_type = q["type"]
        answer = answers.get(qid)

        if answer is None:
            log_cb(f"棰?{qid}: 鏃犵瓟妗堬紝璺宠繃")
            continue

        try:
            if q_type == "1" or q_type == "2":
                driver.find_element(By.CSS_SELECTOR, f"#q{qid}").send_keys(str(answer))
                log_cb(f"棰?{qid}: 濉啓銆寋answer}銆?)

            elif q_type == "3":
                idx = option_letter_to_index(answer)
                if idx == 0:
                    idx = match_option_by_text(answer, q["options"])
                if idx == 0:
                    log_cb(f"棰?{qid}: 鏃犳硶鍖归厤绛旀銆寋answer}銆嶅埌閫夐」锛岃烦杩?)
                    continue
                driver.find_element(
                    By.CSS_SELECTOR,
                    f"#div{qid} > div.ui-controlgroup > div:nth-child({idx})"
                ).click()
                log_cb(f"棰?{qid}: 閫夋嫨绗?{idx} 涓€夐」")

            elif q_type == "4":
                if isinstance(answer, list):
                    letters = answer
                elif isinstance(answer, str):
                    extracted = [c.strip() for c in answer.split(",") if c.strip().isalpha()]
                    if extracted:
                        letters = extracted
                    else:
                        letters = [answer]
                else:
                    letters = []

                matched_any = False
                for letter in letters:
                    idx = option_letter_to_index(letter)
                    if idx == 0:
                        idx = match_option_by_text(letter, q["options"])
                    if idx > 0:
                        driver.find_element(
                            By.CSS_SELECTOR,
                            f"#div{qid} > div.ui-controlgroup > div:nth-child({idx})"
                        ).click()
                        time.sleep(0.2)
                        matched_any = True
                if not matched_any:
                    log_cb(f"棰?{qid}: 鏃犳硶鍖归厤澶氶€夌瓟妗堛€寋answer}銆嶅埌閫夐」锛岃烦杩?)
                else:
                    log_cb(f"棰?{qid}: 澶氶€夊尮閰嶆垚鍔?)

            elif q_type == "5":
                idx = option_letter_to_index(answer)
                if idx == 0:
                    idx = match_option_by_text(answer, q["options"])
                if idx == 0:
                    log_cb(f"棰?{qid}: 鏃犳硶鍖归厤绛旀銆寋answer}銆嶅埌閫夐」锛岃烦杩?)
                    continue
                driver.find_element(
                    By.CSS_SELECTOR,
                    f"#div{qid} > div.scale-div > div > ul > li:nth-child({idx})"
                ).click()
                log_cb(f"棰?{qid}: 閲忚〃閫夋嫨绗?{idx} 椤?)

            elif q_type == "6":
                matrix_rows = driver.find_elements(
                    By.XPATH, f'//*[@id="divRefTab{qid}"]/tr'
                )
                row_count = sum(
                    1 for r in matrix_rows if r.get_attribute("rowindex") is not None
                )
                if isinstance(answer, str):
                    ans_list = [a.strip() for a in answer.split(",")]
                elif isinstance(answer, list):
                    ans_list = [str(a).strip() for a in answer]
                else:
                    ans_list = []

                for i in range(1, row_count + 1):
                    col_opts = driver.find_elements(
                        By.XPATH, f'//*[@id="drv{qid}_{i}"]/td'
                    )
                    if i <= len(ans_list):
                        opt_val = ans_list[i - 1]
                        if isinstance(opt_val, str) and opt_val.isalpha():
                            opt_idx = option_letter_to_index(opt_val)
                        else:
                            opt_idx = int(opt_val)
                    else:
                        opt_idx = random.randint(1, len(col_opts))
                    driver.find_element(
                        By.CSS_SELECTOR, f"#drv{qid}_{i} > td:nth-child({opt_idx})"
                    ).click()
                    time.sleep(0.1)
                log_cb(f"棰?{qid}: 鐭╅樀棰樺～鍐欏畬鎴?)

            elif q_type == "7":
                driver.find_element(By.CSS_SELECTOR, f"#select2-q{qid}-container").click()
                time.sleep(0.5)
                if isinstance(answer, str):
                    idx = option_letter_to_index(answer)
                else:
                    idx = int(answer)
                driver.find_element(
                    By.XPATH, f"//*[@id='select2-q{qid}-results']/li[{idx + 1}]"
                ).click()
                log_cb(f"棰?{qid}: 涓嬫媺妗嗛€夋嫨绗?{idx} 椤?)

            elif q_type == "8":
                score = int(answer) if str(answer).isdigit() else random.randint(1, 100)
                driver.find_element(By.CSS_SELECTOR, f"#q{qid}").send_keys(str(score))
                log_cb(f"棰?{qid}: 婊戝潡璁剧疆 {score}")

            elif q_type == "11":
                opts = driver.find_elements(By.XPATH, f'//*[@id="div{qid}"]/ul/li')
                if isinstance(answer, str):
                    order = [option_letter_to_index(c) for c in answer.split(",") if c.strip().isalpha()]
                elif isinstance(answer, list):
                    order = [option_letter_to_index(c) for c in answer]
                else:
                    order = list(range(1, len(opts) + 1))
                    random.shuffle(order)
                for pos, letter_idx in enumerate(order, 1):
                    target = random.randint(pos - 1, len(opts) - 1)
                    driver.find_element(
                        By.CSS_SELECTOR,
                        f"#div{qid} > ul > li:nth-child({target + 1})"
                    ).click()
                    time.sleep(0.3)
                log_cb(f"棰?{qid}: 鎺掑簭棰樺～鍐欏畬鎴?)

        except Exception as e:
            log_cb(f"棰?{qid}: 濉啓澶辫触 - {e}")

        time.sleep(0.3)


# ==================== 鎻愪氦涓庨獙璇佺爜澶勭悊妯″潡 ====================
def handle_page_navigation(driver: webdriver.Chrome) -> bool:
    """澶勭悊闂嵎缈婚〉锛岃繑鍥炴槸鍚﹁繕鏈変笅涓€椤?""
    try:
        next_btn = driver.find_element(By.CSS_SELECTOR, "#divNext")
        if next_btn.is_displayed():
            next_btn.click()
            time.sleep(0.8)
            return True
    except Exception:
        pass
    return False


def submit(
    driver: webdriver.Chrome,
    log_cb: Callable[[str], None] = print,
) -> None:
    """鎻愪氦闂嵎骞跺鐞嗗悇绉嶉獙璇?""
    try:
        driver.find_element(By.XPATH, '//*[@id="ctlNext"]').click()
        time.sleep(1.5)
    except Exception as e:
        log_cb(f"鐐瑰嚮鎻愪氦鎸夐挳澶辫触: {e}")
        return

    try:
        driver.find_element(By.XPATH, '//*[@id="layui-layer1"]/div[3]/a').click()
        time.sleep(1)
    except Exception:
        pass

    try:
        driver.find_element(By.XPATH, '//*[@id="SM_BTN_1"]').click()
        time.sleep(3)
    except Exception:
        pass

    try:
        slider_text = driver.find_element(By.XPATH, '//*[@id="nc_1__scale_text"]/span')
        slider_btn = driver.find_element(By.XPATH, '//*[@id="nc_1_n1z"]')
        if slider_text and "璇锋寜浣忔粦鍧? in slider_text.text:
            width = slider_btn.size.get("width", 300)
            ActionChains(driver).drag_and_drop_by_offset(
                slider_btn, width, 0
            ).perform()
            time.sleep(1)
    except Exception:
        pass


# ==================== 鎴浘淇濆瓨妯″潡 ====================
def save_screenshot(
    driver: webdriver.Chrome,
    answers: Dict,
    questionnaire_text: str,
    save_dir: str,
    log_cb: Callable[[str], None] = print,
) -> str:
    """淇濆瓨鎴浘鍜岀瓟妗堜俊鎭埌鏈湴"""
    os.makedirs(save_dir, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S", time.localtime())
    run_dir = os.path.join(save_dir, ts)
    os.makedirs(run_dir, exist_ok=True)

    screenshot_path = os.path.join(run_dir, "result.png")
    driver.save_screenshot(screenshot_path)
    log_cb(f"鎴浘宸蹭繚瀛? {screenshot_path}")

    info = {
        "timestamp": ts,
        "answers": answers,
        "questionnaire_snapshot": questionnaire_text,
    }
    info_path = os.path.join(run_dir, "answers.json")
    with open(info_path, "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)
    log_cb(f"绛旀宸蹭繚瀛? {info_path}")

    return run_dir


# ==================== 浠诲姟鎵ц锛堜緵 GUI 璋冪敤锛?===================
def run_task(
    url: str,
    requirements: str,
    cfg: Dict,
    log_cb: Callable[[str], None] = print,
    progress_cb: Callable[[str], None] = None,
) -> bool:
    """鍦ㄧ嫭绔嬬嚎绋嬩腑鎵ц闂嵎濉啓浠诲姟"""
    driver = None
    try:
        driver = init_driver(cfg)
        log_cb(f"姝ｅ湪璁块棶: {url}")
        driver.get(url)
        time.sleep(3)

        log_cb("姝ｅ湪瑙ｆ瀽闂嵎鍐呭...")
        questions = parse_questionnaire(driver)
        if not questions:
            log_cb("鏈兘瑙ｆ瀽鍒伴棶鍗烽鐩紝璇锋鏌ラ摼鎺ユ槸鍚︽纭€?)
            return False
        log_cb(f"鍏辫В鏋愬埌 {len(questions)} 閬撻")

        if progress_cb:
            for q in questions:
                progress_cb(f"  棰榹q['id']}: [{q['type']}] {q['text'][:40]}")

        q_text = format_questionnaire_for_ai(questions)
        answers = call_ai_api(q_text, requirements, cfg, log_cb)

        log_cb("姝ｅ湪濉啓闂嵎...")
        fill_questionnaire(driver, questions, answers, log_cb)

        while handle_page_navigation(driver):
            log_cb("宸茬炕鍒颁笅涓€椤?..")
            time.sleep(1)

        wait_time = random.randint(cfg["wait_min"], cfg["wait_max"])
        log_cb(f"\n绛夊緟 {wait_time} 绉掍互妯℃嫙鐪熷疄鐢ㄦ埛濉啓閫熷害...")
        time.sleep(wait_time)

        log_cb("姝ｅ湪鎻愪氦...")
        submit(driver, log_cb)
        time.sleep(3)

        current_url = driver.current_url
        if "ActivitySubmit" in current_url or "SubmitSuc" in current_url or "Thanks" in driver.page_source:
            log_cb("鎻愪氦鎴愬姛锛?)
        else:
            log_cb(f"鎻愪氦瀹屾垚锛屽綋鍓嶉〉闈? {current_url}")

        save_screenshot(driver, answers, q_text, cfg["screenshot_dir"], log_cb)
        log_cb(f"\n浠诲姟瀹屾垚锛?)
        return True

    except Exception as e:
        import traceback
        log_cb(f"\n绋嬪簭鎵ц鍑洪敊: {e}")
        traceback.print_exc()
        return False
    finally:
        if driver:
            driver.quit()


# ==================== Tkinter GUI ====================
try:
    import tkinter as tk
    from tkinter import messagebox, filedialog
    HAS_TK = True
except ImportError:
    HAS_TK = False


class WJXGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("闂嵎鏄?AI 鑷姩濉啓绯荤粺")
        self.root.geometry("820x640")
        self.root.resizable(True, True)

        self.config = load_config()
        self.running = False
        self._task_thread: Optional[threading.Thread] = None

        self._build_ui()
        self._append_log("绋嬪簭鍚姩锛岃杈撳叆闂嵎閾炬帴鍜屽～鍐欒姹傚悗鐐瑰嚮銆屽紑濮嬪～鍐欍€嶃€?)

    def _build_ui(self):
        # ---- 椤堕儴鏍囬鏍?----
        header = tk.Frame(self.root, bg="#2c3e50", pady=8)
        header.pack(fill="x")
        tk.Label(
            header, text="闂嵎鏄?AI 鑷姩濉啓绯荤粺",
            font=("Microsoft YaHei", 14, "bold"),
            fg="white", bg="#2c3e50"
        ).pack(side="left", padx=15)
        tk.Button(
            header, text="璁剧疆", command=self._open_settings,
            font=("Microsoft YaHei", 9), relief="flat", bg="#3498db", fg="white",
            cursor="hand2", padx=10
        ).pack(side="right", padx=10)

        # ---- 杈撳叆鍖?----
        input_frame = tk.Frame(self.root, padx=15, pady=10)
        input_frame.pack(fill="x")

        tk.Label(input_frame, text="闂嵎閾炬帴:", font=("Microsoft YaHei", 10)).grid(
            row=0, column=0, sticky="nw", pady=(5, 2))
        self.url_entry = tk.Entry(input_frame, font=("Microsoft YaHei", 10), relief="solid", bd=1)
        self.url_entry.grid(row=0, column=1, sticky="ew", pady=(5, 2))
        input_frame.columnconfigure(1, weight=1)

        tk.Label(input_frame, text="濉啓瑕佹眰:", font=("Microsoft YaHei", 10)).grid(
            row=1, column=0, sticky="nw", pady=(5, 2))
        self.requirements_text = tk.Text(input_frame, font=("Microsoft YaHei", 9),
                                          height=4, relief="solid", bd=1, wrap="word")
        self.requirements_text.grid(row=1, column=1, sticky="ew", pady=(5, 2))

        # ---- 鎸夐挳鍖?----
        btn_frame = tk.Frame(self.root, padx=15, pady=5)
        btn_frame.pack(fill="x")

        self.start_btn = tk.Button(
            btn_frame, text="寮€濮嬪～鍐?, command=self._on_start,
            font=("Microsoft YaHei", 10, "bold"), bg="#27ae60", fg="white",
            relief="flat", cursor="hand2", padx=20, pady=5
        )
        self.start_btn.pack(side="left", padx=5)

        self.stop_btn = tk.Button(
            btn_frame, text="鍋滄", command=self._on_stop,
            font=("Microsoft YaHei", 10), bg="#e74c3c", fg="white",
            relief="flat", cursor="hand2", padx=20, pady=5, state="disabled"
        )
        self.stop_btn.pack(side="left", padx=5)

        tk.Button(
            btn_frame, text="娓呯┖鏃ュ織", command=self._clear_log,
            font=("Microsoft YaHei", 10), bg="#95a5a6", fg="white",
            relief="flat", cursor="hand2", padx=20, pady=5
        ).pack(side="left", padx=5)

        # ---- 鐘舵€佹爮 ----
        self.status_label = tk.Label(
            self.root, text="灏辩华", anchor="w", font=("Microsoft YaHei", 9),
            fg="#7f8c8d", padx=15, pady=2
        )
        self.status_label.pack(fill="x")

        # ---- 鏃ュ織鍖?----
        log_frame = tk.Frame(self.root, padx=15, pady=(0, 10))
        log_frame.pack(fill="both", expand=True)

        tk.Label(log_frame, text="鏃ュ織杈撳嚭:", font=("Microsoft YaHei", 10)).pack(anchor="nw", pady=(5, 2))

        log_wrapper = tk.Frame(log_frame, bg="#dcdcdc", bd=1, relief="solid")
        log_wrapper.pack(fill="both", expand=True)

        scrollbar = tk.Scrollbar(log_wrapper)
        scrollbar.pack(side="right", fill="y")

        self.log_text = tk.Text(
            log_wrapper, font=("Consolas", 9), bg="#1e1e1e", fg="#d4d4d4",
            relief="flat", state="disabled", yscrollcommand=scrollbar.set,
            wrap="word"
        )
        self.log_text.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.log_text.yview)

        # 鏃ュ織琛屾爣绛鹃厤鑹?        self.log_text.tag_config("info", foreground="#d4d4d4")
        self.log_text.tag_config("success", foreground="#4ec9b0")
        self.log_text.tag_config("error", foreground="#f44747")
        self.log_text.tag_config("warn", foreground="#ce9178")

    def _append_log(self, msg: str, tag: str = "info"):
        """鍚戞棩蹇楁杩藉姞娑堟伅锛堢嚎绋嬪畨鍏級"""
        def append():
            self.log_text.config(state="normal")
            self.log_text.insert(tk.END, msg + "\n", tag)
            self.log_text.see(tk.END)
            self.log_text.config(state="disabled")
        self.root.after(0, append)

    def _clear_log(self):
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", tk.END)
        self.log_text.config(state="disabled")

    def _set_status(self, msg: str):
        self.root.after(0, lambda: self.status_label.config(text=msg))

    def _set_buttons(self, running: bool):
        def set_btn():
            self.start_btn.config(state="disabled" if running else "normal")
            self.stop_btn.config(state="normal" if running else "disabled")
            self.url_entry.config(state="disabled" if running else "normal")
            self.requirements_text.config(state="disabled" if running else "normal")
        self.root.after(0, set_btn)

    def _on_start(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("鎻愮ず", "璇疯緭鍏ラ棶鍗烽摼鎺ワ紒")
            return
        if not self.config.get("api_key"):
            messagebox.showerror("閿欒", "璇峰厛鍦ㄨ缃腑閰嶇疆 API Key锛?)
            return

        self._clear_log()
        self.running = True
        self._set_buttons(True)
        self._set_status("杩愯涓?..")

        def task():
            req = self.requirements_text.get("1.0", tk.END).strip()
            success = run_task(
                url, req or "璇峰悎鐞嗗～鍐欓棶鍗?,
                self.config,
                log_cb=self._append_log,
                progress_cb=self._append_log,
            )
            self.running = False
            self._set_buttons(False)
            self._set_status("瀹屾垚" if success else "澶辫触")

        self._task_thread = threading.Thread(target=task, daemon=True)
        self._task_thread.start()

    def _on_stop(self):
        self.running = False
        self._set_status("宸插仠姝?)
        self._set_buttons(False)
        self._append_log("鐢ㄦ埛鍋滄浜嗕换鍔°€?, "warn")

    def _open_settings(self):
        SettingsDialog(self.root, self.config, self._on_settings_saved)

    def _on_settings_saved(self, new_cfg: Dict):
        self.config = new_cfg
        self._append_log("璁剧疆宸蹭繚瀛樸€?, "success")


class SettingsDialog:
    """璁剧疆瀵硅瘽妗?""

    def __init__(self, parent: tk.Tk, cfg: Dict, on_save: Callable):
        self.cfg = cfg
        self.on_save = on_save

        self.win = tk.Toplevel(parent)
        self.win.title("璁剧疆")
        self.win.geometry("520x430")
        self.win.resizable(False, False)
        self.win.transient(parent)
        self.win.grab_set()

        outer = tk.Frame(self.win, padx=20, pady=15)
        outer.pack(fill="both", expand=True)

        # API 閰嶇疆
        tk.Label(outer, text="API 閰嶇疆", font=("Microsoft YaHei", 11, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 5))

        row = 1
        fields = [
            ("API Key:", "api_key", 40),
            ("API URL:", "api_url", 40),
            ("Model:", "model", 40),
        ]
        self._vars = {}
        for label_text, key, width in fields:
            tk.Label(outer, text=label_text, font=("Microsoft YaHei", 9)).grid(
                row=row, column=0, sticky="w", pady=3)
            var = tk.StringVar(value=self.cfg.get(key, ""))
            self._vars[key] = var
            show = "*" * len(var.get()) if key == "api_key" else None
            entry = tk.Entry(outer, textvariable=var, font=("Microsoft YaHei", 9),
                             width=width, relief="solid", bd=1)
            entry.grid(row=row, column=1, columnspan=2, sticky="ew", pady=3, padx=(5, 0))
            row += 1

        # 濉啓璁剧疆
        tk.Label(outer, text="濉啓璁剧疆", font=("Microsoft YaHei", 11, "bold")).grid(
            row=row, column=0, columnspan=3, sticky="w", pady=(12, 5))
        row += 1

        tk.Label(outer, text="鏈€灏忕瓑寰?绉?:", font=("Microsoft YaHei", 9)).grid(
            row=row, column=0, sticky="w", pady=3)
        self._vars["wait_min"] = tk.StringVar(value=str(self.cfg.get("wait_min", 80)))
        tk.Entry(outer, textvariable=self._vars["wait_min"], font=("Microsoft YaHei", 9),
                 width=8, relief="solid", bd=1).grid(row=row, column=1, sticky="w", pady=3, padx=(5, 0))

        tk.Label(outer, text="鏈€澶х瓑寰?绉?:", font=("Microsoft YaHei", 9)).grid(
            row=row, column=2, sticky="w", pady=3, padx=(10, 0))
        self._vars["wait_max"] = tk.StringVar(value=str(self.cfg.get("wait_max", 100)))
        tk.Entry(outer, textvariable=self._vars["wait_max"], font=("Microsoft YaHei", 9),
                 width=8, relief="solid", bd=1).grid(row=row, column=2, sticky="w", pady=3, padx=(5, 0))
        row += 1

        tk.Label(outer, text="鎴浘淇濆瓨鐩綍:", font=("Microsoft YaHei", 9)).grid(
            row=row, column=0, sticky="w", pady=3)
        self._vars["screenshot_dir"] = tk.StringVar(value=self.cfg.get("screenshot_dir", "./screenshots"))
        tk.Entry(outer, textvariable=self._vars["screenshot_dir"], font=("Microsoft YaHei", 9),
                 width=28, relief="solid", bd=1).grid(row=row, column=1, sticky="ew", pady=3, padx=(5, 0))
        tk.Button(outer, text="娴忚...", command=self._browse_dir,
                  font=("Microsoft YaHei", 9), relief="flat", bg="#3498db", fg="white",
                  cursor="hand2").grid(row=row, column=2, sticky="w", pady=3, padx=(5, 0))
        row += 1

        # 娴忚鍣ㄧ獥鍙?        tk.Label(outer, text="娴忚鍣ㄧ獥鍙?, font=("Microsoft YaHei", 11, "bold")).grid(
            row=row, column=0, columnspan=3, sticky="w", pady=(12, 5))
        row += 1

        tk.Label(outer, text="瀹藉害:", font=("Microsoft YaHei", 9)).grid(
            row=row, column=0, sticky="w", pady=3)
        self._vars["browser_width"] = tk.StringVar(value=str(self.cfg.get("browser_width", 550)))
        tk.Entry(outer, textvariable=self._vars["browser_width"], font=("Microsoft YaHei", 9),
                 width=8, relief="solid", bd=1).grid(row=row, column=1, sticky="w", pady=3, padx=(5, 0))

        tk.Label(outer, text="楂樺害:", font=("Microsoft YaHei", 9)).grid(
            row=row, column=1, sticky="w", pady=3, padx=(60, 0))
        self._vars["browser_height"] = tk.StringVar(value=str(self.cfg.get("browser_height", 700)))
        tk.Entry(outer, textvariable=self._vars["browser_height"], font=("Microsoft YaHei", 9),
                 width=8, relief="solid", bd=1).grid(row=row, column=2, sticky="w", pady=3, padx=(5, 0))
        row += 1

        outer.columnconfigure(1, weight=1)

        # 鎸夐挳鍖?        btn_row = row + 1
        btn_frame = tk.Frame(outer)
        btn_frame.grid(row=btn_row, column=0, columnspan=3, pady=(15, 0))

        tk.Button(btn_frame, text="淇濆瓨璁剧疆", command=self._on_save,
                  font=("Microsoft YaHei", 10), bg="#27ae60", fg="white",
                  relief="flat", cursor="hand2", padx=20, pady=5
                  ).pack(side="left", padx=5)

        tk.Button(btn_frame, text="鎭㈠榛樿", command=self._on_reset,
                  font=("Microsoft YaHei", 10), bg="#f39c12", fg="white",
                  relief="flat", cursor="hand2", padx=20, pady=5
                  ).pack(side="left", padx=5)

        tk.Button(btn_frame, text="鍙栨秷", command=self.win.destroy,
                  font=("Microsoft YaHei", 10), bg="#95a5a6", fg="white",
                  relief="flat", cursor="hand2", padx=20, pady=5
                  ).pack(side="left", padx=5)

    def _browse_dir(self):
        d = filedialog.askdirectory()
        if d:
            self._vars["screenshot_dir"].set(d)

    def _on_save(self):
        new_cfg = {}
        for key, var in self._vars.items():
            val = var.get().strip()
            if key in ("wait_min", "wait_max", "browser_width", "browser_height"):
                try:
                    val = int(val)
                except ValueError:
                    messagebox.showerror("閿欒", f"{key} 蹇呴』鏄暣鏁帮紒")
                    return
            new_cfg[key] = val

        # 淇濈暀鏈湪鐣岄潰鏄剧ず鐨勫瓧娈?        for k in self.cfg:
            if k not in new_cfg:
                new_cfg[k] = self.cfg[k]

        save_config(new_cfg)
        self.on_save(new_cfg)
        self.win.destroy()

    def _on_reset(self):
        for key, var in self._vars.items():
            if key in DEFAULT_CONFIG:
                var.set(str(DEFAULT_CONFIG[key]))


# ==================== 涓荤▼搴忓叆鍙?====================
def main():
    if not HAS_TK:
        print("閿欒锛氭湭瀹夎 tkinter锛岃浣跨敤鍛戒护琛岀増鏈垨閲嶆柊瀹夎 Python锛堝寘鍚?tkinter锛夈€?)
        return

    root = tk.Tk()
    app = WJXGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
