#!/usr/bin/env python3
"""
从 Word 文档导入周报数据

用法:
    python scripts/import_data.py /path/to/docx/files/

该脚本会:
1. 解析 Word 文档中的周报表格
2. 创建用户账号（如不存在）
3. 导入周报数据
"""

import asyncio
import re
import sys
import os
from pathlib import Path
from datetime import datetime
from docx import Document

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.database import init_db, async_session
from app.models.user import User, UserRole
from app.models.report import Report, ReportStatus
from app.utils.security import get_password_hash


# 员工信息配置
EMPLOYEES = {
    '杨宁': {'department': '产品研发部'},
    '翦磊': {'department': '产品研发部'},
    '朱迪': {'department': '产品研发部'},
    '张士健': {'department': '产品研发部'},
    '程志强': {'department': '产品研发部'},
    '闻世坤': {'department': '产品研发部'},
    '秦闪闪': {'department': '产品研发部'},
    '蒋奇朴': {'department': '产品研发部'},
    '潘六林': {'department': '产品研发部'},
}

# 默认用户密码
DEFAULT_PASSWORD = "Weekly@2026"


def parse_weekly_report(filepath: str) -> dict:
    """解析周报 Word 文档"""
    doc = Document(filepath)

    if not doc.tables:
        raise ValueError(f"文档 {filepath} 中没有找到表格")

    table = doc.tables[0]

    # 提取日期和周次
    header_text = ""
    for row in table.rows[:3]:
        for cell in row.cells:
            text = cell.text.strip()
            if "周工作周报" in text:
                header_text = text
                break
        if header_text:
            break

    # 解析日期
    date_match = re.search(r'(\d{4})年(\d{2})月(\d{2})日', header_text)
    week_match = re.search(r'第(\d+)周', header_text)

    if not date_match:
        raise ValueError(f"无法从 {filepath} 中解析日期")

    year, month, day = date_match.groups()
    report_date = datetime.strptime(f"{year}-{month}-{day}", "%Y-%m-%d").date()
    week_number = int(week_match.group(1)) if week_match else 1

    # 提取所有单元格内容
    all_cells = []
    for row in table.rows:
        for cell in row.cells:
            text = cell.text.strip()
            if text:
                all_cells.append(text)

    # 去重并保持顺序
    seen = set()
    unique_cells = []
    for cell in all_cells:
        if cell not in seen:
            seen.add(cell)
            unique_cells.append(cell)

    # 解析每个人的工作内容
    work_items = {}
    employee_names = list(EMPLOYEES.keys())

    # 查找模式：员工名 -> 完成状态 -> 工作内容
    for i, cell in enumerate(unique_cells):
        if cell in employee_names:
            # 找到员工名，向前查找工作内容
            for j in range(max(0, i-5), i):
                prev_cell = unique_cells[j]
                # 检查是否是工作内容（以数字开头的列表）
                if prev_cell and prev_cell[0].isdigit() and '.' in prev_cell[:3]:
                    if cell not in work_items:
                        work_items[cell] = {'this_week': [], 'next_week': []}

                    # 判断是本周还是下周
                    # 通过检查之前是否出现过"下周"关键词
                    context = ' '.join(unique_cells[max(0, j-3):j])
                    if '下' in context and '周' in context:
                        work_items[cell]['next_week'].append(prev_cell)
                    else:
                        work_items[cell]['this_week'].append(prev_cell)

    return {
        'date': report_date,
        'week': week_number,
        'year': int(year),
        'items': work_items
    }


async def import_data(docx_dir: str):
    """导入数据到数据库"""
    await init_db()

    # 查找所有 docx 文件
    docx_files = list(Path(docx_dir).glob("*.docx"))
    if not docx_files:
        print(f"在 {docx_dir} 中没有找到 .docx 文件")
        return

    print(f"找到 {len(docx_files)} 个文档")

    async with async_session() as db:
        # 1. 创建用户
        print("\n=== 创建用户 ===")
        users = {}
        for name, info in EMPLOYEES.items():
            result = await db.execute(select(User).where(User.real_name == name))
            user = result.scalar_one_or_none()

            if not user:
                # 生成用户名（拼音首字母）
                username = name.lower().replace(' ', '')
                # 检查用户名是否存在
                result = await db.execute(select(User).where(User.username == username))
                if result.scalar_one_or_none():
                    username = f"{username}_{len(users)}"

                user = User(
                    username=username,
                    password=get_password_hash(DEFAULT_PASSWORD),
                    real_name=name,
                    department=info['department'],
                    role=UserRole.user
                )
                db.add(user)
                print(f"  创建用户: {name} ({username})")
            else:
                print(f"  用户已存在: {name}")

            users[name] = user

        await db.commit()

        # 刷新用户对象以获取 ID
        for name in users:
            await db.refresh(users[name])

        # 2. 导入周报数据
        print("\n=== 导入周报 ===")
        for docx_file in sorted(docx_files):
            print(f"\n处理: {docx_file.name}")
            try:
                data = parse_weekly_report(str(docx_file))
                print(f"  日期: {data['date']}, 第{data['week']}周")

                for name, work in data['items'].items():
                    if name not in users:
                        continue

                    user = users[name]

                    # 检查是否已存在
                    result = await db.execute(
                        select(Report).where(
                            Report.user_id == user.id,
                            Report.year == data['year'],
                            Report.week_num == data['week']
                        )
                    )
                    existing = result.scalar_one_or_none()

                    if existing:
                        print(f"  {name}: 周报已存在，跳过")
                        continue

                    this_week = '\n'.join(work.get('this_week', []))
                    next_week = '\n'.join(work.get('next_week', []))

                    if this_week or next_week:
                        report = Report(
                            user_id=user.id,
                            year=data['year'],
                            week_num=data['week'],
                            this_week_work=this_week or "无",
                            next_week_plan=next_week or "待定",
                            status=ReportStatus.submitted
                        )
                        db.add(report)
                        print(f"  {name}: 导入成功")

                await db.commit()

            except Exception as e:
                print(f"  解析错误: {e}")
                continue

    print("\n=== 导入完成 ===")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python scripts/import_data.py /path/to/docx/files/")
        sys.exit(1)

    docx_dir = sys.argv[1]
    if not os.path.isdir(docx_dir):
        print(f"目录不存在: {docx_dir}")
        sys.exit(1)

    asyncio.run(import_data(docx_dir))
