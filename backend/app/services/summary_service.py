from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import Optional
import json
from datetime import datetime
from app.models.report import Report
from app.models.user import User
from app.models.summary import WeeklySummary
from app.utils.date_utils import get_week_date_range
from app.services.llm_service import get_project_extractor

# Word 文档中的人员顺序
PERSON_ORDER = ["杨宁", "翦磊", "朱迪", "张士健", "程志强", "闻世坤", "秦闪闪", "蒋奇朴"]


def sort_by_person_order(items: list, name_key: str = "user_name") -> list:
    """按照 Word 文档中的人员顺序排序"""
    def get_order(item):
        # SQLAlchemy Row 对象可以通过索引访问，item[1] 是 User 对象
        try:
            name = item[1].real_name
        except (TypeError, IndexError, AttributeError):
            # 如果是字典类型
            name = item.get(name_key, "") if hasattr(item, 'get') else ""
        try:
            return PERSON_ORDER.index(name)
        except ValueError:
            return len(PERSON_ORDER)  # 不在列表中的排到最后
    return sorted(items, key=get_order)


async def get_weekly_summary(db: AsyncSession, year: int, week_num: int, current_user: Optional[User] = None) -> dict:
    """获取周汇总数据

    Args:
        current_user: 当前用户，如果是管理员可以看到所有人的周报，否则看不到管理员的周报
    """
    # 获取日期范围
    start_date, end_date = get_week_date_range(year, week_num)

    # 判断是否为管理员
    is_admin = current_user and current_user.role == 'admin'

    # 构建查询条件（eager load items）
    query = select(Report, User).join(User).options(
        selectinload(Report.items)
    ).where(
        Report.year == year,
        Report.week_num == week_num,
        Report.status == "submitted"
    )

    # 非管理员用户看不到管理员的周报
    if not is_admin:
        query = query.where(User.role != 'admin')

    result = await db.execute(query)
    reports_with_users = sort_by_person_order(result.all())

    # 统计数据：非管理员查看时，total_members 也不包含管理员
    if is_admin:
        total_members = await db.scalar(select(func.count(User.id)).where(User.is_active == True))
    else:
        total_members = await db.scalar(select(func.count(User.id)).where(User.is_active == True, User.role != 'admin'))
    submitted_count = len(reports_with_users)

    reports_data = []
    total_tasks = 0
    for report, user in reports_with_users:
        # 计算任务数（按换行或数字开头计算）
        task_count = len([l for l in (report.this_week_work or "").split("\n") if l.strip()])
        total_tasks += task_count

        # 构建 items 数据（结构化的工作条目）
        this_week_items = []
        next_week_items = []
        for item in report.items:
            item_data = {
                "id": item.id,
                "project_name": item.project_name,
                "content": item.content
            }
            if item.item_type.value == "this_week":
                this_week_items.append(item_data)
            else:
                next_week_items.append(item_data)

        reports_data.append({
            "user_id": user.id,
            "user_name": user.real_name,
            "department": user.department,
            "this_week_work": report.this_week_work,
            "next_week_plan": report.next_week_plan,
            "task_count": task_count,
            "this_week_items": this_week_items,
            "next_week_items": next_week_items
        })

    return {
        "year": year,
        "week_num": week_num,
        "date_range": f"{start_date} ~ {end_date}",
        "total_members": total_members,
        "submitted_count": submitted_count,
        "submission_rate": round(submitted_count / total_members * 100, 1) if total_members else 0,
        "reports": reports_data,
        "statistics": {
            "total_tasks": total_tasks
        }
    }


def extract_projects_from_text(text: str) -> list:
    """
    从工作内容中提取项目名称（使用 ProjectExtractor 统一逻辑）
    这是降级方案，优先使用 report_items 表中的结构化数据
    """
    extractor = get_project_extractor()
    data = extractor.load_known_projects()

    # 构建别名到标准名的映射
    alias_map = {}
    for proj in data.get("projects", []):
        if proj.get("status") == "archived":
            continue
        std_name = proj["name"]
        alias_map[std_name.lower()] = std_name
        for alias in proj.get("aliases", []):
            alias_map[alias.lower()] = std_name

    # 提取并归一化
    found_projects = set()
    text_lower = text.lower()
    for keyword, std_name in alias_map.items():
        if keyword in text_lower:
            found_projects.add(std_name)

    return list(found_projects)


