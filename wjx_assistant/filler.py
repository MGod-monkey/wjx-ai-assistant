"""Question filling handlers."""
from __future__ import annotations

import time
from threading import Event
from typing import Any, Callable, Dict, Iterable, List

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

from .answers import option_letter_to_index
from .schema import Question


def _split_answer(answer: Any) -> List[str]:
    if isinstance(answer, list):
        return [str(item).strip() for item in answer if str(item).strip()]
    return [item.strip() for item in str(answer).replace("，", ",").split(",") if item.strip()]


def _safe_idx(idx: int, count: int) -> int:
    if count <= 0:
        return 0
    return max(1, min(idx, count))


def _scroll_into_view(driver, elem: WebElement) -> None:
    try:
        driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'center'});", elem)
        time.sleep(0.08)
    except Exception:
        pass


def _safe_click(driver, elem: WebElement) -> None:
    _scroll_into_view(driver, elem)
    try:
        elem.click()
    except Exception:
        driver.execute_script("arguments[0].click();", elem)


def _click_by_index(driver, elements: Iterable[WebElement], idx: int) -> bool:
    items = list(elements)
    if not items:
        return False
    safe = _safe_idx(idx, len(items))
    if safe <= 0:
        return False
    _safe_click(driver, items[safe - 1])
    return True


def _question_div(driver, qid: str) -> WebElement:
    return driver.find_element(By.CSS_SELECTOR, f"#div{qid}")


def _is_question_visible(driver, qid: str) -> bool:
    try:
        return _question_div(driver, qid).is_displayed()
    except Exception:
        return False


def _ensure_question_visible(driver, q: Question) -> None:
    if _is_question_visible(driver, q.id):
        return
    for _ in range(12):
        try:
            next_btn = driver.find_element(By.CSS_SELECTOR, "#divNext")
            if not next_btn.is_displayed():
                break
            _safe_click(driver, next_btn)
            time.sleep(0.6)
            if _is_question_visible(driver, q.id):
                return
        except Exception:
            break
    if not _is_question_visible(driver, q.id):
        raise RuntimeError("题目所在分页不可见，无法自动翻到该题")


def _find_choice_elements(driver, q: Question) -> List[WebElement]:
    selectors = [
        f"#div{q.id} .ui-radio .jqradio",
        f"#div{q.id} .ui-checkbox .jqcheck",
        f"#div{q.id} .ui-radio",
        f"#div{q.id} .ui-checkbox",
        f"#div{q.id} .ui-controlgroup .label",
    ]
    for selector in selectors:
        items = [item for item in driver.find_elements(By.CSS_SELECTOR, selector) if item.is_displayed()]
        if items:
            return items
    return []


def fill_questionnaire(
    driver,
    questions: List[Question],
    answers: Dict[str, Any],
    log_cb: Callable[..., None] = print,
    stop_event: Event | None = None,
) -> None:
    for q in questions:
        if stop_event and stop_event.is_set():
            log_cb("检测到停止请求，已中断后续题目填写。")
            return
        answer = answers.get(q.id, "")
        try:
            _ensure_question_visible(driver, q)
            if q.type == "text":
                fill_text(driver, q, answer)
                log_cb(f"题 {q.id}: 已填写文本")
            elif q.type in {"single", "scale"}:
                idx = option_letter_to_index(answer)
                fill_single_like(driver, q, idx)
                log_cb(f"题 {q.id}: 选择第 {idx} 项")
            elif q.type == "multiple":
                fill_multiple(driver, q, answer)
                log_cb(f"题 {q.id}: 已选择多选项")
            elif q.type == "matrix":
                fill_matrix(driver, q, answer)
                log_cb(f"题 {q.id}: 已填写矩阵题")
            elif q.type == "dropdown":
                fill_dropdown(driver, q, answer)
                log_cb(f"题 {q.id}: 已选择下拉项")
            elif q.type == "slider":
                fill_slider(driver, q, answer)
                log_cb(f"题 {q.id}: 已设置滑块值 {answer}")
            elif q.type == "sort":
                fill_sort(driver, q, answer)
                log_cb(f"题 {q.id}: 已尝试填写排序题")
            else:
                log_cb(f"题 {q.id}: 暂不支持题型 {q.raw_type}，已跳过")
        except Exception as exc:
            log_cb(f"题 {q.id}: 填写失败 - {exc}")
        time.sleep(0.2)


