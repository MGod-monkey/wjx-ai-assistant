"""
闂嵎鏄?AI 濉啓绯荤粺 - 鏍稿績搴?
鎻愪緵闂嵎瑙ｆ瀽銆丄I 绛旀鐢熸垚銆侀棶鍗峰～鍐欑瓑鏍稿績鍔熻兘
"""
import json
import os
import random
import re
import time
from typing import Callable, Dict, List

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
def init_driver(cfg: Dict, headless: bool = False) -> webdriver.Chrome:
    """鏍规嵁閰嶇疆鍒濆鍖?Chrome 娴忚鍣?""
    option = webdriver.ChromeOptions()
    if headless:
        option.add_argument("--headless=new")
    option.add_experimental_option("excludeSwitches", ["enable-automation"])
    option.add_experimental_option("useAutomationExtension", False)
    driver = webdriver.Chrome(options=option)
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'},
    )
    if not headless:
        driver.set_window_size(cfg["browser_width"], cfg["browser_height"])
        driver.set_window_position(x=100, y=50)
    return driver


# ==================== 闂嵎瑙ｆ瀽妯″潡 ====================
def _click_entry_button(driver: webdriver.Chrome, log_cb: Callable[..., None] = print) -> bool:
    """
    妫€娴嬪苟鐐瑰嚮闂嵎灏侀潰椤电殑"寮€濮嬩綔绛?/"杩涘叆"绛夊叆鍙ｆ寜閽紝
    绛夊緟鐪熸鐨勯棶鍗烽鐩姞杞藉畬鎴愬悗杩斿洖 True锛涙壘涓嶅埌鍒欒繑鍥?False銆?
    """
    entry_keywords = [
        "寮€濮嬩綔绛?, "寮€濮嬬瓟棰?, "绔嬪嵆鍙備笌", "寮€濮嬪～鍐?,
        "椹笂鍘荤瓟", "鍙傚姞绛旈", "鍙備笌绛旈", "杩涘叆绛旈",
    ]

    for keyword in entry_keywords:
        try:
            buttons = driver.find_elements(By.XPATH, "//button")
            for btn in buttons:
                if keyword in btn.text.strip():
                    log_cb(f"鐐瑰嚮鍏ュ彛鎸夐挳: 銆寋btn.text.strip()}銆?)
                    btn.click()
                    time.sleep(2)
                    return True
        except Exception:
            pass

        try:
            xpath = f"//*[contains(text(), '{keyword}')]"
            elems = driver.find_elements(By.XPATH, xpath)
            for elem in elems:
                try:
                    if elem.is_displayed() and elem.is_enabled():
                        log_cb(f"鐐瑰嚮鍏ュ彛鎸夐挳: 銆寋elem.text.strip()}銆?)
                        elem.click()
                        time.sleep(2)
                        return True
                except Exception:
                    continue
        except Exception:
            pass

    return False


def _wait_for_questions(driver: webdriver.Chrome, timeout: int = 10, log_cb: Callable[..., None] = print) -> bool:
    """绛夊緟闂嵎棰樼洰鍔犺浇锛屾渶澶氱瓑寰?timeout 绉掞紝姣?2 绉掓娴嬩竴娆?""
    for _ in range(timeout // 2):
        try:
            page_num = len(driver.find_elements(By.XPATH, '//*[@id="divQuestion"]/fieldset'))
            if page_num > 0:
                return True
        except Exception:
            pass
        time.sleep(2)
    return False


def parse_questionnaire(driver: webdriver.Chrome) -> List[Dict]:
    """瑙ｆ瀽闂嵎椤甸潰锛岃繑鍥炵粨鏋勫寲鐨勯鐩垪琛?""
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

            options: List[str] = []
            if q_type == "1" or q_type == "2":
                pass
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
                    tbl = None
                    try:
                        tbl = driver.find_element(By.CSS_SELECTOR, f"#divRefTab{qid}")
                    except Exception:
                        pass
                    if tbl is None:
                        try:
                            q_div = driver.find_element(By.CSS_SELECTOR, f"#div{qid}")
                            tables = q_div.find_elements(By.TAG_NAME, "table")
                            for t in tables:
                                if t.find_elements(By.TAG_NAME, "tr"):
                                    tbl = t
                                    break
                        except Exception:
                            pass
                    if tbl is None:
                        try:
                            first_row = driver.find_element(By.CSS_SELECTOR, f"#drv{qid}_1")
                            tbl = first_row.find_element(By.XPATH, "./ancestor::table")
                        except Exception:
                            pass
                    if tbl is None:
                        raise Exception("鏈壘鍒扮煩闃甸 table")
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
                pass

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
    log_cb: Callable[..., None] = print,
) -> Dict:
    """璋冪敤 SiliconFlow API锛岃繑鍥?AI 鐢熸垚鐨勭瓟妗堝瓧鍏?""
    prompt = f"""璇锋牴鎹互涓嬮棶鍗峰唴瀹瑰拰鐢ㄦ埛鐨勫～鍐欒姹傦紝鐢熸垚姣忛亾棰樼殑绛旀銆?

銆愰棶鍗峰唴瀹广€?
{questionnaire_text}

銆愮敤鎴峰～鍐欒姹傘€?
{user_requirements}

銆愯緭鍑烘牸寮忚姹傘€?
璇蜂弗鏍间互绾?JSON 鏍煎紡杩斿洖绛旀锛屼笉瑕佸寘鍚换浣曞叾浠栨枃瀛楄鏄庛€傛牸寮忓涓嬶細
{{
    "1": "B",
    "2": ["A", "C"],
    "3": "杩欐槸涓€涓～鍐欑殑绛旀",
    ...
}}
璇存槑锛?
- 鍗曢€夐銆侀噺琛ㄩ銆佷笅鎷夋棰樸€佹粦鍧楅锛氬€煎繀椤讳负閫夐」瀛楁瘝锛堝 "A", "B", "C"锛夛紝涓嶈杩斿洖閫夐」鏂囨湰锛?
- 澶氶€夐锛氬€煎繀椤讳负閫夐」瀛楁瘝鍒楄〃锛堝 ["A", "C"]锛夛紝涓嶈杩斿洖閫夐」鏂囨湰锛?
- 濉┖棰橈細鍊间负瑕佸～鍐欑殑鍏蜂綋鏂囨湰
- 鐭╅樀棰橈細鍊间负姣忎釜灏忛鐨勯€夐」瀛楁瘝锛岄€楀彿鍒嗛殧锛堝 "A,B,C"锛?
- 鎺掑簭棰橈細鍊间负閫夐」瀛楁瘝鐨勬帓鍒楅『搴忥紝閫楀彿鍒嗛殧锛堝 "B,A,C"锛?
- 棰樺彿璇蜂笌闂嵎涓殑棰樺彿淇濇寔涓€鑷?
- 涓ユ牸鎸夌収鐢ㄦ埛瑕佹眰鐢熸垚绛旀
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
    streamed_len = 0
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
                    full_content += content
            except json.JSONDecodeError:
                continue

        # 姣忕Н绱竴娈垫枃瀛楀氨杈撳嚭涓€娆★紙闈為€愬瓧锛夛紝閬垮厤 GUI 杩囬鍒锋柊
        if len(full_content) > streamed_len:
            new_text = full_content[streamed_len:]
            log_cb(new_text, add_newline=False)
            streamed_len = len(full_content)

    log_cb("")

    answers = parse_ai_json_response(full_content)
    log_cb(f"\nAI 杩斿洖鐨勭瓟妗堣В鏋愮粨鏋滐細{answers}")
    return answers


def parse_ai_json_response(content: str) -> Dict:
    """浠?AI 杩斿洖鍐呭涓彁鍙?JSON锛屾敮鎸佸绉嶆牸寮忓閿?""
    if not content or not content.strip():
        raise Exception("AI 杩斿洖鍐呭涓虹┖")

    # 绛栫暐1锛氱洿鎺ユ彁鍙?{ ... } 鍖呰９鐨?JSON
    start = content.find("{")
    end = content.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = content[start:end + 1]
        try:
            parsed = json.loads(candidate)
            return {str(k).strip(): v for k, v in parsed.items()}
        except json.JSONDecodeError:
            pass

    # 绛栫暐2锛氭竻鐞嗗父瑙?AI 鏍煎紡闂鍚庨噸璇?
    cleaned = _preclean_json_content(content)
    start2 = cleaned.find("{")
    end2 = cleaned.rfind("}")
    if start2 != -1 and end2 != -1 and end2 > start2:
        candidate2 = cleaned[start2:end2 + 1]
        try:
            parsed2 = json.loads(candidate2)
            return {str(k).strip(): v for k, v in parsed2.items()}
        except json.JSONDecodeError:
            pass

    # 绛栫暐3锛氭彁鍙?"棰樺彿": "閫夐」" 鏍煎紡鐨勯敭鍊煎
    answers = _extract_qa_pairs(content)
    if answers:
        return answers

    raise Exception(f"鏃犳硶瑙ｆ瀽 AI 杩斿洖鐨?JSON 鍐呭锛歿content[:300]}")


def _preclean_json_content(content: str) -> str:
    """娓呯悊 AI 杈撳嚭涓父瑙佺殑鏍煎紡闂"""
    import re
    # 鍘婚櫎 markdown 浠ｇ爜鍧楁爣璁?
    content = re.sub(r"```json\s*", "", content)
    content = re.sub(r"```\s*", "", content)
    # 鍘婚櫎鎹㈣骞叉壈锛堝厑璁哥殑鎹㈣搴旇鍦ㄥ啋鍙锋垨閫楀彿鍚庯級
    # 鎶婇鍙峰墠鐨勬崲琛屽幓鎺夛紝濡?"  \n    "16": 鍙樻垚 "16":
    content = re.sub(r'"\s*\n\s*"', '"\n"', content)
    # 鍘婚櫎閫夐」鍊间腑澶氫綑鐨勫紩鍙峰寘鍥达紙濡?"B 鍙樻垚 B锛?
    content = re.sub(r'"([A-Za-z0-9\u4e00-\u9fff\u3000-\u303f\uff00-\uffef銆娿€嬶紙锛夈€庛€忋€屻€嵚穃s.,銆傦紝銆侊紒锛?;+\-]+?)"', r'"\1"', content)
    return content


def _extract_qa_pairs(content: str) -> Dict:
    """浠庢贩涔辩殑 AI 杈撳嚭涓彁鍙栭鍙?绛旀閿€煎"""
    import re
    answers = {}
    patterns = [
        r'"(\d+)"\s*:\s*"([^"]*)"',
        r'"(\d+)"\s*:\s*\[\s*([^\]]*)\s*\]',
        r'"(\d+)"\s*:\s*([A-Za-z\u4e00-\u9fff][A-Za-z0-9\u4e00-\u9fff]*)',
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, content):
            qid = match.group(1)
            raw_val = match.group(2).strip()
            if qid and raw_val:
                if "[" in pattern:
                    letters = re.findall(r'"([A-Z])"', raw_val)
                    answers[qid] = letters if letters else raw_val
                else:
                    val = raw_val.strip().strip(',').strip()
                    if val:
                        answers[qid] = val

    return answers if answers else {}


def _clean_answer_value(val: str) -> str:
    """娓呯悊绛旀鍊硷紝鍙繚鐣欓涓湁鏁堝瓧姣?鏁板瓧"""
    val = str(val).strip()
    # 濡傛灉鍊间互瀛楁瘝寮€澶达紝鎻愬彇绗竴涓瓧姣?
    if val and val[0].isalpha():
        return val[0]
    # 濡傛灉鏄函鏁板瓧
    if val.isdigit():
        return val
    # 鍚﹀垯杩斿洖鍘熷鍊?
    return val


def _safe_int(val, default: int = 0) -> int:
    """瀹夊叏杞崲涓烘暣鏁?""
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


def _clamp_option_idx(idx: int, option_count: int) -> int:
    """灏嗛€夐」绱㈠紩闄愬埗鍦ㄦ湁鏁堣寖鍥村唴锛? ~ option_count锛?""
    return max(1, min(idx, option_count))


def _safe_click_option(driver, qid: str, q_type: str, idx: int, log_cb: Callable[..., None]) -> bool:
    """閫氱敤閫夐」鐐瑰嚮锛氳嚜鍔ㄦ牴鎹鐩被鍨嬬‘瀹?CSS 閫夋嫨鍣紝骞跺湪鐐瑰嚮鍓嶅仛杈圭晫鏍￠獙"""
    try:
        if q_type == "3":
            opts = driver.find_elements(By.CSS_SELECTOR, f"#div{qid} > div.ui-controlgroup > div")
            tag = "鍗曢€夐"
        elif q_type == "4":
            opts = driver.find_elements(By.CSS_SELECTOR, f"#div{qid} > div.ui-controlgroup > div")
            tag = "澶氶€夐"
        elif q_type == "5":
            opts = driver.find_elements(By.CSS_SELECTOR, f"#div{qid} > div.scale-div > div > ul > li")
            tag = "閲忚〃棰?
        else:
            opts = []
            tag = "棰?

        count = len(opts)
        if count == 0:
            log_cb(f"棰?{qid}: 鏈壘鍒?{tag} 閫夐」鍏冪礌锛岃烦杩?)
            return False

        safe_idx = _clamp_option_idx(idx, count)
        if safe_idx != idx:
            log_cb(f"棰?{qid}: 绱㈠紩 {idx} 瓒呭嚭鑼冨洿锛屼慨姝ｄ负 {safe_idx}锛堝叡 {count} 椤癸級")

        opts[safe_idx - 1].click()
        return True
    except Exception as e:
        log_cb(f"棰?{qid}: 鐐瑰嚮澶辫触 - {e}")
        return False


# ==================== 闂嵎濉啓妯″潡 ====================
def option_letter_to_index(letter: str) -> int:
    """灏嗛€夐」瀛楁瘝 A/B/C... 杞崲涓?1-based 绱㈠紩锛屽彧璇嗗埆绾嫳鏂囧瓧姣?""
    letter = letter.strip().upper()
    if len(letter) == 1 and letter.isalpha():
        return ord(letter) - ord("A") + 1
    if letter.isdigit():
        return int(letter)
    return 0


def match_option_by_text(answer, options: List[str]) -> int:
    """灏?AI 杩斿洖鐨勯€夐」鏂囨湰鍖归厤鍒板疄闄呴€夐」鍒楄〃锛岃繑鍥?1-based 绱㈠紩"""
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


def _match_answer(driver, qid: str, q_type: str, answer, options: List[str], log_cb) -> int:
    """
    缁煎悎鍖归厤锛氫紭鍏堝瓧姣嶇储寮曪紝澶辫触鍒欐枃鏈尮閰?DOM 閫夐」鏂囧瓧銆?
    杩斿洖 1-based 绱㈠紩锛屾壘涓嶅埌杩斿洖 0銆?
    """
    answer_str = str(answer).strip()

    # 绛栫暐1锛氱函鑻辨枃瀛楁瘝绱㈠紩锛圓/B/C...锛?
    idx = option_letter_to_index(answer_str)
    if idx > 0:
        return idx

    # 绛栫暐2锛氭暟瀛楃储寮?
    if answer_str.isdigit():
        return int(answer_str)

    # 绛栫暐3锛氫粠 DOM 涓洿鎺ユ煡鎵鹃€夐」鏂囧瓧锛堟敮鎸佷腑鏂囧"鏄?鍚?鑳?涓嶅彲浠?绛夛級
    try:
        if q_type == "3" or q_type == "4":
            opts = driver.find_elements(By.CSS_SELECTOR, f"#div{qid} > div.ui-controlgroup > div")
        elif q_type == "5":
            opts = driver.find_elements(By.CSS_SELECTOR, f"#div{qid} > div.scale-div > div > ul > li")
        else:
            opts = []

        for i, opt_el in enumerate(opts, 1):
            text = opt_el.text.strip()
            if answer_str in text or text in answer_str:
                return i
    except Exception:
        pass

    # 绛栫暐4锛氭棫鐗堟枃鏈尮閰嶅厹搴?
    return match_option_by_text(answer, options)


def fill_questionnaire(
    driver: webdriver.Chrome,
    questions: List[Dict],
    answers: Dict,
    log_cb: Callable[..., None] = print,
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
                idx = _match_answer(driver, qid, q_type, answer, q["options"], log_cb)
                if idx == 0:
                    log_cb(f"棰?{qid}: 鏃犳硶鍖归厤绛旀銆寋answer}銆嶅埌閫夐」锛岃烦杩?)
                    continue
                clicked = _safe_click_option(driver, qid, q_type, idx, log_cb)
                if clicked:
                    log_cb(f"棰?{qid}: 閫夋嫨绗?{idx} 涓€夐」")

            elif q_type == "4":
                matched_any = False
                # 瑙ｆ瀽绛旀锛氭敮鎸?["A","B"] 鍒楄〃 鎴?"A,B,C" 瀛楃涓?
                if isinstance(answer, list):
                    parts = answer
                elif isinstance(answer, str):
                    parts = [p.strip() for p in answer.replace("锛?, ",").split(",")]
                else:
                    parts = []
                for part in parts:
                    idx = _match_answer(driver, qid, q_type, part, q["options"], log_cb)
                    if idx > 0 and _safe_click_option(driver, qid, q_type, idx, log_cb):
                        time.sleep(0.2)
                        matched_any = True
                if not matched_any:
                    log_cb(f"棰?{qid}: 鏃犳硶鍖归厤澶氶€夌瓟妗堛€寋answer}銆嶅埌閫夐」锛岃烦杩?)
                else:
                    log_cb(f"棰?{qid}: 澶氶€夊尮閰嶆垚鍔?)

            elif q_type == "5":
                idx = _match_answer(driver, qid, q_type, answer, q["options"], log_cb)
                if idx == 0:
                    log_cb(f"棰?{qid}: 鏃犳硶鍖归厤绛旀銆寋answer}銆嶅埌閫夐」锛岃烦杩?)
                    continue
                clicked = _safe_click_option(driver, qid, q_type, idx, log_cb)
                if clicked:
                    log_cb(f"棰?{qid}: 閲忚〃閫夋嫨绗?{idx} 椤?)

            elif q_type == "6":
                if isinstance(answer, str):
                    ans_list = [a.strip() for a in answer.split(",")]
                elif isinstance(answer, list):
                    ans_list = [str(a).strip() for a in answer]
                else:
                    ans_list = []
                tbl = None
                try:
                    tbl = driver.find_element(By.CSS_SELECTOR, f"#divRefTab{qid}")
                except Exception:
                    pass
                if tbl is None:
                    try:
                        q_div = driver.find_element(By.CSS_SELECTOR, f"#div{qid}")
                        tables = q_div.find_elements(By.TAG_NAME, "table")
                        for t in tables:
                            if t.find_elements(By.TAG_NAME, "tr"):
                                tbl = t
                                break
                    except Exception:
                        pass
                if tbl is None:
                    try:
                        first_row = driver.find_element(By.CSS_SELECTOR, f"#drv{qid}_1")
                        tbl = first_row.find_element(By.XPATH, "./ancestor::table")
                    except Exception:
                        pass
                if tbl is None:
                    log_cb(f"棰?{qid}: 鐭╅樀棰樻湭鎵惧埌 table DOM锛岃烦杩?)
                else:
                    rows = tbl.find_elements(By.TAG_NAME, "tr")
                    filled_rows = 0
                    row_seq = 0
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
                        row_seq += 1
                        if row_seq <= len(ans_list):
                            opt_val = ans_list[row_seq - 1]
                            if isinstance(opt_val, str) and opt_val.strip().isalpha():
                                opt_idx = option_letter_to_index(opt_val.strip())
                            else:
                                opt_idx = _safe_int(opt_val, 1)
                        else:
                            opt_idx = random.randint(1, len(option_cols))
                        opt_idx = max(1, min(opt_idx, len(option_cols)))
                        driver.find_element(
                            By.CSS_SELECTOR, f"#drv{qid}_{row_seq} > td:nth-child({opt_idx + 1})"
                        ).click()
                        time.sleep(0.15)
                        filled_rows += 1
                    log_cb(f"棰?{qid}: 鐭╅樀棰樺～鍐欏畬鎴愶紙{filled_rows}琛岋級")

            elif q_type == "7":
                driver.find_element(By.CSS_SELECTOR, f"#select2-q{qid}-container").click()
                time.sleep(0.5)
                if isinstance(answer, str) and answer.strip().isalpha():
                    idx = option_letter_to_index(answer)
                else:
                    idx = _safe_int(answer, 0)
                li_items = driver.find_elements(By.CSS_SELECTOR, f"#select2-q{qid}-results > li")
                if not li_items:
                    log_cb(f"棰?{qid}: 涓嬫媺閫夐」鏈壘鍒帮紝璺宠繃")
                    continue
                li_idx = max(1, min(idx + 1, len(li_items)))
                driver.find_element(
                    By.XPATH, f"//*[@id='select2-q{qid}-results']/li[{li_idx}]"
                ).click()
                log_cb(f"棰?{qid}: 涓嬫媺妗嗛€夋嫨绗?{idx} 椤?)

            elif q_type == "8":
                score = _safe_int(answer, random.randint(1, 100))
                driver.find_element(By.CSS_SELECTOR, f"#q{qid}").send_keys(str(score))
                log_cb(f"棰?{qid}: 婊戝潡璁剧疆 {score}")

            elif q_type == "11":
                opts = driver.find_elements(By.XPATH, f'//*[@id="div{qid}"]/ul/li')
                if not opts:
                    log_cb(f"棰?{qid}: 鎺掑簭棰樻湭鎵惧埌閫夐」锛岃烦杩?)
                    continue
                if isinstance(answer, str):
                    order = [i for i in (option_letter_to_index(c) for c in answer.split(",") if c.strip().isalpha()) if i > 0]
                elif isinstance(answer, list):
                    order = [i for i in (option_letter_to_index(c) for c in answer) if i > 0]
                else:
                    order = []
                # 杩囨护瓒呭嚭鑼冨洿鐨勭储寮?
                order = [max(1, min(i, len(opts))) for i in order]
                if not order:
                    order = list(range(1, len(opts) + 1))
                    random.shuffle(order)
                for pos, letter_idx in enumerate(order, 1):
                    target = random.randint(pos - 1, len(opts) - 1)
                    target = max(0, min(target, len(opts) - 1))
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


def _is_error_dialog_present(driver: webdriver.Chrome) -> bool:
    """
    缁煎悎妫€娴嬮棶鍗锋槦鐨勫悇绫婚敊璇彁绀猴紝杩斿洖 True 琛ㄧず鏈夐敊璇紙鏈～鍐欏畬鏁达級銆?
    妫€娴嬭寖鍥达細
    1. layui-layer 寮圭獥鍐呯殑閿欒鏂囧瓧
    2. 椤甸潰涓?.errorMessage 绛夐敊璇彁绀烘枃瀛?
    3. 闂嵎鏄熺壒鏈夌殑琛屽唴閿欒鎻愮ず锛堣鍥炵瓟姝ら銆佽濉啓璇ラ€夐」 绛夛級
    4. 浠讳綍鍙鐨勬彁绀烘€ч敊璇枃妗?
    """
    # 鍏堝揩閫熸鏌?URL锛屾彁浜ゆ垚鍔熷悗 URL 浼氬彉鍖栵紝鎻愪氦澶辫触鍒?URL 涓嶅彉
    # 杩欎竴姝ュ湪 submit() 閲屽凡缁忔湁鏇寸簿纭殑鍒ゆ柇锛岃繖閲屽彧鍋氳緟鍔?

    error_keywords = [
        "璇峰畬鍠?, "璇峰～鍐?, "绛旈鏈畬鎴?, "绛旈涓嶅畬鏁?,
        "璇峰洖绛?, "璇烽€夋嫨", "蹇呭～", "涓嶈兘涓虹┖",
        "璇峰厛", "鏈夐鐩湭浣滅瓟", "璇峰畬鎴?, "璇锋鏌?,
    ]

    # ---------- 鏂规硶1锛歭ayui-layer 寮圭獥 ----------
    try:
        layers = driver.find_elements(By.CSS_SELECTOR, ".layui-layer")
        for layer in layers:
            layer_displayed = layer.is_displayed()
            if not layer_displayed:
                continue
            try:
                layer_text = layer.text
                if layer_text:
                    for kw in error_keywords:
                        if kw in layer_text:
                            return True
                # 涔熸鏌?layer 鍐呮墍鏈夊厓绱犵殑鏂囨湰
                for el in layer.find_elements(By.XPATH, ".//*"):
                    try:
                        el_text = el.text.strip()
                        if el_text:
                            for kw in error_keywords:
                                if kw in el_text:
                                    return True
                    except Exception:
                        continue
            except Exception:
                continue
    except Exception:
        pass

    # ---------- 鏂规硶2锛氶〉闈腑鐨?.errorMessage 閿欒鎻愮ず ----------
    try:
        for el in driver.find_elements(By.CLASS_NAME, "errorMessage"):
            if not el.is_displayed():
                continue
            el_text = el.text.strip()
            if el_text:
                for kw in error_keywords:
                    if kw in el_text:
                        return True
    except Exception:
        pass

    # ---------- 鏂规硶3锛氬叏灞€鎼滅储鎵€鏈夊彲瑙佸厓绱犱腑鐨勯敊璇叧閿瓧 ----------
    # 浣跨敤 contains(., 'text') 浠ｆ浛 contains(text(), 'text')锛屾洿鍙潬鍦板尮閰嶆贩鍚堝唴瀹?
    try:
        for el in driver.find_elements(
            By.XPATH, "//*[contains(., '璇峰洖绛旀棰?)]"
        ):
            if el.is_displayed():
                return True
        for el in driver.find_elements(
            By.XPATH, "//*[contains(., '璇峰～鍐欒閫夐」')]"
        ):
            if el.is_displayed():
                return True
    except Exception:
        pass

    return False


def _close_dialog_and_get_incomplete_info(driver: webdriver.Chrome, log_cb: Callable[..., None] = print) -> List[str]:
    """
    鍏抽棴鎵€鏈夊脊绐楋紝灏濊瘯鎻愬彇鏈～鍐欑殑棰樼洰淇℃伅锛岃繑鍥炵己澶遍鐩弿杩板垪琛ㄣ€?
    """
    missing = []
    try:
        layers = driver.find_elements(By.CSS_SELECTOR, ".layui-layer")
        for layer in layers:
            try:
                # 鎻愬彇寮圭獥涓墍鏈夋枃鏈?
                layer_text = layer.text
                if not layer_text.strip():
                    continue
                log_cb(f"妫€娴嬪埌寮圭獥鎻愮ず: {layer_text[:100]}")
                # 灏濊瘯浠庡脊绐椾腑瑙ｆ瀽鍑虹己澶辩殑棰樼洰鏍囬
                topic_matches = re.findall(r'棰榌\s:锛歖?\d+[^\d]', layer_text)
                for m in topic_matches:
                    missing.append(m.strip())
            except Exception:
                pass
            try:
                # 鍏抽棴鎸夐挳锛堝彲鑳芥湁澶氫釜锛屼紭鍏堢偣鍖呭惈"纭畾"/"鎴戠煡閬撲簡"鐨勶級
                close_btns = layer.find_elements(By.XPATH, ".//button | .//a")
                for btn in close_btns:
                    try:
                        txt = btn.text.strip()
                        if any(k in txt for k in ["纭畾", "鐭ラ亾浜?, "鍏抽棴", "纭"]):
                            btn.click()
                            time.sleep(0.5)
                            break
                    except Exception:
                        continue
            except Exception:
                pass
    except Exception:
        pass
    return missing


def submit(
    driver: webdriver.Chrome,
    log_cb: Callable[..., None] = print,
) -> bool:
    """
    鎻愪氦闂嵎骞跺鐞嗗悇绉嶉獙璇併€?
    杩斿洖 True 琛ㄧず鎻愪氦鎴愬姛锛堣烦杞埌鎴愬姛椤碉級锛孎alse 琛ㄧず鎻愪氦澶辫触锛堟湁寮圭獥鎻愮ず锛夈€?
    """
    try:
        driver.find_element(By.XPATH, '//*[@id="ctlNext"]').click()
        time.sleep(2)
    except Exception as e:
        log_cb(f"鐐瑰嚮鎻愪氦鎸夐挳澶辫触: {e}")
        return False

    # 妫€鏌ユ槸鍚﹀嚭鐜颁簡閿欒寮圭獥锛堣瀹屽杽绛旈淇℃伅锛?
    if _is_error_dialog_present(driver):
        log_cb("妫€娴嬪埌鏈～鍐欏畬鏁存彁绀猴紝姝ｅ湪鑾峰彇缂哄け棰樼洰...")
        missing_info = _close_dialog_and_get_incomplete_info(driver, log_cb)
        if missing_info:
            log_cb(f"鍙兘缂哄け鐨勯鐩? {', '.join(missing_info)}")
        else:
            log_cb("璇锋墜鍔ㄦ鏌ユ槸鍚︽湁蹇呭～棰樼洰鏈～鍐?)
        return False

    # 鐐瑰嚮鏅鸿兘妫€娴嬫寜閽紙鑵捐闃叉按绾匡級
    try:
        driver.find_element(By.XPATH, '//*[@id="SM_BTN_1"]').click()
        time.sleep(3)
    except Exception:
        pass

    # 妫€鏌ユ粦鍧楅獙璇?
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

    # 澶勭悊鎻愪氦鍚庡彲鑳藉啀娆″脊鍑虹殑閿欒寮圭獥锛堟粦鍧楃瓑楠岃瘉鍚庨噸鏂拌Е鍙戞彁浜わ級
    if _is_error_dialog_present(driver):
        log_cb("妫€娴嬪埌鎻愪氦鍚庡脊绐楋紙楠岃瘉鏈€氳繃鎴栦粛鏈夐鐩己澶憋級...")
        _close_dialog_and_get_incomplete_info(driver, log_cb)
        return False

    # 娌℃湁閿欒寮圭獥锛岃鏄庢彁浜ゆ垚鍔?
    return True


# ==================== 鎴浘淇濆瓨妯″潡 ====================
def save_screenshot(
    driver: webdriver.Chrome,
    answers: Dict,
    questionnaire_text: str,
    save_dir: str,
    log_cb: Callable[..., None] = print,
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


# ==================== 浠诲姟鎵ц锛堜緵 GUI / CLI 璋冪敤锛?===================
def run_task(
    url: str,
    requirements: str,
    cfg: Dict,
    log_cb: Callable[..., None] = print,
    progress_cb: Callable[..., None] = None,
    headless: bool = False,
) -> bool:
    """鍦ㄧ嫭绔嬬嚎绋嬩腑鎵ц闂嵎濉啓浠诲姟"""
    driver = None
    try:
        driver = init_driver(cfg, headless=headless)
        log_cb(f"姝ｅ湪璁块棶: {url}")
        driver.get(url)
        time.sleep(3)

        # 妫€娴嬪苟澶勭悊闂嵎灏侀潰椤碉紙濡傛湁"寮€濮嬩綔绛?鎸夐挳鍒欑偣鍑昏繘鍏ワ級
        if _click_entry_button(driver, log_cb):
            log_cb("宸茶繘鍏ラ棶鍗烽〉闈?)

        # 绛夊緟棰樼洰鍔犺浇鍑烘潵锛堝皝闈㈤〉鐐瑰嚮鍚庨渶绛夊緟锛?
        if not _wait_for_questions(driver, timeout=10, log_cb=log_cb):
            log_cb("鏈兘妫€娴嬪埌闂嵎棰樼洰锛岄〉闈㈠彲鑳藉凡鍔犺浇瀹屾垚鎴栭渶瑕佺瓑寰?..")

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
        submit_success = submit(driver, log_cb)
        time.sleep(3)

        current_url = driver.current_url
        if submit_success and ("ActivitySubmit" in current_url or "SubmitSuc" in current_url or "Thanks" in driver.page_source):
            log_cb("鎻愪氦鎴愬姛锛?)
            save_screenshot(driver, answers, q_text, cfg["screenshot_dir"], log_cb)
            log_cb(f"\n浠诲姟瀹屾垚锛?)
            return True
        elif not submit_success:
            log_cb(f"鎻愪氦澶辫触锛屽綋鍓嶉〉闈? {current_url}锛屽彲鑳芥湁蹇呭～棰樻湭濉啓銆?)
            save_screenshot(driver, answers, q_text, cfg["screenshot_dir"], log_cb)
            return False
        else:
            log_cb(f"鎻愪氦瀹屾垚锛屽綋鍓嶉〉闈? {current_url}")
            save_screenshot(driver, answers, q_text, cfg["screenshot_dir"], log_cb)
            log_cb(f"\n浠诲姟瀹屾垚锛堟彁浜ょ粨鏋滃緟纭锛夛紒")
            return True

    except Exception as e:
        import traceback
        log_cb(f"\n绋嬪簭鎵ц鍑洪敊: {e}")
        traceback.print_exc()
        return False
    finally:
        if driver:
            driver.quit()
