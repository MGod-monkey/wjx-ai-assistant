"""Shared data structures for questionnaire parsing and filling."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List


@dataclass
class Option:
    """A selectable option parsed from a question."""

    label: str
    value: str = ""
    index: int = 0


@dataclass
class Question:
    """A normalized questionnaire question."""

    id: str
    raw_type: str
    title: str
    options: List[Option] = field(default_factory=list)
    required: bool = False
    index: int = 0

    @property
    def type(self) -> str:
        return normalize_question_type(self.raw_type)

    def to_prompt_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "title": self.title,
            "options": [option.label for option in self.options],
            "required": self.required,
        }


QUESTION_TYPES = {
    "1": "text",
    "2": "text",
    "3": "single",
    "4": "multiple",
    "5": "scale",
    "6": "matrix",
    "7": "dropdown",
    "8": "slider",
    "11": "sort",
}

TYPE_LABELS = {
    "text": "填空题",
    "single": "单选题",
    "multiple": "多选题",
    "scale": "量表题",
    "matrix": "矩阵题",
    "dropdown": "下拉题",
    "slider": "滑块题",
    "sort": "排序题",
    "unknown": "未知题型",
}


def normalize_question_type(raw_type: str) -> str:
    return QUESTION_TYPES.get(str(raw_type or ""), "unknown")