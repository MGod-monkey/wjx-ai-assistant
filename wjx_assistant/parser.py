"""Questionnaire parser for WJX pages."""
from __future__ import annotations

import re
from typing import List

from selenium import webdriver
from selenium.webdriver.common.by import By

from .schema import Option, Question, TYPE_LABELS


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _element_text(elem) -> str:
    for getter in (
        lambda: elem.text,
        lambda: elem.get_attribute("textContent"),
        lambda: elem.get_attribute("innerText"),
    ):
        try:
            text = _normalize_text(getter() or "")
            if text:
                return text
        except Exception:
            pass
    return ""


def _first_text(parent, selectors: List[str]) -> str:
    for selector in selectors:
        try:
            text = _element_text(parent.find_element(By.CSS_SELECTOR, selector))
            if text:
                return text
        except Exception:
            pass
    return ""


def _clean_question_text(text: str) -> str:
    cleaned = _normalize_text(text)
    cleaned = re.sub(r"^\*?\s*\d+[.、．]?\s*", "", cleaned).strip()
    cleaned = re.sub(r"【请选择[^】]*】", "", cleaned).strip()
    return cleaned


def _is_required(div) -> bool:
    try:
        if div.get_attribute("req") == "1":
            return True
    except Exception:
        pass
    try:
        text = _element_text(div)
    except Exception:
        text = ""
    return "*" in text[:10] or "必答" in text[:30]


def _make_options(labels: List[str]) -> List[Option]:
    seen: List[str] = []
    for label in labels:
        cleaned = re.sub(r"^\s*[A-Z][.、．]?\s*", "", _normalize_text(label)).strip()
        if cleaned and cleaned not in seen:
            seen.append(cleaned)
    return [Option(label=label, value=chr(ord("A") + idx), index=idx + 1) for idx, label in enumerate(seen)]


def _extract_choice_options(div) -> List[Option]:
    selectors = [
        ".ui-controlgroup .label",
        ".ui-radio .label",
        ".ui-checkbox .label",
        ".ui-controlgroup > div",
        "li",
    ]
    for selector in selectors:
        labels = [_element_text(item) for item in div.find_elements(By.CSS_SELECTOR, selector)]
        options = _make_options([label for label in labels if label])
        if options:
            return options
    return []


def _extract_scale_options(div) -> List[Option]:
    labels = [_element_text(item) for item in div.find_elements(By.CSS_SELECTOR, ".scale-div li")]
    options = _make_options([label for label in labels if label])
    if options:
        return options
    labels = []
    for item in div.find_elements(By.CSS_SELECTOR, ".scale-div a"):
        label = item.get_attribute("title") or item.get_attribute("val") or _element_text(item)
        if label:
            labels.append(label)
    return _make_options(labels)


def _extract_sort_options(div) -> List[Option]:
    labels = [_element_text(item) for item in div.find_elements(By.CSS_SELECTOR, "ul li")]
    return _make_options([label for label in labels if label])


def _extract_matrix_options(driver: webdriver.Chrome, qid: str, div) -> List[Option]:
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

    labels = []
    for row in table.find_elements(By.TAG_NAME, "tr"):
        cells = row.find_elements(By.TAG_NAME, "td")
        if len(cells) < 2:
            continue
        row_label = _element_text(cells[0])
        choices = [_element_text(cell) for cell in cells[1:] if _element_text(cell)]
        if row_label and choices:
            labels.append(f"{row_label} | 选项: {' / '.join(choices)}")
    return _make_options(labels)


def parse_questionnaire(driver: webdriver.Chrome) -> List[Question]:
    questions: List[Question] = []
    for div in driver.find_elements(By.CSS_SELECTOR, "#divQuestion [topic]"):
        qid = div.get_attribute("topic")
        if not (qid and qid.isdigit()):
            continue
        raw_type = div.get_attribute("type") or ""
        title = _clean_question_text(_first_text(div, [".topichtml", ".field-label", ".field-title", ".topic-title", ".div_title_question"]))

        options: List[Option] = []
        if raw_type in {"3", "4"}:
            options = _extract_choice_options(div)
        elif raw_type == "5":
            options = _extract_scale_options(div)
        elif raw_type == "6":
            options = _extract_matrix_options(driver, qid, div)
        elif raw_type == "7":
            options = [Option(label="下拉选项", value="A", index=1)]
        elif raw_type == "11":
            options = _extract_sort_options(div)

        questions.append(Question(
            id=qid,
            raw_type=raw_type,
            title=title,
            options=options,
            required=_is_required(div),
            index=len(questions),
        ))
    return questions


def format_questionnaire_for_ai(questions: List[Question]) -> str:
    lines = []
    for q in questions:
        type_label = TYPE_LABELS.get(q.type, f"未知题型 {q.raw_type}")
        options = " | ".join(option.label for option in q.options) if q.options else "无选项"
        required = "必填" if q.required else "可选"
        lines.append(f"{q.id}. [{type_label}/{required}] {q.title} | 选项: {options}")
    return "\n".join(lines)