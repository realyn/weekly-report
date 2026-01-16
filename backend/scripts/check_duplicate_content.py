#!/usr/bin/env python3
"""
检查数据库中是否存在内容重复的情况（不同人有相同内容）
这通常表示数据解析错误
"""

import os
import re
import sqlite3
from collections import defaultdict

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'weekly_report.db')


def normalize(text):
    """标准化文本用于比较"""
    if not text:
        return ""
    text = re.sub(r'\s+', '', text)
    return text[:150]  # 比较前150字符


def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 获取2025年所有记录
    cursor.execute('''
        SELECT r.week_num, u.real_name, r.this_week_work, r.next_week_plan
        FROM reports r
        JOIN users u ON r.user_id = u.id
        WHERE r.year = 2025
        ORDER BY r.week_num, u.real_name
    ''')

    # 按周组织数据
    weeks = defaultdict(dict)
    for row in cursor.fetchall():
        week_num, name, this_week, next_week = row
        weeks[week_num][name] = {
            'this_week_work': this_week,
            'next_week_plan': next_week
        }

    conn.close()

    print("检查2025年周报数据重复情况")
    print("=" * 70)

    issues = []

    for week_num in sorted(weeks.keys()):
        week_data = weeks[week_num]
        members = list(week_data.keys())

        # 检查 this_week_work 重复
        for i, m1 in enumerate(members):
            for m2 in members[i+1:]:
                t1 = normalize(week_data[m1]['this_week_work'])
                t2 = normalize(week_data[m2]['this_week_work'])
                if t1 and t2 and t1 == t2:
                    issues.append({
                        'week': week_num,
                        'field': 'this_week_work',
                        'members': f'{m1} = {m2}',
                        'preview': t1[:60]
                    })

        # 检查 next_week_plan 重复
        for i, m1 in enumerate(members):
            for m2 in members[i+1:]:
                t1 = normalize(week_data[m1]['next_week_plan'])
                t2 = normalize(week_data[m2]['next_week_plan'])
                if t1 and t2 and t1 == t2:
                    issues.append({
                        'week': week_num,
                        'field': 'next_week_plan',
                        'members': f'{m1} = {m2}',
                        'preview': t1[:60]
                    })

    if issues:
        print(f"\n发现 {len(issues)} 处内容重复:\n")
        for issue in issues:
            print(f"Week {issue['week']:2d} | {issue['field']:15s} | {issue['members']}")
            print(f"         内容: {issue['preview']}...")
            print()
    else:
        print("\n✓ 未发现内容重复")

    # 检查空值
    print("\n" + "=" * 70)
    print("检查空值情况")
    print("=" * 70)

    empty_count = defaultdict(lambda: {'this_week_work': 0, 'next_week_plan': 0})
    for week_num, week_data in weeks.items():
        for name, data in week_data.items():
            if not data['this_week_work']:
                empty_count[name]['this_week_work'] += 1
            if not data['next_week_plan']:
                empty_count[name]['next_week_plan'] += 1

    print("\n各成员空值统计:")
    for name in sorted(empty_count.keys()):
        counts = empty_count[name]
        if counts['this_week_work'] > 0 or counts['next_week_plan'] > 0:
            print(f"  {name}: this_week_work空{counts['this_week_work']}次, next_week_plan空{counts['next_week_plan']}次")

    return issues


if __name__ == '__main__':
    main()
