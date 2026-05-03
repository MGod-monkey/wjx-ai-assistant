"""Backward-compatible facade for older imports."""

from wjx_assistant import CONFIG_FILE, DEFAULT_CONFIG, AppConfig, load_config, run_task, save_config
from wjx_assistant.ai_client import parse_ai_json_response
from wjx_assistant.answers import option_letter_to_index, validate_answers
from wjx_assistant.browser import create_driver as init_driver
from wjx_assistant.filler import fill_questionnaire
from wjx_assistant.parser import format_questionnaire_for_ai, parse_questionnaire
from wjx_assistant.runner import submit

__all__ = [
    "CONFIG_FILE",
    "DEFAULT_CONFIG",
    "AppConfig",
    "load_config",
    "save_config",
    "run_task",
    "parse_ai_json_response",
    "option_letter_to_index",
    "validate_answers",
    "init_driver",
    "fill_questionnaire",
    "format_questionnaire_for_ai",
    "parse_questionnaire",
    "submit",
]