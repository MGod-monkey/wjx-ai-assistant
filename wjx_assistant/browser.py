"""Browser setup and common Selenium helpers."""
from __future__ import annotations

import time
from typing import Callable

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .config import AppConfig


def create_driver(cfg: AppConfig, headless: bool | None = None) -> webdriver.Chrome:
    options = webdriver.ChromeOptions()
    use_headless = cfg.headless if headless is None else headless
    if use_headless:
        options.add_argument("--headless=new")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    driver = webdriver.Chrome(options=options)
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'},
    )
    if not use_headless:
        driver.set_window_size(cfg.browser_width, cfg.browser_height)
        driver.set_window_position(x=100, y=50)
    return driver


def wait_for_css(driver: webdriver.Chrome, selector: str, timeout: int = 10):
    return WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))


def _text(elem) -> str:
    return " ".join((elem.text or elem.get_attribute("textContent") or "").split())


def _safe_click(driver: webdriver.Chrome, elem) -> None:
    driver.execute_script("arguments[0].scrollIntoView({block:'center', inline:'center'});", elem)
    time.sleep(0.1)
    try:
        elem.click()
    except Exception:
        driver.execute_script("arguments[0].click();", elem)


def click_entry_button(driver: webdriver.Chrome, log_cb: Callable[..., None] = print) -> bool:
    keywords = ["开始作答", "开始答题", "立即参与", "开始填写", "马上去答", "参加答题", "进入答题"]
    precise_selectors = [
        "#cgstartbutton",
        ".lxstartBtn",
        ".slideChunkWord",
        "a",
        "button",
        "[role='button']",
    ]

    candidates = []
    for selector in precise_selectors:
        try:
            candidates.extend(driver.find_elements(By.CSS_SELECTOR, selector))
        except Exception:
            pass

    seen = set()
    for elem in candidates:
        try:
            elem_id = elem.id
            if elem_id in seen:
                continue
            seen.add(elem_id)
            label = _text(elem)
            if label not in keywords:
                continue
            target = elem
            if elem.tag_name.lower() not in {"a", "button"} and elem.get_attribute("role") != "button":
                try:
                    target = elem.find_element(By.XPATH, "./ancestor-or-self::*[self::a or self::button or @role='button' or contains(@class,'lxstartBtn')][1]")
                except Exception:
                    target = elem
            if target.is_displayed() and target.is_enabled():
                log_cb(f"点击入口按钮: {label}")
                _safe_click(driver, target)
                time.sleep(2)
                return True
        except Exception:
            continue
    return False


def wait_for_questions(driver: webdriver.Chrome, timeout: int = 10) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            visible_questions = [
                elem for elem in driver.find_elements(By.CSS_SELECTOR, "#divQuestion .field[topic]")
                if elem.is_displayed()
            ]
            if visible_questions:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def go_next_page(driver: webdriver.Chrome) -> bool:
    try:
        next_btn = driver.find_element(By.CSS_SELECTOR, "#divNext")
        if next_btn.is_displayed():
            _safe_click(driver, next_btn)
            time.sleep(0.8)
            return True
    except Exception:
        pass
    return False