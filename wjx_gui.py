"""Tkinter GUI entry point for WJX AI Assistant."""
from __future__ import annotations

import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import Callable, Dict, Optional

import cv2
import numpy as np
from PIL import Image, ImageGrab

from wjx_assistant.config import DEFAULT_CONFIG, load_config, save_config
from wjx_assistant.runner import run_task


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
        self.root.geometry("860x660")
        self.root.minsize(760, 560)

        self.config = load_config()
        self.running = False
        self._task_thread: Optional[threading.Thread] = None

        self._build_ui()
        self._append_log("程序启动，请输入问卷链接和填写要求后点击开始。")

    def _build_ui(self):
        header = tk.Frame(self.root, bg="#263238", pady=8)
        header.pack(fill="x")
        tk.Label(
            header,
            text="WJX AI Assistant",
            font=("Microsoft YaHei", 15, "bold"),
            fg="white",
            bg="#263238",
        ).pack(side="left", padx=15)
        tk.Button(
            header,
            text="设置",
            command=self._open_settings,
            font=("Microsoft YaHei", 9),
            relief="flat",
            bg="#1976d2",
            fg="white",
            cursor="hand2",
            padx=12,
        ).pack(side="right", padx=10)

        input_frame = tk.Frame(self.root, padx=15, pady=10)
        input_frame.pack(fill="x")
        input_frame.columnconfigure(1, weight=1)

        tk.Label(input_frame, text="问卷链接:", font=("Microsoft YaHei", 10)).grid(row=0, column=0, sticky="w", pady=5)
        self.url_entry = tk.Entry(input_frame, font=("Microsoft YaHei", 10), relief="solid", bd=1)
        self.url_entry.grid(row=0, column=1, sticky="ew", pady=5)
        tk.Button(
            input_frame,
            text="粘贴二维码",
            command=self._paste_qr,
            font=("Microsoft YaHei", 9),
            relief="flat",
            bg="#6a1b9a",
            fg="white",
            cursor="hand2",
            padx=8,
        ).grid(row=0, column=2, sticky="w", pady=5, padx=(8, 0))

        tk.Label(input_frame, text="填写要求:", font=("Microsoft YaHei", 10)).grid(row=1, column=0, sticky="nw", pady=5)
        self.requirements_text = tk.Text(input_frame, font=("Microsoft YaHei", 9), height=4, relief="solid", bd=1, wrap="word")
        self.requirements_text.grid(row=1, column=1, columnspan=2, sticky="ew", pady=5)

        controls = tk.Frame(self.root, padx=15, pady=5)
        controls.pack(fill="x")
        self.start_btn = tk.Button(
            controls,
            text="开始填写",
            command=self._on_start,
            font=("Microsoft YaHei", 10, "bold"),
            bg="#2e7d32",
            fg="white",
            relief="flat",
            cursor="hand2",
            padx=18,
            pady=5,
        )
        self.start_btn.pack(side="left", padx=5)
        self.stop_btn = tk.Button(
            controls,
            text="停止",
            command=self._on_stop,
            font=("Microsoft YaHei", 10),
            bg="#c62828",
            fg="white",
            relief="flat",
            cursor="hand2",
            padx=18,
            pady=5,
            state="disabled",
        )
        self.stop_btn.pack(side="left", padx=5)
        tk.Button(
            controls,
            text="清空日志",
            command=self._clear_log,
            font=("Microsoft YaHei", 10),
            bg="#607d8b",
            fg="white",
            relief="flat",
            cursor="hand2",
            padx=18,
            pady=5,
        ).pack(side="left", padx=5)

        self.headless_var = tk.BooleanVar(value=bool(self.config.get("headless", False)))
        self.auto_submit_var = tk.BooleanVar(value=bool(self.config.get("auto_submit", True)))
        tk.Checkbutton(controls, text="无头模式", variable=self.headless_var, font=("Microsoft YaHei", 9)).pack(side="right", padx=6)
        tk.Checkbutton(controls, text="自动提交", variable=self.auto_submit_var, font=("Microsoft YaHei", 9)).pack(side="right", padx=6)

        self.status_label = tk.Label(self.root, text="就绪", anchor="w", font=("Microsoft YaHei", 9), fg="#546e7a", padx=15, pady=3)
        self.status_label.pack(fill="x")

        log_frame = tk.Frame(self.root, padx=15)
        log_frame.pack(fill="both", expand=True, pady=(0, 10))
        tk.Label(log_frame, text="日志输出:", font=("Microsoft YaHei", 10)).pack(anchor="w", pady=(5, 2))
        wrapper = tk.Frame(log_frame, bg="#d0d0d0", bd=1, relief="solid")
        wrapper.pack(fill="both", expand=True)
        scrollbar = tk.Scrollbar(wrapper)
        scrollbar.pack(side="right", fill="y")
        self.log_text = tk.Text(
            wrapper,
            font=("Consolas", 9),
            bg="#1e1e1e",
            fg="#d4d4d4",
            relief="flat",
            state="disabled",
            yscrollcommand=scrollbar.set,
            wrap="word",
        )
        self.log_text.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.log_text.yview)

    def _append_log(self, msg: str, tag: str = "info", add_newline: bool = True, **kwargs):
        def append():
            self.log_text.config(state="normal")
            suffix = "\n" if add_newline else ""
            self.log_text.insert(tk.END, str(msg) + suffix)
            self.log_text.see(tk.END)
            self.log_text.config(state="disabled")

        self.root.after(0, append)

    def _clear_log(self):
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", tk.END)
        self.log_text.config(state="disabled")

    def _set_status(self, msg: str):
        self.root.after(0, lambda: self.status_label.config(text=msg))

    def _set_running(self, running: bool):
        self.running = running

        def update():
            self.start_btn.config(state="disabled" if running else "normal")
            self.stop_btn.config(state="normal" if running else "disabled")
            self.url_entry.config(state="disabled" if running else "normal")
            self.requirements_text.config(state="disabled" if running else "normal")

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
            self._append_log(f"已识别二维码: {url}")
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

        self._clear_log()
        self._set_running(True)
        self._set_status("运行中...")

        def task():
            success = run_task(
                url,
                self.requirements_text.get("1.0", tk.END).strip() or "请合理填写问卷",
                cfg,
                log_cb=self._append_log,
                progress_cb=self._append_log,
                headless=bool(cfg.get("headless")),
            )
            self._set_running(False)
            self._set_status("完成" if success else "失败")

        self._task_thread = threading.Thread(target=task, daemon=True)
        self._task_thread.start()

    def _on_stop(self):
        messagebox.showinfo("提示", "当前任务会在本轮浏览器操作结束后停止。若页面已打开，也可以直接关闭浏览器。")
        self._append_log("已请求停止。")

    def _open_settings(self):
        SettingsDialog(self.root, self.config, self._on_settings_saved)

    def _on_settings_saved(self, new_cfg: Dict):
        self.config = new_cfg
        self.headless_var.set(bool(new_cfg.get("headless", False)))
        self.auto_submit_var.set(bool(new_cfg.get("auto_submit", True)))
        self._append_log("设置已保存。")


