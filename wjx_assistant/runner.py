"""Task runner orchestration."""
from __future__ import annotations

import random
import time
from typing import Callable, Dict, Optional

from .ai_client import call_ai_api
from .answers import validate_answers
from .browser import click_entry_button, create_driver, go_next_page, wait_for_questions
from .config import AppConfig, get_config_object
from .filler import fill_questionnaire
from .parser import format_questionnaire_for_ai, parse_questionnaire
from .report import create_run_dir, save_run_report
from .validators import is_incomplete_prompt, is_manual_verification_page, validate_questionnaire_url


def submit(driver, auto_submit: bool, log_cb: Callable[..., None] = print) -> bool:
    if not auto_submit:
        log_cb("已按配置跳过提交，浏览器页面保留为待人工检查状态。")
        return True
    try:
        driver.find_element("css selector", "#ctlNext").click()
        time.sleep(3)
    except Exception as exc:
        log_cb(f"点击提交按钮失败: {exc}")
        return False

    page_text = driver.page_source
    if is_manual_verification_page(page_text):
        log_cb("检测到验证码/滑块/人机验证，请人工处理。")
        return False
    if is_incomplete_prompt(page_text):
        log_cb("检测到未完成提示，请检查必填题或页面提示。")
        return False
    return True


def run_task(
    url: str,
    requirements: str,
    cfg: Dict | AppConfig,
    log_cb: Callable[..., None] = print,
    progress_cb: Optional[Callable[..., None]] = None,
    headless: bool = False,
) -> bool:
    cfg_obj = get_config_object(cfg)
    if headless:
        cfg_obj.headless = True
    url = validate_questionnaire_url(url)
    run_dir = create_run_dir(cfg_obj)

    logs: list[str] = []

    def emit(msg: str, add_newline: bool = True, **kwargs):
        text = str(msg)
        if add_newline:
            logs.append(text)
        elif logs:
            logs[-1] += text
        else:
            logs.append(text)
        log_cb(msg, add_newline=add_newline, **kwargs)

    driver = None
    questions = []
    answers = {}
    try:
        driver = create_driver(cfg_obj)
        emit(f"正在访问: {url}")
        driver.get(url)
        time.sleep(3)

        if click_entry_button(driver, emit):
            emit("已进入问卷页面。")
        wait_for_questions(driver, timeout=10)

        emit("正在解析问卷内容...")
        questions = parse_questionnaire(driver)
        if not questions:
            emit("未能解析到问卷题目，请检查链接或页面结构。")
            return False
        emit(f"共解析到 {len(questions)} 道题。")

        if progress_cb:
            for q in questions:
                progress_cb(f"题 {q.id}: [{q.type}] {q.title[:40]}")

        raw_answers = call_ai_api(questions, requirements, cfg_obj, emit)
        answers = validate_answers(questions, raw_answers)

        emit("正在填写问卷...")
        fill_questionnaire(driver, questions, answers, emit)
        while go_next_page(driver):
            emit("已翻到下一页。")

        wait_time = random.randint(cfg_obj.wait_min, cfg_obj.wait_max)
        if wait_time > 0:
            emit(f"等待 {wait_time} 秒后提交...")
            time.sleep(wait_time)

        emit("正在提交...")
        return submit(driver, cfg_obj.auto_submit, emit)
    except Exception as exc:
        emit(f"任务执行出错: {exc}")
        return False
    finally:
        save_run_report(run_dir, driver, cfg_obj, questions, answers, logs, log_cb)
        if driver:
            driver.quit()


def parse_only(url: str, cfg: Dict | AppConfig, log_cb: Callable[..., None] = print):
    cfg_obj = get_config_object(cfg)
    url = validate_questionnaire_url(url)
    driver = None
    try:
        driver = create_driver(cfg_obj)
        driver.get(url)
        time.sleep(3)
        click_entry_button(driver, log_cb)
        wait_for_questions(driver, timeout=10)
        questions = parse_questionnaire(driver)
        return questions, format_questionnaire_for_ai(questions)
    finally:
        if driver:
            driver.quit()