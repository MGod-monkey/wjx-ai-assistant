"""Question filling handlers."""
from __future__ import annotations

import time
from typing import Any, Callable, Dict, List

from selenium.webdriver.common.by import By

from .answers import option_letter_to_index
from .schema import Question


def _click_by_index(elements, idx: int) -> bool:
    if not elements:
        return False
    safe_idx = max(1, min(idx, len(elements)))
    elements[safe_idx - 1].click()
    return True


def fill_questionnaire(driver, questions: List[Question], answers: Dict[str, Any], log_cb: Callable[..., None] = print) -> None:
    for q in questions:
        answer = answers.get(q.id, "")
        try:
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
                log_cb(f"题 {q.id}: 排序题暂不自动拖拽，已跳过")
            else:
                log_cb(f"题 {q.id}: 暂不支持题型 {q.raw_type}，已跳过")
        except Exception as exc:
            log_cb(f"题 {q.id}: 填写失败 - {exc}")
        time.sleep(0.2)


def fill_text(driver, q: Question, answer: Any) -> None:
    elem = driver.find_element(By.CSS_SELECTOR, f"#q{q.id}")
    elem.clear()
    elem.send_keys(str(answer))


def fill_single_like(driver, q: Question, idx: int) -> None:
    if q.type == "scale":
        selector = f"#div{q.id} .scale-div li"
    else:
        selector = f"#div{q.id} > div.ui-controlgroup > div"
    _click_by_index(driver.find_elements(By.CSS_SELECTOR, selector), idx)


def fill_multiple(driver, q: Question, answer: Any) -> None:
    values = answer if isinstance(answer, list) else str(answer).split(",")
    opts = driver.find_elements(By.CSS_SELECTOR, f"#div{q.id} > div.ui-controlgroup > div")
    for value in values:
        _click_by_index(opts, option_letter_to_index(value))
        time.sleep(0.1)


def fill_matrix(driver, q: Question, answer: Any) -> None:
    values = answer if isinstance(answer, list) else str(answer).split(",")
    rows = driver.find_elements(By.CSS_SELECTOR, f"#divRefTab{q.id} tr[rowindex]")
    if not rows:
        rows = driver.find_elements(By.CSS_SELECTOR, f"#div{q.id} table tr[rowindex]")
    for pos, row in enumerate(rows, 1):
        cells = row.find_elements(By.TAG_NAME, "td")
        if len(cells) < 2:
            continue
        raw = values[pos - 1] if pos - 1 < len(values) else "A"
        idx = max(1, min(option_letter_to_index(raw), len(cells) - 1))
        cells[idx].click()
        time.sleep(0.1)


def fill_dropdown(driver, q: Question, answer: Any) -> None:
    idx = option_letter_to_index(answer)
    driver.find_element(By.CSS_SELECTOR, f"#select2-q{q.id}-container").click()
    time.sleep(0.3)
    items = driver.find_elements(By.CSS_SELECTOR, f"#select2-q{q.id}-results > li")
    _click_by_index(items, idx + 1)


def fill_slider(driver, q: Question, answer: Any) -> None:
    driver.find_element(By.CSS_SELECTOR, f"#q{q.id}").send_keys(str(answer))