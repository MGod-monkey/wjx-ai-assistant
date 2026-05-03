"""Input validation helpers."""
from __future__ import annotations

from urllib.parse import urlparse


def validate_questionnaire_url(url: str) -> str:
    cleaned = (url or "").strip()
    parsed = urlparse(cleaned)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("请输入有效的 http/https 问卷链接。")
    return cleaned


def is_manual_verification_page(page_text: str) -> bool:
    keywords = ["验证码", "滑块", "智能验证", "请按住滑块", "安全验证", "人机验证"]
    return any(keyword in page_text for keyword in keywords)


def is_incomplete_prompt(page_text: str) -> bool:
    keywords = ["请完成", "请填写", "请回答", "请选择", "必填", "不能为空"]
    return any(keyword in page_text for keyword in keywords)