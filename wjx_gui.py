"""
问卷星 AI 填写系统 - GUI 版本
调用 wjx_core.py 中的核心逻辑
"""
try:
    import tkinter as tk
    from tkinter import messagebox, filedialog
except ImportError:
    print("错误：未安装 tkinter。")
    exit(1)

import io
import threading
from typing import Callable, Dict, Optional

import cv2
import numpy as np
from PIL import Image, ImageGrab

import wjx_core


def decode_qr_from_image(image: Image.Image) -> Optional[str]:
    """用 cv2 解码 QR 码，返回链接或 None"""
    rgb = image.convert("RGB")
    arr = np.array(rgb)
    bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
    detector = cv2.QRCodeDetector()
    data, _, _ = detector.detectAndDecode(bgr)
    return data if data else None


class WJXGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("问卷星 AI 自动填写系统")
        self.root.geometry("820x640")
        self.root.minsize(700, 500)

        self.config = wjx_core.load_config()
        self.running = False
        self._task_thread: Optional[threading.Thread] = None

        self._build_ui()
        self._append_log("程序启动，请输入问卷链接和填写要求后点击「开始填写」。")

    def _build_ui(self):
        # ---- 顶部标题栏 ----
        header = tk.Frame(self.root, bg="#2c3e50", pady=8)
        header.pack(fill="x")
        tk.Label(
            header, text="问卷星 AI 自动填写系统",
            font=("Microsoft YaHei", 14, "bold"),
            fg="white", bg="#2c3e50"
        ).pack(side="left", padx=15)
        tk.Button(
            header, text="设置", command=self._open_settings,
            font=("Microsoft YaHei", 9), relief="flat", bg="#3498db", fg="white",
            cursor="hand2", padx=10
        ).pack(side="right", padx=10)

        # ---- 输入区 ----
        input_frame = tk.Frame(self.root, padx=15, pady=10)
        input_frame.pack(fill="x")

        tk.Label(input_frame, text="问卷链接:", font=("Microsoft YaHei", 10)).grid(
            row=0, column=0, sticky="nw", pady=5)
        self.url_entry = tk.Entry(input_frame, font=("Microsoft YaHei", 10), relief="solid", bd=1)
        self.url_entry.grid(row=0, column=1, sticky="ew", pady=5)

        qr_btn = tk.Button(input_frame, text="粘贴二维码", command=self._paste_qr,
                           font=("Microsoft YaHei", 9), relief="flat", bg="#8e44ad", fg="white",
                           cursor="hand2", padx=8)
        qr_btn.grid(row=0, column=2, sticky="w", pady=5, padx=(8, 0))

        input_frame.columnconfigure(1, weight=1)

        tk.Label(input_frame, text="填写要求:", font=("Microsoft YaHei", 10)).grid(
            row=1, column=0, sticky="nw", pady=5)
        self.requirements_text = tk.Text(input_frame, font=("Microsoft YaHei", 9),
                                          height=4, relief="solid", bd=1, wrap="word")
        self.requirements_text.grid(row=1, column=1, sticky="ew", pady=5)

        # ---- 按钮区 ----
        btn_frame = tk.Frame(self.root, padx=15, pady=5)
        btn_frame.pack(fill="x")

        self.start_btn = tk.Button(
            btn_frame, text="开始填写", command=self._on_start,
            font=("Microsoft YaHei", 10, "bold"), bg="#27ae60", fg="white",
            relief="flat", cursor="hand2", padx=20, pady=5
        )
        self.start_btn.pack(side="left", padx=5)

        self.stop_btn = tk.Button(
            btn_frame, text="停止", command=self._on_stop,
            font=("Microsoft YaHei", 10), bg="#e74c3c", fg="white",
            relief="flat", cursor="hand2", padx=20, pady=5, state="disabled"
        )
        self.stop_btn.pack(side="left", padx=5)

        tk.Button(
            btn_frame, text="清空日志", command=self._clear_log,
            font=("Microsoft YaHei", 10), bg="#95a5a6", fg="white",
            relief="flat", cursor="hand2", padx=20, pady=5
        ).pack(side="left", padx=5)

        # 无头模式勾选框
        self.headless_var = tk.BooleanVar(value=False)
        tk.Checkbutton(
            btn_frame, text="无头模式（不显示浏览器）",
            variable=self.headless_var,
            font=("Microsoft YaHei", 9),
            cursor="hand2",
            activeforeground="#2c3e50"
        ).pack(side="right", padx=10)

        # ---- 状态栏 ----
        self.status_label = tk.Label(
            self.root, text="就绪", anchor="w", font=("Microsoft YaHei", 9),
            fg="#7f8c8d", padx=15, pady=2
        )
        self.status_label.pack(fill="x")

        # ---- 日志区 ----
        log_frame = tk.Frame(self.root, padx=15)
        log_frame.pack(fill="both", expand=True, pady=(0, 10))

        tk.Label(log_frame, text="日志输出:", font=("Microsoft YaHei", 10)).pack(anchor="nw", pady=(5, 2))

        log_wrapper = tk.Frame(log_frame, bg="#dcdcdc", bd=1, relief="solid")
        log_wrapper.pack(fill="both", expand=True)

        scrollbar = tk.Scrollbar(log_wrapper)
        scrollbar.pack(side="right", fill="y")

        self.log_text = tk.Text(
            log_wrapper, font=("Consolas", 9), bg="#1e1e1e", fg="#d4d4d4",
            relief="flat", state="disabled", yscrollcommand=scrollbar.set,
            wrap="word"
        )
        self.log_text.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.log_text.yview)

        self.log_text.tag_config("info", foreground="#d4d4d4")
        self.log_text.tag_config("success", foreground="#4ec9b0")
        self.log_text.tag_config("error", foreground="#f44747")
        self.log_text.tag_config("warn", foreground="#ce9178")

    def _append_log(self, msg: str, tag: str = "info", add_newline: bool = True):
        def append():
            self.log_text.config(state="normal")
            suffix = "\n" if add_newline else ""
            self.log_text.insert(tk.END, msg + suffix, tag)
            self.log_text.see(tk.END)
            self.log_text.config(state="disabled")
        self.root.after(0, append)

    def _clear_log(self):
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", tk.END)
        self.log_text.config(state="disabled")

    def _set_status(self, msg: str):
        self.root.after(0, lambda: self.status_label.config(text=msg))

    def _set_buttons(self, running: bool):
        def set_btn():
            self.start_btn.config(state="disabled" if running else "normal")
            self.stop_btn.config(state="normal" if running else "disabled")
            self.url_entry.config(state="disabled" if running else "normal")
            self.requirements_text.config(state="disabled" if running else "normal")
        self.root.after(0, set_btn)

    def _paste_qr(self):
        """从剪贴板读取图片并识别二维码，填入链接框"""
        try:
            img = ImageGrab.grabclipboard()
            if img is None:
                messagebox.showwarning("提示", "剪贴板中没有图片，请先复制包含二维码的图片。")
                return

            # Windows 有时返回文件路径列表
            if isinstance(img, list):
                for path in img:
                    img = Image.open(path)
                    if img:
                        break
                else:
                    messagebox.showwarning("提示", "无法打开剪贴板中的图片文件。")
                    return

            if not isinstance(img, Image.Image):
                messagebox.showwarning("提示", "剪贴板内容不是图片格式。")
                return

            # 先检查图片尺寸，太小的可能是图标，跳过
            w, h = img.size
            if w < 50 or h < 50:
                messagebox.showwarning("提示", "图片尺寸太小（二维码图片通常需要至少 100px）。")
                return

            url = decode_qr_from_image(img)
            if url:
                self.url_entry.delete(0, tk.END)
                self.url_entry.insert(0, url)
                self._append_log(f"已识别二维码: {url}", "success")
            else:
                messagebox.showerror("识别失败", "无法从图片中识别出二维码，请确保图片清晰且包含有效的 QR 码。")
        except Exception as e:
            messagebox.showerror("错误", f"读取剪贴板或识别二维码时出错：{e}")

    def _on_start(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("提示", "请输入问卷链接！")
            return
        if not self.config.get("api_key"):
            messagebox.showerror("错误", "请先在设置中配置 API Key！")
            return

        self._clear_log()
        self.running = True
        self._set_buttons(True)
        self._set_status("运行中...")

        def task():
            req = self.requirements_text.get("1.0", tk.END).strip()
            headless = self.headless_var.get()
            if headless:
                self._append_log("无头模式已启用，浏览器将在后台运行。", "warn")
            success = wjx_core.run_task(
                url, req or "请合理填写问卷",
                self.config,
                log_cb=self._append_log,
                progress_cb=self._append_log,
                headless=headless,
            )
            self.running = False
            self._set_buttons(False)
            self._set_status("完成" if success else "失败")

        self._task_thread = threading.Thread(target=task, daemon=True)
        self._task_thread.start()

    def _on_stop(self):
        self.running = False
        self._set_status("已停止")
        self._set_buttons(False)
        self._append_log("用户停止了任务。", "warn")

    def _open_settings(self):
        SettingsDialog(self.root, self.config, self._on_settings_saved)

    def _on_settings_saved(self, new_cfg: Dict):
        self.config = new_cfg
        self._append_log("设置已保存。", "success")


class SettingsDialog:
    def __init__(self, parent: tk.Tk, cfg: Dict, on_save: Callable):
        self.cfg = cfg
        self.on_save = on_save
        self._vars = {}

        self.win = tk.Toplevel(parent)
        self.win.title("设置")
        self.win.geometry("520x430")
        self.win.resizable(False, False)
        self.win.transient(parent)
        self.win.grab_set()

        outer = tk.Frame(self.win, padx=20, pady=15)
        outer.pack(fill="both", expand=True)

        # API 配置
        tk.Label(outer, text="API 配置", font=("Microsoft YaHei", 11, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 5))

        row = 1
        fields = [
            ("API Key:", "api_key"),
            ("API URL:", "api_url"),
            ("Model:", "model"),
        ]
        for label_text, key in fields:
            tk.Label(outer, text=label_text, font=("Microsoft YaHei", 9)).grid(
                row=row, column=0, sticky="w", pady=3)
            var = tk.StringVar(value=self.cfg.get(key, ""))
            self._vars[key] = var
            tk.Entry(outer, textvariable=var, font=("Microsoft YaHei", 9),
                     width=40, relief="solid", bd=1).grid(
                row=row, column=1, columnspan=2, sticky="ew", pady=3, padx=(5, 0))
            row += 1

        # 填写设置
        tk.Label(outer, text="填写设置", font=("Microsoft YaHei", 11, "bold")).grid(
            row=row, column=0, columnspan=3, sticky="w", pady=(12, 5))
        row += 1

        tk.Label(outer, text="最小等待(秒):", font=("Microsoft YaHei", 9)).grid(
            row=row, column=0, sticky="w", pady=3)
        self._vars["wait_min"] = tk.StringVar(value=str(self.cfg.get("wait_min", 80)))
        tk.Entry(outer, textvariable=self._vars["wait_min"], font=("Microsoft YaHei", 9),
                 width=8, relief="solid", bd=1).grid(row=row, column=1, sticky="w", pady=3, padx=(5, 0))

        tk.Label(outer, text="最大等待(秒):", font=("Microsoft YaHei", 9)).grid(
            row=row, column=2, sticky="w", pady=3, padx=(10, 0))
        self._vars["wait_max"] = tk.StringVar(value=str(self.cfg.get("wait_max", 100)))
        tk.Entry(outer, textvariable=self._vars["wait_max"], font=("Microsoft YaHei", 9),
                 width=8, relief="solid", bd=1).grid(row=row, column=2, sticky="w", pady=3, padx=(5, 0))
        row += 1

        tk.Label(outer, text="截图保存目录:", font=("Microsoft YaHei", 9)).grid(
            row=row, column=0, sticky="w", pady=3)
        self._vars["screenshot_dir"] = tk.StringVar(value=self.cfg.get("screenshot_dir", "./screenshots"))
        tk.Entry(outer, textvariable=self._vars["screenshot_dir"], font=("Microsoft YaHei", 9),
                 width=28, relief="solid", bd=1).grid(row=row, column=1, sticky="ew", pady=3, padx=(5, 0))
        tk.Button(outer, text="浏览...", command=self._browse_dir,
                  font=("Microsoft YaHei", 9), relief="flat", bg="#3498db", fg="white",
                  cursor="hand2").grid(row=row, column=2, sticky="w", pady=3, padx=(5, 0))
        row += 1

        # 浏览器窗口
        tk.Label(outer, text="浏览器窗口", font=("Microsoft YaHei", 11, "bold")).grid(
            row=row, column=0, columnspan=3, sticky="w", pady=(12, 5))
        row += 1

        tk.Label(outer, text="宽度:", font=("Microsoft YaHei", 9)).grid(
            row=row, column=0, sticky="w", pady=3)
        self._vars["browser_width"] = tk.StringVar(value=str(self.cfg.get("browser_width", 550)))
        tk.Entry(outer, textvariable=self._vars["browser_width"], font=("Microsoft YaHei", 9),
                 width=8, relief="solid", bd=1).grid(row=row, column=1, sticky="w", pady=3, padx=(5, 0))

        tk.Label(outer, text="高度:", font=("Microsoft YaHei", 9)).grid(
            row=row, column=1, sticky="w", pady=3, padx=(60, 0))
        self._vars["browser_height"] = tk.StringVar(value=str(self.cfg.get("browser_height", 700)))
        tk.Entry(outer, textvariable=self._vars["browser_height"], font=("Microsoft YaHei", 9),
                 width=8, relief="solid", bd=1).grid(row=row, column=2, sticky="w", pady=3, padx=(5, 0))
        row += 1

        outer.columnconfigure(1, weight=1)

        # 按钮区
        btn_row = row + 1
        btn_frame = tk.Frame(outer)
        btn_frame.grid(row=btn_row, column=0, columnspan=3, pady=15)

        tk.Button(btn_frame, text="保存设置", command=self._on_save,
                  font=("Microsoft YaHei", 10), bg="#27ae60", fg="white",
                  relief="flat", cursor="hand2", padx=20, pady=5
                  ).pack(side="left", padx=5)

        tk.Button(btn_frame, text="恢复默认", command=self._on_reset,
                  font=("Microsoft YaHei", 10), bg="#f39c12", fg="white",
                  relief="flat", cursor="hand2", padx=20, pady=5
                  ).pack(side="left", padx=5)

        tk.Button(btn_frame, text="取消", command=self.win.destroy,
                  font=("Microsoft YaHei", 10), bg="#95a5a6", fg="white",
                  relief="flat", cursor="hand2", padx=20, pady=5
                  ).pack(side="left", padx=5)

    def _browse_dir(self):
        d = filedialog.askdirectory()
        if d:
            self._vars["screenshot_dir"].set(d)

    def _on_save(self):
        new_cfg = {}
        for key, var in self._vars.items():
            val = var.get().strip()
            if key in ("wait_min", "wait_max", "browser_width", "browser_height"):
                try:
                    val = int(val)
                except ValueError:
                    messagebox.showerror("错误", f"{key} 必须是整数！")
                    return
            new_cfg[key] = val

        for k in self.cfg:
            if k not in new_cfg:
                new_cfg[k] = self.cfg[k]

        wjx_core.save_config(new_cfg)
        self.on_save(new_cfg)
        self.win.destroy()

    def _on_reset(self):
        defaults = wjx_core.DEFAULT_CONFIG
        for key, var in self._vars.items():
            if key in defaults:
                var.set(str(defaults[key]))


def main():
    root = tk.Tk()
    app = WJXGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
