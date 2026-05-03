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


def click_entry_button(driver: webdriver.Chrome, log_cb: Callable[..., None] = print) -> bool:
    keywords = ["开始作答", "开始答题", "立即参与", "开始填写", "马上去答", "参加答题", "进入答题"]
    for keyword in keywords:
        xpath = f"//*[self::button or self::a or self::div or self::span][contains(normalize-space(.), '{keyword}')]"
        try:
            for elem in driver.find_elements(By.XPATH, xpath):
                if elem.is_displayed() and elem.is_enabled():
                    log_cb(f"点击入口按钮: {elem.text.strip() or keyword}")
                    elem.click()
                    time.sleep(2)
                    return True
        except Exception:
            continue
    return False


def wait_for_questions(driver: webdriver.Chrome, timeout: int = 10) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if driver.find_elements(By.CSS_SELECTOR, "#divQuestion [topic]"):
            return True
        time.sleep(0.5)
    return False


def go_next_page(driver: webdriver.Chrome) -> bool:
    try:
        next_btn = driver.find_element(By.CSS_SELECTOR, "#divNext")
        if next_btn.is_displayed():
            next_btn.click()
            time.sleep(0.8)
            return True
    except Exception:
        pass
    return False