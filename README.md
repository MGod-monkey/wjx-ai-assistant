# WJX AI Assistant

WJX AI Assistant 是一个面向问卷星页面的本地辅助工具。它会解析问卷题目，调用兼容 OpenAI Chat Completions 格式的 API 生成答案，并通过 Selenium 在浏览器中完成填写。

请只在自己创建的问卷、内部测试问卷或已获得授权的场景中使用。本项目不会也不应被用于刷量、作弊、绕过平台风控或提交未经授权的数据。

## 功能

- 解析问卷星常见题型：填空、单选、多选、量表、矩阵、下拉等。
- 支持 GUI 和命令行两种入口。
- 支持从剪贴板二维码识别问卷链接。
- 支持自定义 API 地址、模型、等待时间、浏览器尺寸和截图目录。
- 自动保存运行截图和生成答案，便于复盘测试结果。

## 文件结构

```text
.
├── wjx_core.py          # 核心解析、AI 调用、填写和提交逻辑
├── wjx_gui.py           # Tkinter 图形界面入口
├── wjx_cli.py           # 命令行入口
├── config.example.json  # 配置示例，不包含密钥
├── requirements.txt     # Python 依赖
├── .gitignore
└── LICENSE
```

旧版单文件脚本、调试脚本、诊断 JSON 和运行截图已经移除或加入忽略规则。

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
  "browser_height": 700
}
```

`config.json` 已被 `.gitignore` 忽略，请不要把真实密钥提交到仓库。

## 使用

启动图形界面：

```bash
python wjx_gui.py
```

命令行运行：

```bash
python wjx_cli.py "https://www.wjx.cn/vm/example.aspx" -r "按测试要求生成合理答案"
```

无头模式：

```bash
python wjx_cli.py "https://www.wjx.cn/vm/example.aspx" --headless --no-wait
```

## 注意事项

- 问卷星页面结构变化时，解析选择器可能需要调整。
- 遇到验证码、滑块或平台安全校验时，请手动处理或停止任务。
- 生成内容来自配置的模型服务，请自行确认输出是否符合测试需求。