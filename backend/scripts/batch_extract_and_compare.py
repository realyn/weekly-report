#!/usr/bin/env python3
"""
批量提取周报图片数据并与数据库对比
使用方法：手动填充提取的数据，然后运行比较
"""

import os
import sqlite3
import json
from difflib import SequenceMatcher

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, 'data', 'weekly_report.db')
RAW_DATA_FILE = os.path.join(BASE_DIR, 'data', 'extracted_raw_data.json')
DATE_MAPPING_FILE = os.path.join(BASE_DIR, 'data', 'date_mapping.json')
OUTPUT_SQL_FILE = os.path.join(BASE_DIR, 'data', 'fix_reports.sql')

TEAM_MEMBERS = ['杨宁', '翦磊', '朱迪', '张士健', '程志强', '闻世坤', '秦闪闪', '蒋奇朴']


def load_date_mapping():
    """加载日期映射"""
    with open(DATE_MAPPING_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def date_to_iso_week(date_str):
    """将日期转换为ISO周次"""
    from datetime import datetime
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    return dt.isocalendar()[1]


def load_extracted_data():
    """加载提取的原始数据"""
    with open(RAW_DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_db_data():
    """获取数据库中2025年所有数据"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT r.week_num, u.real_name, r.this_week_work, r.next_week_plan, r.id
        FROM reports r
        JOIN users u ON r.user_id = u.id
        WHERE r.year = 2025
        ORDER BY r.week_num, u.real_name
    ''')

    data = {}
    for row in cursor.fetchall():
        week_num, name, this_week, next_week, report_id = row
        if week_num not in data:
            data[week_num] = {}
        data[week_num][name] = {
            'this_week_work': this_week or '',
            'next_week_plan': next_week or '',
            'report_id': report_id
        }

    conn.close()
    return data


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
    return SequenceMatcher(None, n1[:300], n2[:300]).ratio()


def compare_all():
    """对比所有数据"""
    extracted = load_extracted_data()
    db_data = get_db_data()
    date_mapping = load_date_mapping()

    issues = []
    stats = {'total_checked': 0, 'issues_found': 0, 'missing_in_db': 0}

    for date_str, week_data in extracted.get('data', {}).items():
        # 计算ISO周次
        week_num = date_to_iso_week(date_str)
        folder = week_data.get('folder', '')

        db_week = db_data.get(week_num, {})

        for member in TEAM_MEMBERS:
            member_data = week_data.get(member, {})
            db_member = db_week.get(member, {})

            for field in ['this_week_work', 'next_week_plan']:
                extracted_val = member_data.get(field, '')
                db_val = db_member.get(field, '')

                if not extracted_val:
                    continue

                stats['total_checked'] += 1
                sim = similarity(extracted_val, db_val)

                if sim < 0.85:  # 相似度低于85%
                    stats['issues_found'] += 1
                    issues.append({
                        'date': date_str,
                        'folder': folder,
                        'week_num': week_num,
                        'member': member,
                        'field': field,
                        'similarity': sim,
                        'db_value': db_val[:100] if db_val else '【空】',
                        'extracted_value': extracted_val[:100],
                        'full_extracted': extracted_val,
                        'report_id': db_member.get('report_id')
                    })

    return issues, stats


def generate_fix_sql(issues):
    """生成修复SQL"""
    sqls = []
    for issue in issues:
        if issue['report_id']:
            escaped_val = issue['full_extracted'].replace("'", "''")
            sql = f"""-- {issue['date']} (Week {issue['week_num']}) {issue['member']} {issue['field']} (相似度: {issue['similarity']:.2f})
UPDATE reports SET {issue['field']} = '{escaped_val}'
WHERE id = {issue['report_id']};"""
            sqls.append(sql)
        else:
            sqls.append(f"-- 警告: {issue['date']} {issue['member']} 在数据库中未找到记录")
    return sqls


def main():
    import argparse
    parser = argparse.ArgumentParser(description='批量对比周报数据')
    parser.add_argument('--compare', action='store_true', help='执行对比')
    parser.add_argument('--generate-sql', action='store_true', help='生成修复SQL')
    parser.add_argument('--show-stats', action='store_true', help='显示统计信息')
    parser.add_argument('--week', type=int, help='只处理指定周')
    parser.add_argument('--member', help='只处理指定成员')
    args = parser.parse_args()

    if args.compare or args.generate_sql or args.show_stats:
        issues, stats = compare_all()

        if args.week:
            issues = [i for i in issues if i['week_num'] == args.week]
        if args.member:
            issues = [i for i in issues if i['member'] == args.member]

        if args.show_stats:
            print(f"\n统计信息:")
            print(f"  检查字段数: {stats['total_checked']}")
            print(f"  发现差异数: {stats['issues_found']}")
            print(f"  差异率: {stats['issues_found']/max(stats['total_checked'],1)*100:.1f}%")

        if args.compare:
            if issues:
                print(f"\n发现 {len(issues)} 处差异:\n")
                for issue in issues[:20]:  # 只显示前20个
                    print(f"[{issue['date']}] Week {issue['week_num']} | {issue['member']} | {issue['field']}")
                    print(f"  相似度: {issue['similarity']:.2f}")
                    print(f"  数据库: {issue['db_value']}...")
                    print(f"  提取值: {issue['extracted_value']}...")
                    print()
                if len(issues) > 20:
                    print(f"... 还有 {len(issues)-20} 处差异未显示")
            else:
                print("未发现差异")

        if args.generate_sql:
            sqls = generate_fix_sql(issues)
            with open(OUTPUT_SQL_FILE, 'w', encoding='utf-8') as f:
                f.write('\n\n'.join(sqls))
            print(f"\nSQL已保存到: {OUTPUT_SQL_FILE}")
            print(f"共 {len(sqls)} 条SQL语句")
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
