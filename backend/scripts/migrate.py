#!/usr/bin/env python3
"""数据库迁移脚本 - 确保数据库结构与代码中的模型一致"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / 'data' / 'weekly_report.db'

MIGRATIONS = [
    # (表名, 列名, 列定义, 默认值)
    ('users', 'must_change_password', 'BOOLEAN', '1'),
    ('weekly_summary', 'llm_analysis', 'TEXT', None),
    ('weekly_summary', 'analyzed_at', 'DATETIME', None),
]

def get_existing_columns(cursor, table):
    cursor.execute(f'PRAGMA table_info({table})')
    return {row[1] for row in cursor.fetchall()}

def migrate():
    print(f"数据库路径: {DB_PATH}")

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        for table, column, col_type, default in MIGRATIONS:
            if column in get_existing_columns(cursor, table):
                print(f"跳过: {table}.{column} 已存在")
                continue

            default_clause = f" DEFAULT {default}" if default else ""
            sql = f"ALTER TABLE {table} ADD COLUMN {column} {col_type}{default_clause}"
            print(f"执行迁移: {sql}")
            cursor.execute(sql)

        conn.commit()

    print("迁移完成!")

if __name__ == '__main__':
    migrate()
