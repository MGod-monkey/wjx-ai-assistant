"""Command-line entry point for WJX AI Assistant."""
from __future__ import annotations

import argparse
import sys

from wjx_assistant.config import load_config
from wjx_assistant.runner import parse_only, run_task


def _cli_log(msg: str, add_newline: bool = True, **kwargs):
    if add_newline:
        print(msg)
    else:
        print(msg, end="", flush=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="WJX AI Assistant")
    parser.add_argument("url", nargs="?", help="问卷星链接；不填则交互式输入")
    parser.add_argument("-r", "--requirements", default="", help="填写要求")
    parser.add_argument("--config", default="config.json", help="配置文件路径")
    parser.add_argument("--headless", action="store_true", help="无头模式，不显示浏览器窗口")
    parser.add_argument("--no-wait", action="store_true", help="跳过提交前的随机等待时间")
    parser.add_argument("--no-submit", action="store_true", help="只填写不提交，便于人工检查")
    parser.add_argument("--dry-run", action="store_true", help="只解析问卷，不调用 AI、不填写")
    parser.add_argument("--print-questions", action="store_true", help="打印解析后的题目结构")
    parser.add_argument("--output", default="", help="运行报告输出目录")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    cfg = load_config(args.config)

    if args.no_wait:
        cfg["wait_min"] = 0
        cfg["wait_max"] = 0
    if args.no_submit:
        cfg["auto_submit"] = False
    if args.headless:
        cfg["headless"] = True
    if args.output:
        cfg["output_dir"] = args.output

    print("=" * 60)
    print("WJX AI Assistant")
    print("=" * 60)

    url = args.url or input("请输入问卷星链接: ").strip()
    if not url:
        print("链接不能为空，程序退出。")
        return 1

    if args.dry_run or args.print_questions:
        questions, formatted = parse_only(url, cfg, log_cb=_cli_log)
        if args.print_questions:
            print("\n解析结果:")
            print(formatted)
        print(f"\n共解析到 {len(questions)} 道题。")
        return 0

    requirements = args.requirements
    if not requirements:
        requirements = input(
            "请输入填写要求（例如：第1题选B，年龄选18-25岁，填空题写满意；可留空）: "
        ).strip()
    if not requirements:
        print("未输入填写要求，将使用 AI 自由生成答案。")

    print(f"\n浏览器模式: {'无头' if cfg.get('headless') else '可视化'}")
    print(f"提交模式: {'自动提交' if cfg.get('auto_submit', True) else '只填写不提交'}")

    success = run_task(
        url,
        requirements or "请合理填写问卷",
        cfg,
        log_cb=_cli_log,
        progress_cb=_cli_log,
        headless=bool(cfg.get("headless")),
    )

    if not cfg.get("headless"):
        input("\n按回车键退出...")
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())