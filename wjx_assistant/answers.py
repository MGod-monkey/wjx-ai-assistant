"""Answer validation and fallback generation."""
from __future__ import annotations

import random
import re
from typing import Any, Dict, List

from .schema import Question


def normalize_answer_value(value: Any) -> Any:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return str(value).strip()


def _clean_option_text(value: Any) -> str:
    text = str(value or "").strip()
    text = re.sub(r"^\s*[A-Z][.、．]?\s*", "", text, flags=re.IGNORECASE)
    return re.sub(r"\s+", "", text).lower()


def option_letter_to_index(value: Any) -> int:
    text = str(value).strip()
    if not text:
        return 1
    if text.isdigit():
        return max(1, int(text))
    first = text[0].upper()
    if "A" <= first <= "Z":
        return ord(first) - ord("A") + 1
    return 1


def option_value_to_index(question: Question, value: Any) -> int:
    text = str(value).strip()
    if not text:
        return 1
    if text.isdigit() or (text and "A" <= text[0].upper() <= "Z"):
        return option_letter_to_index(text)

    target = _clean_option_text(text)
    for idx, option in enumerate(question.options, 1):
        label = _clean_option_text(option.label)
        raw = _clean_option_text(option.value)
        if target and (target == label or target == raw or target in label or label in target):
            return idx
    return 1


def default_answer(question: Question) -> Any:
    if question.type == "text":
        return "满意"
    if question.type == "multiple":
        return ["A"]
    if question.type == "matrix":
        count = max(1, len(question.options))
        return ",".join("A" for _ in range(count))
    if question.type == "slider":
        return "80"
    if question.type == "sort":
        count = max(1, len(question.options))
        return ",".join(chr(ord("A") + idx) for idx in range(count))
    return "A"


def validate_answers(questions: List[Question], raw_answers: Dict[str, Any]) -> Dict[str, Any]:
    normalized: Dict[str, Any] = {}
    for q in questions:
        value = raw_answers.get(q.id, default_answer(q))
        value = normalize_answer_value(value)
        if q.type in {"single", "scale", "dropdown"}:
            idx = option_value_to_index(q, value)
            option_count = max(1, len(q.options))
            idx = max(1, min(idx, option_count))
            value = chr(ord("A") + idx - 1)
        elif q.type == "multiple":
            values = value if isinstance(value, list) else str(value).replace("，", ",").split(",")
            if not values:
                values = ["A"]
            option_count = max(1, len(q.options))
            clamped = []
            for item in values:
                idx = max(1, min(option_value_to_index(q, item), option_count))
                letter = chr(ord("A") + idx - 1)
                if letter not in clamped:
                    clamped.append(letter)
            value = clamped or ["A"]
        elif q.type == "slider":
            try:
                score = int(str(value))
            except ValueError:
                score = random.randint(60, 90)
            value = str(max(1, min(score, 100)))
        elif q.type in {"matrix", "sort"}:
            if isinstance(value, list):
                value = ",".join(str(item) for item in value)
            value = str(value).replace("，", ",") or default_answer(q)
        normalized[q.id] = value
    return normalized