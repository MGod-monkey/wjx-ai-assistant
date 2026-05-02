"""
问卷星 AI 填写系统 - 终端版本
调用 wjx_core.py 中的核心逻辑
"""
import argparse
import sys

import wjx_core


def _cli_log(msg: str, add_newline: bool = True, **kwargs):
    if add_newline:
        print(msg)
    else:
        print(msg, end="", flush=True)


def main():
    parser = argparse.ArgumentParser(description="问卷星 AI 自动填写系统")
    parser.add_argument("url", nargs="?", help="问卷星链接（可选，不填则交互式输入）")
    parser.add_argument("-r", "--requirements", default="", help="填写要求")
    parser.add_argument("--headless", action="store_true", help="无头模式，不显示浏览器窗口")
    parser.add_argument("--no-wait", action="store_true", help="跳过提交前的随机等待时间")
    args = parser.parse_args()

    cfg = wjx_core.load_config()

    print("=" * 60)
    print("问卷星 AI 自动填写系统")
    print("=" * 60)

    url = args.url
    if not url:
        url = input("请输入问卷星链接: ").strip()
        if not url:
            print("链接不能为空，程序退出。")
            return

    requirements = args.requirements
    if not requirements:
        requirements = input(
            "请输入填写要求（如：第1题选B，年龄选18-25岁，\n"
            "  填空题写满意，多选题选AC等，多条用逗号分隔）: "
        ).strip()

    if not requirements:
        print("未输入填写要求，将使用 AI 自由生成答案。")

    print(f"\n浏览器模式: {'无头' if args.headless else '可视化'}")
    if args.no_wait:
        cfg["wait_min"] = 0
        cfg["wait_max"] = 0

    success = wjx_core.run_task(
        url,
        requirements or "请合理填写问卷",
        cfg,
        log_cb=_cli_log,
        progress_cb=_cli_log,
        headless=args.headless,
    )

    if not args.headless:
        input("\n按回车键退出...")
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