def fill_text(driver, q: Question, answer: Any) -> None:
    elem = driver.find_element(By.CSS_SELECTOR, f"#q{q.id}")
    _scroll_into_view(driver, elem)
    try:
        elem.clear()
        elem.send_keys(str(answer))
    except Exception:
        driver.execute_script(
            "arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('input')); arguments[0].dispatchEvent(new Event('change'));",
            elem,
            str(answer),
        )


def fill_single_like(driver, q: Question, idx: int) -> None:
    if q.type == "scale":
        selectors = [f"#div{q.id} .scale-div a", f"#div{q.id} .scale-div li", f"#div{q.id} li"]
        items: List[WebElement] = []
        for selector in selectors:
            items = [item for item in driver.find_elements(By.CSS_SELECTOR, selector) if item.is_displayed()]
            if items:
                break
    else:
        items = _find_choice_elements(driver, q)
    if not _click_by_index(driver, items, idx):
        raise RuntimeError("没有找到可点击选项")


def fill_multiple(driver, q: Question, answer: Any) -> None:
    values = _split_answer(answer)
    opts = _find_choice_elements(driver, q)
    if not opts:
        raise RuntimeError("没有找到多选选项")
    for value in values:
        _click_by_index(driver, opts, option_letter_to_index(value))
        time.sleep(0.1)


def fill_matrix(driver, q: Question, answer: Any) -> None:
    values = _split_answer(answer)
    rows = driver.find_elements(By.CSS_SELECTOR, f"#divRefTab{q.id} tr[rowindex]")
    if not rows:
        rows = driver.find_elements(By.CSS_SELECTOR, f"#div{q.id} table tr[rowindex]")
    rows = [row for row in rows if row.is_displayed()]
    if not rows:
        raise RuntimeError("没有找到矩阵行")
    for pos, row in enumerate(rows, 1):
        cells = [cell for cell in row.find_elements(By.TAG_NAME, "td") if cell.is_displayed()]
        if len(cells) < 2:
            continue
        raw = values[pos - 1] if pos - 1 < len(values) else "A"
        idx = _safe_idx(option_letter_to_index(raw), len(cells) - 1)
        if idx > 0:
            _safe_click(driver, cells[idx])
            time.sleep(0.1)


def fill_dropdown(driver, q: Question, answer: Any) -> None:
    idx = option_letter_to_index(answer)
    container_selectors = [f"#select2-q{q.id}-container", f"#q{q.id}"]
    clicked = False
    for selector in container_selectors:
        try:
            elem = driver.find_element(By.CSS_SELECTOR, selector)
            if elem.is_displayed():
                _safe_click(driver, elem)
                clicked = True
                break
        except Exception:
            pass
    if not clicked:
        raise RuntimeError("没有找到下拉框")
    time.sleep(0.3)
    items = [item for item in driver.find_elements(By.CSS_SELECTOR, f"#select2-q{q.id}-results > li") if item.is_displayed()]
    if items:
        _click_by_index(driver, items, idx + 1)
        return
    options = [item for item in driver.find_elements(By.CSS_SELECTOR, f"#q{q.id} option") if item.is_displayed()]
    if not _click_by_index(driver, options, idx):
        raise RuntimeError("没有找到下拉选项")


def fill_slider(driver, q: Question, answer: Any) -> None:
    elem = driver.find_element(By.CSS_SELECTOR, f"#q{q.id}")
    value = str(answer).strip() or "80"
    _scroll_into_view(driver, elem)
    try:
        elem.clear()
        elem.send_keys(value)
    except Exception:
        driver.execute_script(
            "arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('input')); arguments[0].dispatchEvent(new Event('change'));",
            elem,
            value,
        )


def fill_sort(driver, q: Question, answer: Any) -> None:
    values = _split_answer(answer)
    items = [item for item in driver.find_elements(By.CSS_SELECTOR, f"#div{q.id} ul li") if item.is_displayed()]
    if not items:
        raise RuntimeError("没有找到排序选项")
    for value in values or [chr(ord("A") + i) for i in range(len(items))]:
        idx = option_letter_to_index(value)
        if not _click_by_index(driver, items, idx):
            break
        time.sleep(0.15)