#!/usr/bin/env python3
"""
2025年历史数据修复脚本

问题：
1. 张士健和朱迪的本周工作内容重复（朱迪的内容被错误地替换为张士健的）
2. 部分记录本周工作=下周计划（数据导入时混淆）

修复策略：
1. 从原始Word文档中重新提取正确数据
2. 更新数据库中的错误记录
"""

import os
import re
import sqlite3
from datetime import datetime
from docx import Document

# 配置
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'weekly_report.db')
WORD_DIR = '/Users/yn/Documents/工作/工时/2025/'

# 团队成员
TEAM_MEMBERS = ['杨宁', '翦磊', '朱迪', '张士健', '程志强', '闻世坤', '秦闪闪', '蒋奇朴']


def get_week_from_filename(filename):
    """从文件名提取周数
    格式: 产品研发部工作计划2025.MM.DD.docx
    """
    match = re.search(r'2025\.(\d{2})\.(\d{2})\.docx', filename)
    if match:
        month, day = int(match.group(1)), int(match.group(2))
        date = datetime(2025, month, day)
        return date.isocalendar()[1]
    return None


def extract_from_word(doc_path):
    """从Word文档提取周报数据

    返回: {
        'member_name': {
            'this_week_work': str,
            'next_week_plan': str
        }
    }
    """
    doc = Document(doc_path)

    # 收集所有单元格文本
    cells = []
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                text = cell.text.strip()
                if text:
                    cells.append(text)

    result = {}

    # 根据表格结构，工作内容通常在名字前面
    # 策略：找到名字，往前查找工作内容
    for i, text in enumerate(cells):
        # 查找单独的名字单元格
        for member in TEAM_MEMBERS:
            if text == member or (member in text and len(text) < 15):
                # 往前找工作内容
                for j in range(i-1, max(0, i-10), -1):
                    prev_text = cells[j]
                    # 工作内容特征：以数字开头或长度较长
                    if (re.match(r'^[1-9][\.、]', prev_text) or
                        (len(prev_text) > 30 and member not in prev_text)):
                        # 检查是否是其他人的名字
                        if not any(m in prev_text for m in TEAM_MEMBERS if m != member):
                            if member not in result:
                                result[member] = {'this_week_work': None, 'next_week_plan': None}

                            # 判断是本周还是下周（根据后面的标记）
                            context = ' '.join(cells[max(0, j-5):min(len(cells), j+5)])
                            if '下周' in context or '下    周' in context:
                                if result[member]['next_week_plan'] is None:
                                    result[member]['next_week_plan'] = prev_text
                            else:
                                if result[member]['this_week_work'] is None:
                                    result[member]['this_week_work'] = prev_text
                            break

    return result


