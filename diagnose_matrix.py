"""
诊断脚本：检查问卷星矩阵题（第7、8题）的 DOM 结构
"""
import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By

driver = webdriver.Chrome()
driver.set_window_size(1200, 900)

try:
    print("访问问卷...")
    driver.get("https://v.wjx.cn/vm/QxFVfde.aspx")
    time.sleep(3)

    # 点击开始作答
    try:
        btn = driver.find_element(By.XPATH, "//*[contains(text(), '开始作答')]")
        btn.click()
        time.sleep(3)
        print("已点击开始作答")
    except Exception as e:
        print(f"点击失败: {e}")

    # 等待题目加载
    time.sleep(2)

    results = {}

    for qid in ["7", "8"]:
        print(f"\n=== 检查题目 {qid} ===")
        q_result = {}

        # 1. 检查 div{qid} 是否存在
        try:
            div_q = driver.find_element(By.CSS_SELECTOR, f"#div{qid}")
            q_result["div_exists"] = True
            q_result["div_type"] = div_q.get_attribute("type")
            q_result["div_topic"] = div_q.get_attribute("topic")
            print(f"  div{qid} 存在, type={q_result['div_type']}, topic={q_result['div_topic']}")
        except Exception as e:
            q_result["div_exists"] = False
            print(f"  div{qid} 不存在: {e}")
            results[f"q{qid}"] = q_result
            continue

        # 2. 检查 divRefTab{qid} 是否存在
        try:
            ref_tab = driver.find_element(By.CSS_SELECTOR, f"#divRefTab{qid}")
            q_result["divRefTab_exists"] = True
            rows = ref_tab.find_elements(By.TAG_NAME, "tr")
            q_result["divRefTab_row_count"] = len(rows)
            print(f"  divRefTab{qid} 存在, {len(rows)} 行")
            for row in rows:
                row_id = row.get_attribute("id")
                rowindex = row.get_attribute("rowindex")
                first_cell = row.find_elements(By.TAG_NAME, "td")[0].text.strip()[:20] if row.find_elements(By.TAG_NAME, "td") else ""
                print(f"    tr: id={row_id}, rowindex={rowindex}, first_cell={first_cell}")
        except Exception as e:
            q_result["divRefTab_exists"] = False
            print(f"  divRefTab{qid} 不存在: {e}")

        # 3. 检查 #drv{qid}_1 是否存在
        try:
            drv_row1 = driver.find_element(By.CSS_SELECTOR, f"#drv{qid}_1")
            q_result["drv1_exists"] = True
            q_result["drv1_rowindex"] = drv_row1.get_attribute("rowindex")
            q_result["drv1_id"] = drv_row1.get_attribute("id")
            print(f"  #drv{qid}_1 存在, rowindex={q_result['drv1_rowindex']}")
        except Exception as e:
            q_result["drv1_exists"] = False
            print(f"  #drv{qid}_1 不存在: {e}")

        # 4. 检查 div{qid} 内的所有 table
        try:
            tables = div_q.find_elements(By.TAG_NAME, "table")
            q_result["table_count_in_div"] = len(tables)
            print(f"  div{qid} 内有 {len(tables)} 个 table:")
            for i, t in enumerate(tables):
                t_id = t.get_attribute("id") or "(no id)"
                t_rows = t.find_elements(By.TAG_NAME, "tr")
                print(f"    table[{i}]: id={t_id}, {len(t_rows)} rows")
                for row in t_rows[:3]:  # 只显示前3行
                    row_id = row.get_attribute("id")
                    rowindex = row.get_attribute("rowindex")
                    first_cell = row.find_elements(By.TAG_NAME, "td")[0].text.strip()[:20] if row.find_elements(By.TAG_NAME, "td") else ""
                    print(f"      tr: id={row_id}, rowindex={rowindex}, first_cell={first_cell}")
        except Exception as e:
            print(f"  检查 div{qid} 内的 table 失败: {e}")

        # 5. 列出所有包含 drv{qid} 的元素 ID
        try:
            all_drv = driver.find_elements(By.CSS_SELECTOR, f"[id*='drv{qid}']")
            q_result["drv_elements_count"] = len(all_drv)
            q_result["drv_ids"] = [el.get_attribute("id") for el in all_drv[:10]]
            print(f"  所有包含 drv{qid} 的元素 ({len(all_drv)} 个): {q_result['drv_ids']}")
        except Exception as e:
            print(f"  检查 drv 元素失败: {e}")

        results[f"q{qid}"] = q_result

    # 6. 列出页面上所有 table 的 ID
    all_tables = driver.find_elements(By.TAG_NAME, "table")
    print(f"\n页面共有 {len(all_tables)} 个 table:")
    for t in all_tables:
        t_id = t.get_attribute("id") or "(no id)"
        t_rows = t.find_elements(By.TAG_NAME, "tr")
        print(f"  table: id={t_id}, {len(t_rows)} rows")

    # 保存结果
    with open("dom_diagnostic.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("\n诊断结果已保存到 dom_diagnostic.json")

finally:
    input("按回车退出...")
    driver.quit()