def categorize_work(text: str) -> str:
    """对工作内容进行分类（关键词方式，作为 LLM 的降级方案）"""
    if any(k in text for k in ["开发", "功能", "新增", "实现", "编写"]):
        return "功能开发"
    elif any(k in text for k in ["维护", "运维", "检查", "巡检"]):
        return "系统维护"
    elif any(k in text for k in ["排查", "修复", "问题", "bug", "修正"]):
        return "问题排查"
    elif any(k in text for k in ["监控", "告警", "报警"]):
        return "运维监控"
    elif any(k in text for k in ["沟通", "会议", "讨论", "确认", "演示"]):
        return "需求沟通"
    else:
        return "其他工作"


async def extract_projects_with_llm(reports_data: list) -> dict:
    """使用 LLM 智能提取项目信息"""
    try:
        extractor = get_project_extractor()
        result = await extractor.extract_batch(reports_data)
        return result
    except Exception as e:
        print(f"LLM 提取失败，使用降级方案: {e}")
        return None


async def trigger_llm_analysis(db: AsyncSession, year: int, week_num: int):
    """触发 LLM 分析并缓存结果（周报提交时调用）"""
    from app.models.report import ReportStatus

    # 查询该周所有已提交的周报
    result = await db.execute(
        select(Report, User)
        .join(User)
        .where(
            Report.year == year,
            Report.week_num == week_num,
            Report.status == ReportStatus.submitted
        )
    )
    reports_with_users = sort_by_person_order(result.all())

    if not reports_with_users:
        return

    # 准备数据
    reports_for_llm = []
    for report, user in reports_with_users:
        reports_for_llm.append({
            "user_name": user.real_name,
            "this_week_work": report.this_week_work or "",
            "next_week_plan": report.next_week_plan or ""
        })

    # 调用 LLM 分析
    llm_result = await extract_projects_with_llm(reports_for_llm)

    if llm_result:
        # 保存到数据库缓存
        existing = await db.execute(
            select(WeeklySummary).where(
                WeeklySummary.year == year,
                WeeklySummary.week_num == week_num
            )
        )
        summary = existing.scalar_one_or_none()

        analysis_json = json.dumps(llm_result, ensure_ascii=False)

        if summary:
            summary.llm_analysis = analysis_json
            summary.analyzed_at = datetime.now()
        else:
            summary = WeeklySummary(
                year=year,
                week_num=week_num,
                llm_analysis=analysis_json,
                analyzed_at=datetime.now()
            )
            db.add(summary)

        await db.commit()
        print(f"LLM 分析完成并缓存: {year}年第{week_num}周")


async def get_cached_llm_analysis(db: AsyncSession, year: int, week_num: int) -> Optional[dict]:
    """获取缓存的 LLM 分析结果"""
    result = await db.execute(
        select(WeeklySummary).where(
            WeeklySummary.year == year,
            WeeklySummary.week_num == week_num
        )
    )
    summary = result.scalar_one_or_none()

    if summary and summary.llm_analysis:
        try:
            return json.loads(summary.llm_analysis)
        except json.JSONDecodeError:
            return None
    return None


