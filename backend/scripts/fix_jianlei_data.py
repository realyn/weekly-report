#!/usr/bin/env python3
"""
修复翦磊2025年周报数据缺失
问题：next_week_plan 大量缺失
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


def extract_jianlei_from_word(doc_path):
    """从Word文档精确提取翦磊的数据"""
    doc = Document(doc_path)
    result = {'this_week_work': None, 'next_week_plan': None}

    for table in doc.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells]

            # 查找翦磊所在位置
            for ci, cell_text in enumerate(cells):
                if cell_text == '翦磊':
                    # 检查是本周工作行还是下周计划行
                    row_text = ' '.join(cells)

                    if '下    周' in row_text or '下周' in row_text:
                        # 下周计划行：翦磊前面的单元格是计划内容
                        for j in range(ci - 1, -1, -1):
                            content = cells[j]
                            if content and len(content) > 20 and '翦磊' not in content:
                                # 检查是否是工作内容（以数字开头或较长文本）
                                if re.match(r'^[1-9][\\.、]', content) or len(content) > 30:
                                    result['next_week_plan'] = content
                                    break
                    else:
                        # 本周工作行
                        for j in range(ci - 1, -1, -1):
                            content = cells[j]
                            if content and len(content) > 20 and '翦磊' not in content:
                                if re.match(r'^[1-9][\\.、]', content) or len(content) > 30:
                                    result['this_week_work'] = content
                                    break

    return result


def get_db_record(week_num):
    """获取数据库中翦磊的记录"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT r.id, r.this_week_work, r.next_week_plan
        FROM reports r
        JOIN users u ON r.user_id = u.id
        WHERE r.year = 2025 AND r.week_num = ? AND u.real_name = '翦磊'
    ''', (week_num,))

    row = cursor.fetchone()
    conn.close()

    if row:
        return {'id': row[0], 'this_week_work': row[1], 'next_week_plan': row[2]}
    return None


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

        # 检查是否有缺失
        has_missing = (not db_record['this_week_work']) or (not db_record['next_week_plan'])
        if not has_missing:
            continue

        # 从Word提取数据
        doc_path = os.path.join(WORD_DIR, filename)
        word_data = extract_jianlei_from_word(doc_path)

        # 检查并修复 this_week_work
        if not db_record['this_week_work'] and word_data['this_week_work']:
            fixes.append({
                'week': week_num,
                'id': db_record['id'],
                'field': 'this_week_work',
                'value': word_data['this_week_work']
            })
            print(f"\nWeek {week_num} - this_week_work 缺失")
            print(f"  Word: {word_data['this_week_work'][:60]}...")

        # 检查并修复 next_week_plan
        if not db_record['next_week_plan'] and word_data['next_week_plan']:
            fixes.append({
                'week': week_num,
                'id': db_record['id'],
                'field': 'next_week_plan',
                'value': word_data['next_week_plan']
            })
            print(f"\nWeek {week_num} - next_week_plan 缺失")
            print(f"  Word: {word_data['next_week_plan'][:60]}...")

    print("\n" + "=" * 60)
    print(f"共发现 {len(fixes)} 处需要修复")

    if fixes and not dry_run:
        for fix in fixes:
            apply_fix(fix['id'], fix['field'], fix['value'], dry_run=False)
            print(f"已修复: Week {fix['week']} - {fix['field']}")
        print(f"\n修复完成")
    elif dry_run:
        print("\n使用 --apply 参数执行实际修复")


if __name__ == '__main__':
    main()
