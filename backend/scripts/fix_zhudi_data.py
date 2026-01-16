#!/usr/bin/env python3
"""
修复朱迪2025年周报数据错误
问题：第9、10、12、13周的 next_week_plan 错误地显示为杨宁的内容
"""

import os
import re
import sqlite3
from datetime import datetime
from docx import Document

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'weekly_report.db')
WORD_DIR = '/Users/yn/Documents/工作/工时/2025/'


def get_week_from_filename(filename):
    """从文件名提取周数"""
    match = re.search(r'2025\.(\d{2})\.(\d{2})\.docx', filename)
    if match:
        month, day = int(match.group(1)), int(match.group(2))
        date = datetime(2025, month, day)
        return date.isocalendar()[1]
    return None


def extract_zhudi_from_word(doc_path):
    """从Word文档精确提取朱迪的数据

    Word表格结构：在"下周"行中，朱迪的名字前一个单元格就是朱迪的计划内容
    需要精确提取紧邻的单元格，而不是搜索最长的内容
    """
    doc = Document(doc_path)
    result = {'this_week_work': None, 'next_week_plan': None}

    for table in doc.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells]

            # 查找朱迪所在位置
            for ci, cell_text in enumerate(cells):
                if cell_text == '朱迪':
                    # 检查是本周工作行还是下周计划行
                    row_text = ' '.join(cells)

                    if '下    周' in row_text or '下周' in row_text:
                        # 下周计划行：朱迪前面紧邻的单元格是计划内容
                        # 只取紧邻的前一个非空单元格
                        for j in range(ci - 1, -1, -1):
                            content = cells[j]
                            # 跳过标题行文字和空内容
                            if content and '下' not in content and '内容' not in content and '说明' not in content:
                                # 排除其他人的名字
                                other_names = ['杨宁', '翦磊', '张士健', '程志强', '闻世坤', '秦闪闪', '蒋奇朴']
                                if not any(name in content for name in other_names):
                                    result['next_week_plan'] = content
                                    break
                    else:
                        # 本周工作行
                        for j in range(ci - 1, -1, -1):
                            content = cells[j]
                            if content and len(content) > 10 and '朱迪' not in content:
                                if re.match(r'^[1-9]', content) or '项目' in content or len(content) > 20:
                                    result['this_week_work'] = content
                                    break

    return result


def get_db_record(week_num):
    """获取数据库中朱迪的记录"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT r.id, r.this_week_work, r.next_week_plan
        FROM reports r
        JOIN users u ON r.user_id = u.id
        WHERE r.year = 2025 AND r.week_num = ? AND u.real_name = '朱迪'
    ''', (week_num,))

    row = cursor.fetchone()
    conn.close()

    if row:
        return {'id': row[0], 'this_week_work': row[1], 'next_week_plan': row[2]}
    return None


def get_yangning_next_plan(week_num):
    """获取杨宁该周的下周计划（用于判断是否是错误数据）"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT r.next_week_plan
        FROM reports r
        JOIN users u ON r.user_id = u.id
        WHERE r.year = 2025 AND r.week_num = ? AND u.real_name = '杨宁'
    ''', (week_num,))

    row = cursor.fetchone()
    conn.close()

    return row[0] if row else None


def is_same_content(text1, text2):
    """判断两段内容是否相同（忽略空格差异）"""
    if not text1 or not text2:
        return False
    # 移除空格，统一比较
    t1 = re.sub(r'\s+', '', text1)[:100]
    t2 = re.sub(r'\s+', '', text2)[:100]
    return t1 == t2


def apply_fix(report_id, field, value, dry_run=True):
    """应用修复"""
    if dry_run:
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(f'UPDATE reports SET {field} = ? WHERE id = ?', (value, report_id))
    conn.commit()
    conn.close()


def main():
    import sys
    dry_run = '--apply' not in sys.argv

    print(f"运行模式: {'DRY RUN' if dry_run else 'APPLY'}")
    print("=" * 60)

    fixes = []

    for filename in sorted(os.listdir(WORD_DIR)):
        if not filename.endswith('.docx') or filename.startswith('~'):
            continue

        week_num = get_week_from_filename(filename)
        if week_num is None:
            continue

        db_record = get_db_record(week_num)
        if not db_record:
            continue

        yangning_plan = get_yangning_next_plan(week_num)

        # 检查朱迪的 next_week_plan 是否与杨宁的相同（说明是错误数据）
        if yangning_plan and is_same_content(db_record['next_week_plan'], yangning_plan):
            # 从Word提取朱迪真正的数据
            doc_path = os.path.join(WORD_DIR, filename)
            word_data = extract_zhudi_from_word(doc_path)

            if word_data['next_week_plan']:
                # 确保提取的数据与杨宁的不同
                if not is_same_content(word_data['next_week_plan'], yangning_plan):
                    fixes.append({
                        'week': week_num,
                        'id': db_record['id'],
                        'field': 'next_week_plan',
                        'old_value': db_record['next_week_plan'][:60] + '...',
                        'new_value': word_data['next_week_plan']
                    })
                    print(f"\nWeek {week_num} - next_week_plan 错误（与杨宁相同）")
                    print(f"  当前: {db_record['next_week_plan'][:60]}...")
                    print(f"  Word: {word_data['next_week_plan'][:60]}...")

    print("\n" + "=" * 60)
    print(f"共发现 {len(fixes)} 处需要修复")

    if fixes and not dry_run:
        for fix in fixes:
            apply_fix(fix['id'], fix['field'], fix['new_value'], dry_run=False)
            print(f"已修复: Week {fix['week']} - {fix['field']}")
        print(f"\n修复完成")
    elif dry_run:
        print("\n使用 --apply 参数执行实际修复")


if __name__ == '__main__':
    main()