class SettingsDialog:
    def __init__(self, parent: tk.Tk, cfg: Dict, on_save: Callable[[Dict], None]):
        self.cfg = dict(DEFAULT_CONFIG)
        self.cfg.update(cfg)
        self.on_save = on_save
        self._vars: Dict[str, tk.Variable] = {}

        self.win = tk.Toplevel(parent)
        self.win.title("设置")
        self.win.geometry("560x520")
        self.win.resizable(False, False)
        self.win.transient(parent)
        self.win.grab_set()

        outer = tk.Frame(self.win, padx=18, pady=14)
        outer.pack(fill="both", expand=True)
        outer.columnconfigure(1, weight=1)

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
            tk.Label(outer, text=label + ":", font=("Microsoft YaHei", 9)).grid(row=row, column=0, sticky="w", pady=4)
            var = tk.StringVar(value=str(self.cfg.get(key, "")))
            self._vars[key] = var
            show = "*" if key == "api_key" and var.get() else None
            tk.Entry(outer, textvariable=var, show=show, font=("Microsoft YaHei", 9), relief="solid", bd=1).grid(
                row=row, column=1, sticky="ew", pady=4, padx=(8, 0)
            )
            if kind == "dir":
                tk.Button(outer, text="浏览", command=lambda k=key: self._browse_dir(k)).grid(row=row, column=2, padx=(6, 0))

        base = len(rows)
        self._vars["headless"] = tk.BooleanVar(value=bool(self.cfg.get("headless", False)))
        self._vars["auto_submit"] = tk.BooleanVar(value=bool(self.cfg.get("auto_submit", True)))
        tk.Checkbutton(outer, text="默认无头模式", variable=self._vars["headless"]).grid(row=base, column=1, sticky="w", pady=5)
        tk.Checkbutton(outer, text="自动提交", variable=self._vars["auto_submit"]).grid(row=base + 1, column=1, sticky="w", pady=5)

        buttons = tk.Frame(outer)
        buttons.grid(row=base + 2, column=0, columnspan=3, pady=18)
        tk.Button(buttons, text="保存", command=self._on_save, bg="#2e7d32", fg="white", relief="flat", padx=20, pady=5).pack(side="left", padx=5)
        tk.Button(buttons, text="恢复默认", command=self._on_reset, bg="#f9a825", fg="white", relief="flat", padx=20, pady=5).pack(side="left", padx=5)
        tk.Button(buttons, text="取消", command=self.win.destroy, bg="#78909c", fg="white", relief="flat", padx=20, pady=5).pack(side="left", padx=5)

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