async def get_weekly_report_dashboard(db: AsyncSession, year: int, week_num: int, current_user: Optional[User] = None) -> dict:
    """获取单周可视化面板数据

    Args:
        current_user: 当前用户，如果是管理员可以看到所有人的周报，否则看不到管理员的周报
    """
    from app.models.report import ReportStatus, ReportItem, ItemType
    from sqlalchemy.orm import selectinload

    start_date, end_date = get_week_date_range(year, week_num)

    # 判断是否为管理员
    is_admin = current_user and current_user.role == 'admin'

    # 获取活跃用户数
    if is_admin:
        # 管理员看到所有人（不含管理员自己，保持原有逻辑）
        total_members = await db.scalar(
            select(func.count(User.id)).where(User.is_active == True, User.role != 'admin')
        )
    else:
        # 非管理员也看不到管理员
        total_members = await db.scalar(
            select(func.count(User.id)).where(User.is_active == True, User.role != 'admin')
        )

    # 构建查询条件，预加载 items
    query = select(Report, User).join(User).where(
        Report.year == year,
        Report.week_num == week_num,
        Report.status == ReportStatus.submitted
    ).options(selectinload(Report.items))

    # 非管理员用户看不到管理员的周报
    if not is_admin:
        query = query.where(User.role != 'admin')

    result = await db.execute(query)
    reports_with_users = sort_by_person_order(result.all())
    submitted_count = len(reports_with_users)

    # 准备周报数据用于 LLM 分析
    reports_for_llm = []
    member_tasks = []  # 各成员任务分布
    member_details = []  # 团队成员详情
    next_week_plans = []  # 下周计划
    total_tasks = 0

    for report, user in reports_with_users:
        this_week_lines = [l.strip() for l in (report.this_week_work or "").split("\n") if l.strip()]
        next_week_lines = [l.strip() for l in (report.next_week_plan or "").split("\n") if l.strip()]
        task_count = len(this_week_lines)
        total_tasks += task_count

        # 准备 LLM 分析数据
        reports_for_llm.append({
            "user_name": user.real_name,
            "this_week_work": report.this_week_work or "",
            "next_week_plan": report.next_week_plan or ""
        })

        # 各成员任务数
        member_tasks.append({
            "name": user.real_name,
            "task_count": task_count
        })

        # 成员详情 - 提取主要工作摘要
        main_work = "、".join([l.split(".")[-1].strip()[:20] for l in this_week_lines[:4]])
        next_work = "、".join([l.split(".")[-1].strip()[:20] for l in next_week_lines[:4]])
        member_details.append({
            "name": user.real_name,
            "main_work": main_work,
            "next_work": next_work,
            "task_count": task_count,
            "next_task_count": len(next_week_lines),
            "status": "completed"
        })

        # 下周计划统计：优先使用 report_items 结构化数据
        plan_projects = {}
        next_week_items = [item for item in report.items if item.item_type == ItemType.next_week]

        if next_week_items:
            # 使用结构化数据
            for item in next_week_items:
                proj = item.project_name or "其他"
                plan_projects[proj] = plan_projects.get(proj, 0) + 1
        else:
            # 降级：使用文本解析
            for line in next_week_lines:
                projs = extract_projects_from_text(line)
                if projs:
                    for p in projs:
                        plan_projects[p] = plan_projects.get(p, 0) + 1
                else:
                    plan_projects["其他"] = plan_projects.get("其他", 0) + 1

        if plan_projects:
            next_week_plans.append({
                "name": user.real_name,
                "projects": plan_projects
            })

    # 项目参与度统计：优先使用 report_items 结构化数据
    project_involvement = {}  # 项目 -> 工作条目数
    project_people = {}  # 项目 -> 参与人员集合
    work_categories = {}
    all_projects = set()
    has_structured_data = False

    for report, user in reports_with_users:
        this_week_items = [item for item in report.items if item.item_type == ItemType.this_week]

        if this_week_items:
            # 使用结构化数据
            has_structured_data = True
            for item in this_week_items:
                proj = item.project_name or "其他"
                all_projects.add(proj)
                project_involvement[proj] = project_involvement.get(proj, 0) + 1
                # 记录参与人员
                if proj not in project_people:
                    project_people[proj] = set()
                project_people[proj].add(user.real_name)
                # 工作分类
                category = categorize_work(item.content or "")
                work_categories[category] = work_categories.get(category, 0) + 1
        else:
            # 该用户没有结构化数据，使用文本解析
            work_text = report.this_week_work or ""
            projects = extract_projects_from_text(work_text)
            for proj in projects:
                all_projects.add(proj)
                project_involvement[proj] = project_involvement.get(proj, 0) + 1
                # 记录参与人员
                if proj not in project_people:
                    project_people[proj] = set()
                project_people[proj].add(user.real_name)

            this_week_lines = [l.strip() for l in work_text.split("\n") if l.strip()]
            for line in this_week_lines:
                category = categorize_work(line)
                work_categories[category] = work_categories.get(category, 0) + 1

    # 如果没有任何结构化数据，尝试从 LLM 缓存获取
    if not has_structured_data:
        llm_result = await get_cached_llm_analysis(db, year, week_num)
        if llm_result and llm_result.get("project_involvement"):
            project_data = llm_result["project_involvement"]
            category_data = llm_result.get("work_categories", [])
            all_projects = set(p["name"] for p in project_data)
        else:
            # 使用上面的关键词提取结果
            project_data = [{"name": k, "value": v} for k, v in sorted(project_involvement.items(), key=lambda x: -x[1])]
            category_data = [{"name": k, "value": v} for k, v in sorted(work_categories.items(), key=lambda x: -x[1])]
    else:
        # 使用结构化数据的统计结果
        project_data = [{"name": k, "value": v} for k, v in sorted(project_involvement.items(), key=lambda x: -x[1])]
        category_data = [{"name": k, "value": v} for k, v in sorted(work_categories.items(), key=lambda x: -x[1])]

    # 主要项目列表：按参与人数排序（人数相同则按工作条目数）
    main_projects = sorted(
        all_projects,
        key=lambda p: (len(project_people.get(p, set())), project_involvement.get(p, 0)),
        reverse=True
    )[:6]

    return {
        "year": year,
        "week_num": week_num,
        "date_range": f"{start_date} ~ {end_date}",
        "stats": {
            "total_members": total_members,
            "total_tasks": total_tasks,
            "completion_rate": round(submitted_count / total_members * 100) if total_members else 0,
            "main_projects_count": len(all_projects)
        },
        "member_tasks": member_tasks,
        "project_involvement": project_data,
        "main_projects": main_projects,
        "work_categories": category_data,
        "member_details": member_details,
        "next_week_plans": next_week_plans
    }


