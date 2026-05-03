"""Tkinter GUI entry point for WJX AI Assistant."""
from __future__ import annotations

import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Callable, Dict, Optional

import cv2
import numpy as np
from PIL import Image, ImageGrab

from wjx_assistant.config import DEFAULT_CONFIG, load_config, save_config
from wjx_assistant.runner import run_task

COLORS = {
    "bg": "#f5f7fb",
    "panel": "#ffffff",
    "line": "#d8dee9",
    "text": "#1f2933",
    "muted": "#617083",
    "primary": "#1769aa",
    "primary_hover": "#0d5c9c",
    "success": "#1b7f4c",
    "danger": "#b42318",
    "warning": "#946200",
    "log_bg": "#111827",
    "log_text": "#d1d5db",
}


def decode_qr_from_image(image: Image.Image) -> Optional[str]:
    rgb = image.convert("RGB")
    arr = np.array(rgb)
    bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
    detector = cv2.QRCodeDetector()
    data, _, _ = detector.detectAndDecode(bgr)
    return data if data else None


class WJXGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("WJX AI Assistant")
        self.root.geometry("980x720")
        self.root.minsize(860, 620)
        self.root.configure(bg=COLORS["bg"])

        self.config = load_config()
        self.running = False
        self.stop_event = threading.Event()
        self._task_thread: Optional[threading.Thread] = None

        self._configure_style()
        self._build_ui()
        self._append_log("程序启动。请确认只在授权问卷或测试问卷中使用。", "info")

    def _configure_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Root.TFrame", background=COLORS["bg"])
        style.configure("Panel.TFrame", background=COLORS["panel"], relief="solid", borderwidth=1)
        style.configure("Title.TLabel", background=COLORS["bg"], foreground=COLORS["text"], font=("Microsoft YaHei", 18, "bold"))
        style.configure("Subtitle.TLabel", background=COLORS["bg"], foreground=COLORS["muted"], font=("Microsoft YaHei", 9))
        style.configure("PanelTitle.TLabel", background=COLORS["panel"], foreground=COLORS["text"], font=("Microsoft YaHei", 11, "bold"))
        style.configure("Body.TLabel", background=COLORS["panel"], foreground=COLORS["text"], font=("Microsoft YaHei", 9))
        style.configure("Muted.TLabel", background=COLORS["panel"], foreground=COLORS["muted"], font=("Microsoft YaHei", 9))
        style.configure("Primary.TButton", font=("Microsoft YaHei", 10, "bold"), padding=(14, 7))
        style.configure("Tool.TButton", font=("Microsoft YaHei", 9), padding=(10, 5))
        style.configure("TCheckbutton", background=COLORS["panel"], foreground=COLORS["text"], font=("Microsoft YaHei", 9))
        style.configure("Horizontal.TProgressbar", troughcolor="#e5eaf1", background=COLORS["primary"])

    def _build_ui(self):
        outer = ttk.Frame(self.root, style="Root.TFrame", padding=18)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(2, weight=1)

        self._build_header(outer)
        self._build_workspace(outer)
        self._build_log_panel(outer)

    def _build_header(self, parent):
        header = ttk.Frame(parent, style="Root.TFrame")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        header.columnconfigure(0, weight=1)

        title_box = ttk.Frame(header, style="Root.TFrame")
        title_box.grid(row=0, column=0, sticky="w")
        ttk.Label(title_box, text="WJX AI Assistant", style="Title.TLabel").pack(anchor="w")
        ttk.Label(title_box, text="问卷解析、AI 答案生成、自动填写与运行报告", style="Subtitle.TLabel").pack(anchor="w", pady=(2, 0))

        right = ttk.Frame(header, style="Root.TFrame")
        right.grid(row=0, column=1, sticky="e")
        self.status_badge = tk.Label(
            right,
            text="就绪",
            bg="#e8f2ff",
            fg=COLORS["primary"],
            padx=12,
            pady=5,
            font=("Microsoft YaHei", 9, "bold"),
        )
        self.status_badge.pack(side="left", padx=(0, 8))
        ttk.Button(right, text="设置", style="Tool.TButton", command=self._open_settings).pack(side="left")

    def _build_workspace(self, parent):
        workspace = ttk.Frame(parent, style="Root.TFrame")
        workspace.grid(row=1, column=0, sticky="ew", pady=(0, 14))
        workspace.columnconfigure(0, weight=3)
        workspace.columnconfigure(1, weight=2)

        main_panel = ttk.Frame(workspace, style="Panel.TFrame", padding=14)
        main_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        main_panel.columnconfigure(1, weight=1)

        ttk.Label(main_panel, text="任务输入", style="PanelTitle.TLabel").grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))
        ttk.Label(main_panel, text="问卷链接", style="Body.TLabel").grid(row=1, column=0, sticky="w", pady=5)
        self.url_entry = ttk.Entry(main_panel, font=("Microsoft YaHei", 10))
        self.url_entry.grid(row=1, column=1, sticky="ew", pady=5, padx=(10, 8))
        ttk.Button(main_panel, text="二维码", style="Tool.TButton", command=self._paste_qr).grid(row=1, column=2, sticky="e", pady=5)

        ttk.Label(main_panel, text="填写要求", style="Body.TLabel").grid(row=2, column=0, sticky="nw", pady=5)
        req_frame = tk.Frame(main_panel, bg=COLORS["line"], bd=1)
        req_frame.grid(row=2, column=1, columnspan=2, sticky="ew", pady=5, padx=(10, 0))
        self.requirements_text = tk.Text(
            req_frame,
            height=5,
            relief="flat",
            bd=0,
            wrap="word",
            font=("Microsoft YaHei", 9),
            bg="#fbfcfe",
            fg=COLORS["text"],
            padx=8,
            pady=8,
        )
        self.requirements_text.pack(fill="both", expand=True)

        mode_row = ttk.Frame(main_panel, style="Panel.TFrame")
        mode_row.grid(row=3, column=1, columnspan=2, sticky="ew", pady=(6, 2), padx=(10, 0))
        self.headless_var = tk.BooleanVar(value=bool(self.config.get("headless", False)))
        self.auto_submit_var = tk.BooleanVar(value=bool(self.config.get("auto_submit", True)))
        ttk.Checkbutton(mode_row, text="无头模式", variable=self.headless_var).pack(side="left", padx=(0, 16))
        ttk.Checkbutton(mode_row, text="自动提交", variable=self.auto_submit_var).pack(side="left")

        actions = ttk.Frame(main_panel, style="Panel.TFrame")
        actions.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(12, 0))
        self.start_btn = ttk.Button(actions, text="开始填写", style="Primary.TButton", command=self._on_start)
        self.start_btn.pack(side="left")
        self.stop_btn = ttk.Button(actions, text="停止", style="Tool.TButton", command=self._on_stop, state="disabled")
        self.stop_btn.pack(side="left", padx=8)
        ttk.Button(actions, text="清空日志", style="Tool.TButton", command=self._clear_log).pack(side="left")

        self.progress = ttk.Progressbar(actions, mode="indeterminate", length=170)
        self.progress.pack(side="right", padx=(8, 0))

        side_panel = ttk.Frame(workspace, style="Panel.TFrame", padding=14)
        side_panel.grid(row=0, column=1, sticky="nsew")
        side_panel.columnconfigure(0, weight=1)
        ttk.Label(side_panel, text="运行概览", style="PanelTitle.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 10))

        self.mode_text = ttk.Label(side_panel, text="", style="Body.TLabel", justify="left")
        self.mode_text.grid(row=1, column=0, sticky="ew", pady=4)
        self.output_text = ttk.Label(side_panel, text="", style="Muted.TLabel", justify="left", wraplength=310)
        self.output_text.grid(row=2, column=0, sticky="ew", pady=4)
        self.safety_text = ttk.Label(
            side_panel,
            text="遇到验证码、滑块或安全校验时会提示人工处理，不会绕过平台验证。",
            style="Muted.TLabel",
            justify="left",
            wraplength=310,
        )
        self.safety_text.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        self._refresh_overview()

    def _build_log_panel(self, parent):
        log_panel = ttk.Frame(parent, style="Panel.TFrame", padding=14)
        log_panel.grid(row=2, column=0, sticky="nsew")
        log_panel.rowconfigure(1, weight=1)
        log_panel.columnconfigure(0, weight=1)
        ttk.Label(log_panel, text="日志", style="PanelTitle.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 8))

        wrapper = tk.Frame(log_panel, bg=COLORS["line"], bd=1)
        wrapper.grid(row=1, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(wrapper)
        scrollbar.pack(side="right", fill="y")
        self.log_text = tk.Text(
            wrapper,
            font=("Consolas", 9),
            bg=COLORS["log_bg"],
            fg=COLORS["log_text"],
            relief="flat",
            state="disabled",
            yscrollcommand=scrollbar.set,
            wrap="word",
            padx=10,
            pady=10,
        )
        self.log_text.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.log_text.yview)
        self.log_text.tag_config("info", foreground=COLORS["log_text"])
        self.log_text.tag_config("success", foreground="#86efac")
        self.log_text.tag_config("warn", foreground="#fde68a")
        self.log_text.tag_config("error", foreground="#fca5a5")

    def _refresh_overview(self):
        mode = "无头模式" if self.headless_var.get() else "可视化浏览器"
        submit = "自动提交" if self.auto_submit_var.get() else "只填写不提交"
        self.mode_text.config(text=f"浏览器: {mode}\n提交: {submit}")
        self.output_text.config(text=f"报告目录: {self.config.get('output_dir', './runs')}")

    def _append_log(self, msg: str, tag: str = "info", add_newline: bool = True, **kwargs):
        text = str(msg)
        if "失败" in text or "出错" in text or "错误" in text:
            tag = "error"
        elif "停止" in text or "验证" in text or "跳过" in text:
            tag = "warn"
        elif "完成" in text or "保存" in text or "成功" in text:
            tag = "success"

        def append():
            self.log_text.config(state="normal")
            suffix = "\n" if add_newline else ""
            self.log_text.insert(tk.END, text + suffix, tag)
            self.log_text.see(tk.END)
            self.log_text.config(state="disabled")

        self.root.after(0, append)

    def _clear_log(self):
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", tk.END)
        self.log_text.config(state="disabled")

    def _set_status(self, msg: str, kind: str = "info"):
        colors = {
            "info": ("#e8f2ff", COLORS["primary"]),
            "success": ("#e9f8ef", COLORS["success"]),
            "warn": ("#fff7e6", COLORS["warning"]),
            "error": ("#fdecec", COLORS["danger"]),
        }
        bg, fg = colors.get(kind, colors["info"])
        self.root.after(0, lambda: self.status_badge.config(text=msg, bg=bg, fg=fg))

    def _set_running(self, running: bool):
        self.running = running

        def update():
            self.start_btn.config(state="disabled" if running else "normal")
            self.stop_btn.config(state="normal" if running else "disabled")
            self.url_entry.config(state="disabled" if running else "normal")
            self.requirements_text.config(state="disabled" if running else "normal")
            if running:
                self.progress.start(12)
                self._set_status("运行中", "info")
            else:
                self.progress.stop()

        self.root.after(0, update)

    def _paste_qr(self):
        try:
            img = ImageGrab.grabclipboard()
            if isinstance(img, list) and img:
                img = Image.open(img[0])
            if not isinstance(img, Image.Image):
                messagebox.showwarning("提示", "剪贴板中没有可识别的图片。")
                return
            url = decode_qr_from_image(img)
            if not url:
                messagebox.showerror("识别失败", "没有从图片中识别出有效二维码。")
                return
            self.url_entry.delete(0, tk.END)
            self.url_entry.insert(0, url)
            self._append_log(f"已识别二维码: {url}", "success")
        except Exception as exc:
            messagebox.showerror("错误", f"读取剪贴板或识别二维码失败: {exc}")

    def _on_start(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("提示", "请输入问卷链接。")
            return
        cfg = dict(self.config)
        cfg["headless"] = self.headless_var.get()
        cfg["auto_submit"] = self.auto_submit_var.get()
        if not cfg.get("api_key"):
            messagebox.showerror("错误", "请先在设置中配置 API Key，或设置 WJX_API_KEY 环境变量。")
            return

        self.stop_event.clear()
        self._clear_log()
        self._refresh_overview()
        self._set_running(True)

        def task():
            success = run_task(
                url,
                self.requirements_text.get("1.0", tk.END).strip() or "请合理填写问卷",
                cfg,
                log_cb=self._append_log,
                progress_cb=self._append_log,
                headless=bool(cfg.get("headless")),
                stop_event=self.stop_event,
            )
            self._set_running(False)
            self._set_status("完成" if success else "失败", "success" if success else "error")

        self._task_thread = threading.Thread(target=task, daemon=True)
        self._task_thread.start()

    def _on_stop(self):
        self.stop_event.set()
        self._set_status("停止中", "warn")
        self._append_log("已请求停止，当前浏览器操作结束后会中断任务。", "warn")

    def _open_settings(self):
        SettingsDialog(self.root, self.config, self._on_settings_saved)

    def _on_settings_saved(self, new_cfg: Dict):
        self.config = new_cfg
        self.headless_var.set(bool(new_cfg.get("headless", False)))
        self.auto_submit_var.set(bool(new_cfg.get("auto_submit", True)))
        self._refresh_overview()
        self._append_log("设置已保存。", "success")


class SettingsDialog:
    def __init__(self, parent: tk.Tk, cfg: Dict, on_save: Callable[[Dict], None]):
        self.cfg = dict(DEFAULT_CONFIG)
        self.cfg.update(cfg)
        self.on_save = on_save
        self._vars: Dict[str, tk.Variable] = {}

        self.win = tk.Toplevel(parent)
        self.win.title("设置")
        self.win.geometry("600x560")
        self.win.resizable(False, False)
        self.win.configure(bg=COLORS["bg"])
        self.win.transient(parent)
        self.win.grab_set()

        outer = ttk.Frame(self.win, style="Root.TFrame", padding=16)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(0, weight=1)

        ttk.Label(outer, text="运行设置", style="Title.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 12))
        panel = ttk.Frame(outer, style="Panel.TFrame", padding=14)
        panel.grid(row=1, column=0, sticky="nsew")
        panel.columnconfigure(1, weight=1)

        rows = [
            ("API Key", "api_key", "entry"),
            ("API URL", "api_url", "entry"),
            ("Model", "model", "entry"),
            ("最小等待(秒)", "wait_min", "entry"),
            ("最大等待(秒)", "wait_max", "entry"),
            ("截图目录", "screenshot_dir", "dir"),
            ("运行报告目录", "output_dir", "dir"),
            ("浏览器宽度", "browser_width", "entry"),
            ("浏览器高度", "browser_height", "entry"),
            ("最大重试次数", "max_retries", "entry"),
        ]
        for row, (label, key, kind) in enumerate(rows):
            ttk.Label(panel, text=label + ":", style="Body.TLabel").grid(row=row, column=0, sticky="w", pady=4)
            var = tk.StringVar(value=str(self.cfg.get(key, "")))
            self._vars[key] = var
            show = "*" if key == "api_key" and var.get() else None
            ttk.Entry(panel, textvariable=var, show=show, font=("Microsoft YaHei", 9)).grid(row=row, column=1, sticky="ew", pady=4, padx=(10, 0))
            if kind == "dir":
                ttk.Button(panel, text="浏览", style="Tool.TButton", command=lambda k=key: self._browse_dir(k)).grid(row=row, column=2, padx=(6, 0))

        base = len(rows)
        self._vars["headless"] = tk.BooleanVar(value=bool(self.cfg.get("headless", False)))
        self._vars["auto_submit"] = tk.BooleanVar(value=bool(self.cfg.get("auto_submit", True)))
        ttk.Checkbutton(panel, text="默认无头模式", variable=self._vars["headless"]).grid(row=base, column=1, sticky="w", pady=(8, 2))
        ttk.Checkbutton(panel, text="自动提交", variable=self._vars["auto_submit"]).grid(row=base + 1, column=1, sticky="w", pady=2)

        buttons = ttk.Frame(outer, style="Root.TFrame")
        buttons.grid(row=2, column=0, sticky="e", pady=(14, 0))
        ttk.Button(buttons, text="保存", style="Primary.TButton", command=self._on_save).pack(side="left", padx=5)
        ttk.Button(buttons, text="恢复默认", style="Tool.TButton", command=self._on_reset).pack(side="left", padx=5)
        ttk.Button(buttons, text="取消", style="Tool.TButton", command=self.win.destroy).pack(side="left", padx=5)

    def _browse_dir(self, key: str):
        value = filedialog.askdirectory()
        if value:
            self._vars[key].set(value)

    def _on_reset(self):
        for key, value in DEFAULT_CONFIG.items():
            if key in self._vars:
                self._vars[key].set(value)

    def _on_save(self):
        new_cfg = dict(self.cfg)
        for key, var in self._vars.items():
            value = var.get()
            if key in {"wait_min", "wait_max", "browser_width", "browser_height", "max_retries"}:
                try:
                    value = int(value)
                except ValueError:
                    messagebox.showerror("错误", f"{key} 必须是整数。")
                    return
            new_cfg[key] = value
        save_config(new_cfg)
        self.on_save(load_config())
        self.win.destroy()


def main():
    root = tk.Tk()
    WJXGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()