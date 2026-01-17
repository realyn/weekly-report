"""
周报解析服务 - 将自由文本解析为结构化工作条目
使用 LLM 分析文本，识别项目名和工作条目，与 projects.json 匹配
"""
import json
import logging
from typing import Optional
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.llm_service import LLMService, get_project_extractor
from app.models.report import Report, ReportItem, ItemType
from app.schemas.report import ParseResult, ParsedWorkItem

logger = logging.getLogger(__name__)


class ReportParserService:
    """周报解析服务"""

    PARSE_SYSTEM_PROMPT = """你是一个专业的工作周报解析助手。将周报文本解析为结构化的工作条目。

解析规则：
1. 识别每条具体的工作内容，拆分成独立条目
2. **重要**：project_name 必须从已知项目列表中精确选择一个项目名称
3. 根据工作内容、项目描述、子项名称和别名来判断归属哪个项目
4. 如果工作内容无法明确归属任何项目，project_name 设为 null
5. 保持原始工作描述的完整性，不要丢失信息
6. 去除无意义的序号、分隔符等

输出格式：必须严格按照 JSON 格式输出，不要有其他文字。"""

    PARSE_PROMPT_TEMPLATE = """请解析以下周报内容。

**重要**：project_name 字段必须从以下项目列表中精确选择，不要自行创造项目名。

已知项目列表：
{known_projects}

本周工作内容：
{this_week_work}

下周计划：
{next_week_plan}

请输出 JSON 格式（project_name 必须是上述列表中的标准项目名，或 null）：
{{
  "this_week_items": [
    {{"project_name": "从列表中选择的标准项目名或null", "content": "具体工作内容"}}
  ],
  "next_week_items": [
    {{"project_name": "从列表中选择的标准项目名或null", "content": "具体计划内容"}}
  ]
}}"""

    def __init__(self):
        self.llm = LLMService()
        self.extractor = get_project_extractor()

    def _get_known_projects_str(self) -> str:
        """获取已知项目列表字符串，包含描述和子项"""
        data = self.extractor.load_known_projects()
        projects = data.get("projects", [])

        lines = []
        for proj in projects:
            if proj.get("status") == "archived":
                continue

            name = proj['name']
            desc = proj.get("description", "")
            sub_items = proj.get("sub_items", [])
            aliases = proj.get("aliases", [])

            # 构建项目信息
            info_parts = []
            if desc:
                info_parts.append(desc)
            if sub_items:
                sub_names = [s.get("name", "") for s in sub_items if s.get("name")]
                if sub_names:
                    info_parts.append(f"子项：{', '.join(sub_names)}")
            if aliases:
                info_parts.append(f"别名：{', '.join(aliases)}")

            if info_parts:
                lines.append(f"- {name}：{'; '.join(info_parts)}")
            else:
                lines.append(f"- {name}")

        return "\n".join(lines) if lines else "暂无"

    def _clean_json_response(self, response: str) -> str:
        """清理 LLM 响应，提取 JSON"""
        response = response.strip()
        if response.startswith("```"):
            parts = response.split("```")
            if len(parts) >= 2:
                response = parts[1]
                if response.startswith("json"):
                    response = response[4:]
        return response.strip()

    def _match_project_name(self, raw_name: Optional[str]) -> Optional[str]:
        """
        匹配项目名到标准名称

        策略：只做精确匹配，信任 LLM 输出
        - LLM 已被要求输出标准项目名
        - 此方法仅验证是否为有效项目名或别名
        - 如不匹配，返回原始值供用户在前端修正
        """
        if not raw_name:
            return None

        data = self.extractor.load_known_projects()
        projects = data.get("projects", [])

        raw_stripped = raw_name.strip()
        raw_lower = raw_stripped.lower()

        for proj in projects:
            if proj.get("status") == "archived":
                continue
            # 精确匹配标准项目名
            if raw_lower == proj["name"].lower():
                return proj["name"]
            # 精确匹配别名
            for alias in proj.get("aliases", []):
                if raw_lower == alias.lower():
                    return proj["name"]

        # 不匹配时返回原始值，供用户在前端修正
        return raw_stripped if raw_stripped else None

    async def parse_report_text(
        self,
        this_week_work: Optional[str],
        next_week_plan: Optional[str]
    ) -> ParseResult:
        """
        解析周报文本，返回结构化工作条目

        Args:
            this_week_work: 本周工作文本
            next_week_plan: 下周计划文本

        Returns:
            ParseResult: 解析结果
        """
        result = ParseResult(
            raw_this_week=this_week_work,
            raw_next_week=next_week_plan
        )

        # 如果没有内容，直接返回空结果
        if not this_week_work and not next_week_plan:
            return result

        # 构建 prompt
        known_projects = self._get_known_projects_str()
        prompt = self.PARSE_PROMPT_TEMPLATE.format(
            known_projects=known_projects,
            this_week_work=this_week_work or "（无）",
            next_week_plan=next_week_plan or "（无）"
        )

        try:
            # 调用 LLM 解析
            response = await self.llm.call(prompt, self.PARSE_SYSTEM_PROMPT)
            response = self._clean_json_response(response)
            parsed = json.loads(response)

            # 处理本周工作
            for item in parsed.get("this_week_items", []):
                project_name = self._match_project_name(item.get("project_name"))
                content = item.get("content", "").strip()
                if content:
                    result.this_week_items.append(
                        ParsedWorkItem(project_name=project_name, content=content)
                    )

            # 处理下周计划
            for item in parsed.get("next_week_items", []):
                project_name = self._match_project_name(item.get("project_name"))
                content = item.get("content", "").strip()
                if content:
                    result.next_week_items.append(
                        ParsedWorkItem(project_name=project_name, content=content)
                    )

            logger.info(
                f"周报解析完成: 本周{len(result.this_week_items)}条, "
                f"下周{len(result.next_week_items)}条"
            )

        except json.JSONDecodeError as e:
            logger.warning(f"LLM 返回 JSON 解析失败: {e}, 使用降级方案")
            result = self._fallback_parse(this_week_work, next_week_plan)
        except Exception as e:
            logger.error(f"周报解析失败: {e}, 使用降级方案")
            result = self._fallback_parse(this_week_work, next_week_plan)

        return result

    def _fallback_parse(
        self,
        this_week_work: Optional[str],
        next_week_plan: Optional[str]
    ) -> ParseResult:
        """
        降级解析方案：简单按行拆分
        当 LLM 不可用时使用
        """
        result = ParseResult(
            raw_this_week=this_week_work,
            raw_next_week=next_week_plan
        )

        def parse_lines(text: Optional[str]) -> list[ParsedWorkItem]:
            if not text:
                return []

            items = []
            # 按行拆分，去除空行和纯序号行
            for line in text.split("\n"):
                line = line.strip()
                # 去除序号前缀
                line = line.lstrip("0123456789.-、）) ")
                if line and len(line) > 2:
                    items.append(ParsedWorkItem(project_name=None, content=line))
            return items

        result.this_week_items = parse_lines(this_week_work)
        result.next_week_items = parse_lines(next_week_plan)

        return result

    async def save_parsed_items(
        self,
        db: AsyncSession,
        report: Report,
        parse_result: ParseResult
    ) -> int:
        """
        保存解析后的工作条目到数据库

        Args:
            db: 数据库会话
            report: 周报对象
            parse_result: 解析结果

        Returns:
            保存的条目数量
        """
        # 先删除旧的 items
        await db.execute(
            delete(ReportItem).where(ReportItem.report_id == report.id)
        )

        count = 0

        # 保存本周工作
        for i, item in enumerate(parse_result.this_week_items):
            report_item = ReportItem(
                report_id=report.id,
                item_type=ItemType.this_week,
                project_name=item.project_name,
                content=item.content,
                sequence=i
            )
            db.add(report_item)
            count += 1

        # 保存下周计划
        for i, item in enumerate(parse_result.next_week_items):
            report_item = ReportItem(
                report_id=report.id,
                item_type=ItemType.next_week,
                project_name=item.project_name,
                content=item.content,
                sequence=i
            )
            db.add(report_item)
            count += 1

        await db.commit()
        logger.info(f"保存周报条目完成: report_id={report.id}, 共{count}条")

        return count


# 单例
_parser_service: Optional[ReportParserService] = None


def get_report_parser_service() -> ReportParserService:
    """获取周报解析服务实例"""
    global _parser_service
    if _parser_service is None:
        _parser_service = ReportParserService()
    return _parser_service