async def get_chart_statistics(db: AsyncSession, year: int, start_week: int, end_week: int) -> dict:
    """获取图表统计数据"""
    from app.models.report import ReportStatus

    total_members = await db.scalar(select(func.count(User.id)).where(User.is_active == True))

    weekly_stats = []
    for week_num in range(start_week, end_week + 1):
        start_date, end_date = get_week_date_range(year, week_num)

        # 查询该周已提交的周报
        result = await db.execute(
            select(Report, User)
            .join(User)
            .where(
                Report.year == year,
                Report.week_num == week_num,
                Report.status == ReportStatus.submitted
            )
        )
        reports_with_users = result.all()
        submitted_count = len(reports_with_users)

        # 统计任务数和每个人的任务
        total_tasks = 0
        user_tasks = []
        for report, user in reports_with_users:
            task_count = len([l for l in (report.this_week_work or "").split("\n") if l.strip()])
            total_tasks += task_count
            user_tasks.append({
                "user_name": user.real_name,
                "task_count": task_count
            })

        weekly_stats.append({
            "week_num": week_num,
            "date_range": f"{start_date} ~ {end_date}",
            "submitted_count": submitted_count,
            "not_submitted_count": total_members - submitted_count,
            "submission_rate": round(submitted_count / total_members * 100, 1) if total_members else 0,
            "total_tasks": total_tasks,
            "user_tasks": user_tasks
        })

    # 计算总体统计
    total_submitted = sum(w["submitted_count"] for w in weekly_stats)
    total_tasks_all = sum(w["total_tasks"] for w in weekly_stats)
    avg_submission_rate = round(sum(w["submission_rate"] for w in weekly_stats) / len(weekly_stats), 1) if weekly_stats else 0

    return {
        "year": year,
        "start_week": start_week,
        "end_week": end_week,
        "total_members": total_members,
        "weekly_stats": weekly_stats,
        "summary": {
            "total_submitted": total_submitted,
            "total_tasks": total_tasks_all,
            "avg_submission_rate": avg_submission_rate
        }
    }


async def save_weekly_summary(db: AsyncSession, year: int, week_num: int, summary_data: dict, doc_path: Optional[str] = None):
    """保存周汇总"""
    result = await db.execute(
        select(WeeklySummary).where(
            WeeklySummary.year == year,
            WeeklySummary.week_num == week_num
        )
    )
    summary = result.scalar_one_or_none()

    if summary:
        summary.summary_data = json.dumps(summary_data, ensure_ascii=False)
        if doc_path:
            summary.doc_path = doc_path
    else:
        summary = WeeklySummary(
            year=year,
            week_num=week_num,
            summary_data=json.dumps(summary_data, ensure_ascii=False),
            doc_path=doc_path
        )
        db.add(summary)

    await db.commit()
    return summary
