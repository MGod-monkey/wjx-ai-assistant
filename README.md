# WJX AI Assistant

WJX AI Assistant 是一个面向问卷星页面的本地辅助工具。它会解析问卷题目，调用兼容 OpenAI Chat Completions 格式的 API 生成答案，并通过 Selenium 在浏览器中完成填写。

请只在自己创建的问卷、内部测试问卷或已获得授权的场景中使用。本项目不会也不应被用于刷量、作弊、绕过平台风控或提交未经授权的数据。遇到验证码、滑块或人机校验时，系统只会提示人工处理，不做绕过。

## 功能

- 解析问卷星常见题型：填空、单选、多选、量表、矩阵、下拉、滑块、排序等。
- 支持 GUI 和命令行两种入口。
- 支持从剪贴板二维码识别问卷链接。
- 支持自定义 API 地址、模型、等待时间、浏览器尺寸、是否自动提交和运行报告目录。
- 每次运行保存题目、答案、脱敏配置、截图和 HTML 快照，方便排查。
- 保留 `wjx_core.py` 兼容层，旧入口仍可导入 `load_config()`、`save_config()`、`run_task()`。

## 文件结构

```text
.
├── wjx_assistant/
│   ├── config.py      # 配置读取、校验、脱敏
│   ├── schema.py      # Question / Option 数据结构
│   ├── browser.py     # Selenium 启动、等待和翻页
│   ├── parser.py      # 问卷题目解析
│   ├── ai_client.py   # AI API 调用和 JSON 解析
│   ├── answers.py     # 答案合法性校验和默认答案
│   ├── filler.py      # 各题型填写逻辑
│   ├── report.py      # 运行报告保存
│   └── runner.py      # 一次任务的完整流程
├── wjx_core.py        # 兼容旧代码的导出层
├── wjx_gui.py         # Tkinter 图形界面入口
├── wjx_cli.py         # 命令行入口
├── config.example.json
├── requirements.txt
└── tests/
```

## 安装

建议使用 Python 3.10 或更新版本。

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

还需要本机安装 Chrome 浏览器。Selenium 4 会优先自动管理驱动；如果自动驱动不可用，请自行安装匹配 Chrome 版本的 ChromeDriver。

## 配置

复制配置示例：

```bash
copy config.example.json config.json
```

然后编辑 `config.json`：

```json
{
  "api_key": "你的 API Key",
  "api_url": "https://api.siliconflow.cn/v1/chat/completions",
  "model": "deepseek-ai/DeepSeek-V2.5",
  "wait_min": 10,
  "wait_max": 20,
  "screenshot_dir": "./screenshots",
  "browser_width": 550,
  "browser_height": 700,
  "headless": false,
  "auto_submit": true,
  "max_retries": 2,
  "output_dir": "./runs"
}
```

也可以把 API Key 放到环境变量 `WJX_API_KEY` 中。`config.json` 已被 `.gitignore` 忽略，请不要把真实密钥提交到仓库。

## GUI 使用

```bash
python wjx_gui.py
```

GUI 适合手动输入链接、设置 API Key、粘贴二维码并观察日志。

## CLI 使用

自动填写并提交：

```bash
python wjx_cli.py "https://www.wjx.cn/vm/example.aspx" -r "按测试要求生成合理答案"
```

只填写不提交，便于人工检查：

```bash
python wjx_cli.py "https://www.wjx.cn/vm/example.aspx" --no-submit
```

只解析问卷并打印题目结构：

```bash
python wjx_cli.py "https://www.wjx.cn/vm/example.aspx" --dry-run --print-questions
```

无头模式并指定运行报告目录：

```bash
python wjx_cli.py "https://www.wjx.cn/vm/example.aspx" --headless --output runs/test-001
```

## 运行报告

每次运行会生成一个独立目录：

```text
runs/20260503_153000/
├── answers.json
├── config.safe.json
├── page.html
├── questions.json
└── result.png
```

这些文件默认不会提交到 git。

## 测试

```bash
python -m unittest discover -s tests
```

当前测试覆盖配置归一化、AI JSON 解析、题型映射和答案校验。真实网页解析和填写仍建议用你自己创建的测试问卷做人工验收。

## 限制

- 问卷星页面结构变化时，解析选择器可能需要调整。
- 遇到验证码、滑块或安全校验时，需要人工处理。
- 排序题目前只做解析和答案校验，自动拖拽填写仍需后续增强。
- AI 输出质量取决于配置的模型服务和填写要求描述。