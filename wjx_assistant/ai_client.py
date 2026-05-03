"""AI client and answer parsing."""
from __future__ import annotations

import json
import re
from typing import Any, Callable, Dict, List

import requests

from .config import AppConfig
from .parser import format_questionnaire_for_ai
from .schema import Question

MODEL_DISABLED_CODE = 30003


def build_prompt(questions: List[Question], requirements: str) -> str:
    questionnaire_text = format_questionnaire_for_ai(questions)
    return f"""请根据下面的问卷内容和填写要求生成答案。仅用于本人创建或已获授权的测试问卷。

问卷内容:
{questionnaire_text}

填写要求:
{requirements or '请合理填写问卷'}

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
- 排序题返回选项字母顺序，用英文逗号分隔。
- 题号必须与问卷题号一致。
"""


def _candidate_models(cfg: AppConfig) -> List[str]:
    models: List[str] = []
    for model in [cfg.model, *cfg.model_fallbacks]:
        model = str(model or "").strip()
        if model and model not in models:
            models.append(model)
    return models


def call_ai_api(questions: List[Question], requirements: str, cfg: AppConfig, log_cb: Callable[..., None] = print) -> Dict[str, Any]:
    if not cfg.api_key:
        raise RuntimeError("请先在 config.json、GUI 设置或 WJX_API_KEY 环境变量中配置 API Key。")

    errors: List[str] = []
    for model in _candidate_models(cfg):
        try:
            return _call_model(questions, requirements, cfg, model, log_cb)
        except RuntimeError as exc:
            message = str(exc)
            errors.append(message)
            if "模型已被禁用" in message and model != _candidate_models(cfg)[-1]:
                log_cb(f"模型 {model} 不可用，正在尝试备用模型...")
                continue
            raise
    raise RuntimeError("; ".join(errors) if errors else "没有可用模型。")


def _call_model(questions: List[Question], requirements: str, cfg: AppConfig, model: str, log_cb: Callable[..., None]) -> Dict[str, Any]:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": build_prompt(questions, requirements)}],
        "stream": True,
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Bearer {cfg.api_key}",
    }

    log_cb(f"正在调用 AI 生成答案，请稍候... 模型: {model}")
    response = requests.post(cfg.api_url, json=payload, headers=headers, stream=True, timeout=120)
    if response.status_code != 200:
        raise RuntimeError(_format_api_error(response, model))

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


def _format_api_error(response: requests.Response, model: str) -> str:
    raw = response.text
    try:
        data = response.json()
    except ValueError:
        data = {}
    code = data.get("code")
    message = data.get("message") or raw
    if response.status_code == 403 and code == MODEL_DISABLED_CODE:
        return (
            f"模型已被禁用: {model}。请在设置中改用可用模型，例如 deepseek-ai/DeepSeek-V3，"
            "或通过 SiliconFlow 的 /v1/models 接口查看当前账号可用模型。"
        )
    return f"API 请求失败: {response.status_code} {message}"


def parse_ai_json_response(content: str) -> Dict[str, Any]:
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
    fallback = _extract_simple_pairs(cleaned)
    if fallback:
        return fallback
    raise RuntimeError(f"无法解析 AI 返回的 JSON: {content[:300]}")


def _extract_simple_pairs(content: str) -> Dict[str, str]:
    answers: Dict[str, str] = {}
    for match in re.finditer(r'"?(\d+)"?\s*[:：]\s*"?([A-Za-z0-9,，\u4e00-\u9fff ]+)"?', content):
        answers[match.group(1)] = match.group(2).strip().rstrip(",，")
    return answers