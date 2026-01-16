#!/usr/bin/env python3
"""
对比图片提取数据与数据库数据，生成修复SQL
"""

import os
import sqlite3
import json
from difflib import SequenceMatcher

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'weekly_report.db')
DATA_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'extracted_2025_data.json')

TEAM_MEMBERS = ['杨宁', '翦磊', '朱迪', '张士健', '程志强', '闻世坤', '秦闪闪', '蒋奇朴']


def normalize_text(text):
    """标准化文本用于比较"""
    if not text:
        return ""
    import re
    text = re.sub(r'\s+', '', text)
    return text


def similarity(t1, t2):
    """计算相似度"""
    n1 = normalize_text(t1)
    n2 = normalize_text(t2)
    if not n1 and not n2:
        return 1.0
    if not n1 or not n2:
        return 0.0
    return SequenceMatcher(None, n1[:200], n2[:200]).ratio()


def get_db_data():
    """获取数据库中2025年所有数据"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT r.week_num, u.real_name, r.this_week_work, r.next_week_plan
        FROM reports r
        JOIN users u ON r.user_id = u.id
        WHERE r.year = 2025
        ORDER BY r.week_num, u.real_name
    ''')

    data = {}
    for row in cursor.fetchall():
        week_num, name, this_week, next_week = row
        if week_num not in data:
            data[week_num] = {}
        data[week_num][name] = {
            'this_week_work': this_week,
            'next_week_plan': next_week
        }

    conn.close()
    return data


def load_extracted_data():
    """加载从图片提取的数据"""
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get('weeks', {})


def compare_data():
    """对比数据，找出差异"""
    db_data = get_db_data()
    extracted_data = load_extracted_data()

    issues = []

    for week_str, week_data in extracted_data.items():
        week_num = int(week_str)
        db_week = db_data.get(week_num, {})

        for member, content in week_data.items():
            db_member = db_week.get(member, {})

            for field in ['this_week_work', 'next_week_plan']:
                extracted_val = content.get(field)
                db_val = db_member.get(field)

                if not extracted_val:
                    continue

                sim = similarity(extracted_val, db_val)

                if sim < 0.8:  # 相似度低于80%
                    issues.append({
                        'week_num': week_num,
                        'member': member,
                        'field': field,
                        'similarity': sim,
                        'db_value': db_val[:100] if db_val else 'NULL',
                        'extracted_value': extracted_val[:100],
                        'full_extracted': extracted_val
                    })

    return issues


def generate_fix_sql(issues):
    """生成修复SQL"""
    sqls = []
    for issue in issues:
        escaped_val = issue['full_extracted'].replace("'", "''")
        sql = f"""-- Week {issue['week_num']} {issue['member']} {issue['field']} (相似度: {issue['similarity']:.2f})
UPDATE reports SET {issue['field']} = '{escaped_val}'
WHERE id = (
    SELECT r.id FROM reports r
    JOIN users u ON r.user_id = u.id
    WHERE r.year = 2025 AND r.week_num = {issue['week_num']} AND u.real_name = '{issue['member']}'
);"""
        sqls.append(sql)
    return sqls


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--show-db', action='store_true', help='显示数据库数据')
    parser.add_argument('--compare', action='store_true', help='对比数据')
    parser.add_argument('--week', type=int, help='只处理指定周')
    parser.add_argument('--member', help='只处理指定成员')
    parser.add_argument('--output', '-o', help='输出SQL文件')
    args = parser.parse_args()

    if args.show_db:
        db_data = get_db_data()
        for week_num in sorted(db_data.keys()):
            if args.week and week_num != args.week:
                continue
            print(f"\n=== Week {week_num} ===")
            for member, content in sorted(db_data[week_num].items()):
                if args.member and member != args.member:
                    continue
                print(f"\n{member}:")
                print(f"  本周: {(content['this_week_work'] or 'NULL')[:60]}...")
                print(f"  下周: {(content['next_week_plan'] or 'NULL')[:60]}...")

    if args.compare:
        issues = compare_data()
        if args.week:
            issues = [i for i in issues if i['week_num'] == args.week]
        if args.member:
            issues = [i for i in issues if i['member'] == args.member]

        if issues:
            print(f"发现 {len(issues)} 处差异:\n")
            for issue in issues:
                print(f"Week {issue['week_num']} | {issue['member']} | {issue['field']}")
                print(f"  相似度: {issue['similarity']:.2f}")
                print(f"  数据库: {issue['db_value']}...")
                print(f"  提取值: {issue['extracted_value']}...")
                print()

            if args.output:
                sqls = generate_fix_sql(issues)
                with open(args.output, 'w', encoding='utf-8') as f:
                    f.write('\n\n'.join(sqls))
                print(f"SQL已保存到: {args.output}")
        else:
            print("未发现差异")


if __name__ == '__main__':
    main()
