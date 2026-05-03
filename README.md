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

### 安装 Chrome 与 ChromeDriver

本项目通过 Selenium 控制 Chrome 浏览器填写页面，因此电脑上需要能正常打开 Chrome。

1. 安装 Chrome
   - 访问 [Google Chrome 下载页](https://www.google.com/chrome/) 安装稳定版 Chrome。
   - 安装完成后打开 Chrome，在地址栏输入 `chrome://version`，记下主版本号，例如 `147.0.7727.102` 的主版本号是 `147`。

2. 优先使用 Selenium 4 自动管理驱动
   - 本项目使用 Selenium 4。Selenium 自带的 Selenium Manager 会在启动浏览器时自动查找 Chrome 版本、下载匹配的 ChromeDriver 并缓存到本机。
   - 正常情况下，你不需要手动下载 ChromeDriver；安装依赖后直接运行 `python wjx_gui.py` 或 `python wjx_cli.py ...` 即可。

3. 自动驱动不可用时手动安装 ChromeDriver
   - 如果启动时报 `Unable to obtain driver for chrome`、`chromedriver not found`、`SessionNotCreatedException` 或提示 ChromeDriver 与 Chrome 版本不匹配，就需要手动处理驱动。
   - Chrome 115 及以上版本：打开 [Chrome for Testing 下载面板](https://googlechromelabs.github.io/chrome-for-testing/)，找到与你 Chrome 主版本号一致的 Stable 版本，下载 `chromedriver-win64.zip`。
   - Chrome 114 及以下版本：打开 [ChromeDriver 下载说明](https://developer.chrome.com/docs/chromedriver/downloads)，选择对应版本的 ChromeDriver。
   - 解压后把 `chromedriver.exe` 放到一个固定目录，例如 `C:\Tools\chromedriver\chromedriver.exe`。
   - 将 `C:\Tools\chromedriver` 加入系统 `Path` 环境变量：Windows 搜索“编辑系统环境变量” -> “环境变量” -> 在用户变量或系统变量中编辑 `Path` -> 新增该目录 -> 确定。
   - 重新打开 PowerShell，执行 `chromedriver --version`。能看到版本号就说明驱动已被系统识别。

4. 版本不匹配时怎么处理
   - 最稳妥的方式是更新 Chrome 到最新版，然后重新运行程序，让 Selenium Manager 自动管理。
   - 如果必须手动驱动，请保证 Chrome 和 ChromeDriver 的主版本号一致，例如 Chrome `147.x` 对应 ChromeDriver `147.x`。

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
  "model": "deepseek-ai/DeepSeek-V3",
  "model_fallbacks": ["Qwen/Qwen2-7B-Instruct"],
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

也可以把 API Key 放到环境变量 `WJX_API_KEY` 中。`model_fallbacks` 会在主模型被禁用时自动尝试备用模型；如果服务商模型列表变化，请在 SiliconFlow 控制台或 `/v1/models` 接口确认当前账号可用模型。`config.json` 已被 `.gitignore` 忽略，请不要把真实密钥提交到仓库。

### 申请 SiliconFlow API Key

本项目默认使用硅基流动的 OpenAI 兼容接口，申请 Key 后填入 GUI 或 `config.json` 即可使用。

1. 注册并登录
   - 打开 [SiliconFlow 控制台](https://cloud.siliconflow.cn/)。
   - 按页面提示注册或登录账号。平台支持手机号、邮箱，以及 GitHub / Google 等登录方式。

2. 创建 API Key
   - 登录后进入 [API 密钥页面](https://cloud.siliconflow.cn/account/ak)。
   - 点击“新建 API 密钥”或“Create API Key”。
   - 创建后立即复制并妥善保存。密钥只应保存在本机配置或环境变量中，不要提交到 GitHub。

3. 确认可用模型
   - 打开 [模型广场](https://cloud.siliconflow.cn/models) 查看当前账号可用模型、价格和限速。
   - README 示例使用 `deepseek-ai/DeepSeek-V3`，备用模型示例为 `Qwen/Qwen2-7B-Instruct`。如果运行时报 `Model disabled`，说明该模型对当前账号不可用或已下线，需要在模型广场换成可用的模型名称。

4. 写入项目配置
   - GUI：运行 `python wjx_gui.py`，在设置区域填写 API Key、API 地址和模型名称，然后保存配置。
   - 配置文件：复制 `config.example.json` 为 `config.json`，把 `api_key` 改成你的密钥。
   - 环境变量：不想把密钥写入文件时，可以在 PowerShell 临时设置：

```powershell
$env:WJX_API_KEY="sk-你的密钥"
python wjx_gui.py
```

如需长期保存到当前 Windows 用户环境变量：

```powershell
setx WJX_API_KEY "sk-你的密钥"
```

设置完成后重新打开 PowerShell，再运行程序。

5. 测试配置
   - 先只解析问卷，确认浏览器和页面解析正常：

```bash
python wjx_cli.py "https://www.wjx.cn/vm/example.aspx" --dry-run --print-questions
```

   - 再执行不提交的完整填写测试，确认 AI 调用和自动填写正常：

```bash
python wjx_cli.py "https://www.wjx.cn/vm/example.aspx" --no-submit
```

### 常见配置问题

- `403 {"code":30003,"message":"Model disabled."}`：当前模型不可用，请到 SiliconFlow 模型广场选择可用模型，并更新 `model` 或 `model_fallbacks`。
- `API 请求失败: 401`：API Key 错误、过期或未正确读取。检查 `config.json`、GUI 设置或 `WJX_API_KEY`。
- `Unable to obtain driver for chrome`：Selenium Manager 未能自动下载驱动，请按上面的 ChromeDriver 手动安装步骤处理。
- `SessionNotCreatedException`：通常是 Chrome 和 ChromeDriver 主版本号不一致，更新 Chrome 或重新下载匹配版本的 ChromeDriver。

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
