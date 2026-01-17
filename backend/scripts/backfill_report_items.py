"""
补录历史周报的 report_items 数据

将 2025 年的周报内容通过 LLM 解析，填充 project_name 等结构化字段
"""
import asyncio
import sys
from pathlib import Path

# 强制 unbuffered 输出
sys.stdout.reconfigure(line_buffering=True)

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import async_session
from app.models.report import Report, ReportItem, ItemType, ReportStatus
from app.models.user import User
from app.services.report_parser_service import ReportParserService
import time


async def get_reports_without_items(db: AsyncSession, year: int) -> list:
    """获取没有 report_items 的周报"""
    # 子查询：已有 items 的 report_id
    subquery = select(ReportItem.report_id).distinct()

    result = await db.execute(
        select(Report, User)
        .join(User)
        .where(
            Report.year == year,
            Report.status == ReportStatus.submitted,
            ~Report.id.in_(subquery)
        )
        .order_by(Report.week_num, User.real_name)
    )
    return result.all()


async def save_parsed_items(db: AsyncSession, report_id: int, parse_result):
    """保存解析结果到 report_items 表（parse_result 是 ParseResult Pydantic 对象）"""
    count = 0

    # 保存本周工作
    for i, item in enumerate(parse_result.this_week_items or []):
        report_item = ReportItem(
            report_id=report_id,
            item_type=ItemType.this_week,
            project_name=item.project_name,
            content=item.content or "",
            sequence=i
        )
        db.add(report_item)
        count += 1

    # 保存下周计划
    for i, item in enumerate(parse_result.next_week_items or []):
        report_item = ReportItem(
            report_id=report_id,
            item_type=ItemType.next_week,
            project_name=item.project_name,
            content=item.content or "",
            sequence=i
        )
        db.add(report_item)
        count += 1

    await db.commit()
    return count


async def backfill_year(year: int, dry_run: bool = False, provider: str = "deepseek"):
    """补录指定年份的数据"""
    parser = ReportParserService()
    parser.llm.provider = provider  # 使用指定的 LLM 提供商
    print(f"🤖 LLM 提供商: {provider}")

    async with async_session() as db:
        reports = await get_reports_without_items(db, year)
        total = len(reports)

        if total == 0:
            print(f"✅ {year}年没有需要补录的周报")
            return

        print(f"📋 {year}年共有 {total} 条周报需要补录")

        if dry_run:
            print("🔍 Dry run 模式，仅显示待处理数据：")
            for report, user in reports[:10]:
                print(f"   - 第{report.week_num}周 {user.real_name}")
            if total > 10:
                print(f"   ... 还有 {total - 10} 条")
            return

        success = 0
        failed = 0
        total_items = 0

        for i, (report, user) in enumerate(reports):
            try:
                print(f"[{i+1}/{total}] 处理: 第{report.week_num}周 {user.real_name}...", end=" ", flush=True)

                # 调用 LLM 解析
                parse_result = await parser.parse_report_text(
                    report.this_week_work or "",
                    report.next_week_plan or ""
                )

                # 保存结果
                items_count = await save_parsed_items(db, report.id, parse_result)
                total_items += items_count
                success += 1

                print(f"✅ {items_count} 条")

                # 限速：避免 API 请求过快
                if i < total - 1:
                    await asyncio.sleep(0.5)

            except Exception as e:
                failed += 1
                print(f"❌ 失败: {e}")

        print(f"\n{'='*50}")
        print(f"📊 补录完成统计:")
        print(f"   成功: {success}/{total}")
        print(f"   失败: {failed}/{total}")
        print(f"   新增 items: {total_items}")


async def main():
    import argparse

    arg_parser = argparse.ArgumentParser(description="补录历史周报的 report_items 数据")
    arg_parser.add_argument("--year", type=int, default=2025, help="要补录的年份 (默认 2025)")
    arg_parser.add_argument("--dry-run", action="store_true", help="仅显示待处理数据，不实际执行")
    arg_parser.add_argument("--provider", type=str, default="deepseek",
                          choices=["deepseek", "dashscope", "qwen"],
                          help="LLM 提供商 (默认 deepseek)")

    args = arg_parser.parse_args()

    print(f"{'='*50}")
    print(f"📦 周报 report_items 数据补录工具")
    print(f"{'='*50}")
    print(f"目标年份: {args.year}")
    print(f"模式: {'Dry Run' if args.dry_run else '实际执行'}")
    print()

    await backfill_year(args.year, dry_run=args.dry_run, provider=args.provider)


if __name__ == "__main__":
    asyncio.run(main())