def get_database_records(week_num):
    """获取数据库中指定周的记录"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT r.id, u.real_name, r.this_week_work, r.next_week_plan
        FROM reports r
        JOIN users u ON r.user_id = u.id
        WHERE r.year = 2025 AND r.week_num = ? AND r.status = 'submitted'
        ORDER BY u.real_name
    ''', (week_num,))

    rows = cursor.fetchall()
    conn.close()

    return {row[1]: {'id': row[0], 'this_week_work': row[2], 'next_week_plan': row[3]}
            for row in rows}


def normalize_text(text):
    """标准化文本用于比较（忽略格式差异）"""
    if not text:
        return ''
    # 移除空格、统一标点
    text = re.sub(r'[ \t]+', '', text)
    text = text.replace('。', '.').replace('、', '.').replace('，', ',')
    text = re.sub(r'\n+', '\n', text)
    return text.strip()


def is_significant_difference(old_text, new_text):
    """判断是否是有意义的内容差异（不只是格式差异）"""
    old_norm = normalize_text(old_text)
    new_norm = normalize_text(new_text)

    # 如果标准化后的前100字符相同，认为只是格式差异
    if old_norm[:100] == new_norm[:100]:
        return False

    # 如果内容差异超过20%，认为是显著差异
    if len(old_norm) > 0:
        # 简单比较：看共同字符数
        common = sum(1 for c in old_norm[:100] if c in new_norm[:100])
        similarity = common / min(len(old_norm[:100]), len(new_norm[:100])) if old_norm and new_norm else 0
        return similarity < 0.8  # 相似度低于80%才认为是显著差异

    return True


def compare_and_fix(week_num, word_data, db_data, dry_run=True):
    """比较并修复数据差异 - 只修复显著内容差异"""
    fixes = []

    for member, word_content in word_data.items():
        if member not in db_data:
            continue

        db_content = db_data[member]
        report_id = db_content['id']

        # 比较本周工作
        word_this_week = word_content.get('this_week_work', '')
        db_this_week = db_content.get('this_week_work', '')

        if word_this_week and db_this_week:
            # 只修复显著差异
            if is_significant_difference(db_this_week, word_this_week):
                fixes.append({
                    'id': report_id,
                    'member': member,
                    'field': 'this_week_work',
                    'old_value': db_this_week[:80] + '...',
                    'new_value': word_this_week[:80] + '...',
                    'full_new_value': word_this_week
                })

        # 比较下周计划
        word_next_week = word_content.get('next_week_plan', '')
        db_next_week = db_content.get('next_week_plan', '')

        if word_next_week and db_next_week:
            if is_significant_difference(db_next_week, word_next_week):
                fixes.append({
                    'id': report_id,
                    'member': member,
                    'field': 'next_week_plan',
                    'old_value': db_next_week[:80] + '...',
                    'new_value': word_next_week[:80] + '...',
                    'full_new_value': word_next_week
                })

    return fixes


def apply_fixes(fixes, dry_run=True):
    """应用修复"""
    if not fixes:
        print("没有需要修复的数据")
        return

    print(f"\n{'=' * 60}")
    print(f"{'[DRY RUN] ' if dry_run else ''}发现 {len(fixes)} 处需要修复:")
    print('=' * 60)

    for fix in fixes:
        print(f"\n[{fix['member']}] {fix['field']}:")
        print(f"  旧值: {fix['old_value']}")
        print(f"  新值: {fix['new_value']}")

    if dry_run:
        print(f"\n{'=' * 60}")
        print("这是 DRY RUN 模式，未实际修改数据库")
        print("使用 --apply 参数来实际执行修复")
        return

    # 实际修复
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    for fix in fixes:
        cursor.execute(f'''
            UPDATE reports SET {fix['field']} = ? WHERE id = ?
        ''', (fix['full_new_value'], fix['id']))
        print(f"已更新: {fix['member']} 的 {fix['field']}")

    conn.commit()
    conn.close()
    print(f"\n修复完成，共更新 {len(fixes)} 条记录")


def find_affected_weeks():
    """查找受影响的周（有重复内容的周）"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 查找有重复 this_week_work 的周
    cursor.execute('''
        SELECT r.week_num, GROUP_CONCAT(u.real_name), r.this_week_work
        FROM reports r
        JOIN users u ON r.user_id = u.id
        WHERE r.year = 2025 AND r.status = 'submitted'
        GROUP BY r.week_num, r.this_week_work
        HAVING COUNT(*) > 1 AND LENGTH(r.this_week_work) > 10
    ''')

    rows = cursor.fetchall()
    conn.close()

    affected_weeks = set()
    for row in rows:
        week, names, content = row
        print(f"Week {week}: {names} 有重复内容")
        affected_weeks.add(week)

    return sorted(affected_weeks)


def main():
    import sys

    dry_run = '--apply' not in sys.argv

    if dry_run:
        print("运行模式: DRY RUN (不会实际修改数据库)")
        print("添加 --apply 参数来实际执行修复\n")
    else:
        print("运行模式: APPLY (将实际修改数据库)\n")

    # 查找受影响的周
    print("正在查找受影响的周...")
    affected_weeks = find_affected_weeks()

    if not affected_weeks:
        print("没有发现重复数据问题")
        return

    print(f"\n受影响的周: {affected_weeks}")

    # 遍历Word文档，修复受影响的周
    all_fixes = []

    for filename in sorted(os.listdir(WORD_DIR)):
        if not filename.endswith('.docx') or filename.startswith('~'):
            continue

        week_num = get_week_from_filename(filename)
        if week_num is None or week_num not in affected_weeks:
            continue

        print(f"\n处理 Week {week_num}: {filename}")

        doc_path = os.path.join(WORD_DIR, filename)
        word_data = extract_from_word(doc_path)
        db_data = get_database_records(week_num)

        fixes = compare_and_fix(week_num, word_data, db_data, dry_run)
        if fixes:
            for fix in fixes:
                fix['week'] = week_num
            all_fixes.extend(fixes)

    # 应用修复
    apply_fixes(all_fixes, dry_run)


if __name__ == '__main__':
    main()
