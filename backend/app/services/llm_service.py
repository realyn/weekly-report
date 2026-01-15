"""
LLM 服务 - 用于智能抽取项目信息
支持 Qwen (DashScope)、DeepSeek、OpenAI 兼容接口

方案四：混合智能匹配 + Embedding 增强
1. LLM 原始抽取 → 2. 精确匹配 → 3. Embedding 语义匹配 → 4. LLM智能匹配 → 5. 待审核队列
"""
import json
import math
import os
from datetime import datetime
from typing import Optional, List, Dict
import httpx
from app.config import get_settings

settings = get_settings()


class EmbeddingService:
    """Embedding 向量服务 - 使用阿里云 DashScope"""

    def __init__(self):
        self.api_key = settings.DASHSCOPE_API_KEY
        self.model = settings.EMBEDDING_MODEL
        self.dimension = settings.EMBEDDING_DIMENSION
        self.base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    async def get_embedding(self, text: str) -> List[float]:
        """获取单个文本的向量"""
        if not self.api_key:
            return []

        url = f"{self.base_url}/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "input": text,
            "encoding_format": "float"
        }
        # text-embedding-v4 支持自定义维度
        if self.model == "text-embedding-v4":
            payload["dimensions"] = self.dimension

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                result = response.json()
                return result["data"][0]["embedding"]
        except Exception as e:
            print(f"Embedding 调用失败: {e}")
            return []

    async def get_embeddings_batch(self, texts: List[str], batch_size: int = 10) -> List[List[float]]:
        """批量获取文本向量（分批处理）"""
        if not self.api_key or not texts:
            return []

        url = f"{self.base_url}/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        all_embeddings = []

        # 分批处理
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            payload = {
                "model": self.model,
                "input": batch,
                "encoding_format": "float"
            }
            if self.model == "text-embedding-v4":
                payload["dimensions"] = self.dimension

            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(url, headers=headers, json=payload)
                    response.raise_for_status()
                    result = response.json()
                    # 按 index 排序返回
                    embeddings = sorted(result["data"], key=lambda x: x["index"])
                    all_embeddings.extend([e["embedding"] for e in embeddings])
            except Exception as e:
                print(f"Embedding 批量调用失败 (batch {i//batch_size + 1}): {e}")
                # 继续处理剩余批次，用空向量填充失败的
                all_embeddings.extend([[] for _ in batch])

        return all_embeddings

    @staticmethod
    def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """计算余弦相似度"""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)


class LLMService:
    """LLM 调用服务"""

    def __init__(self):
        self.provider = settings.LLM_PROVIDER

    async def _call_openai_compatible(self, prompt: str, system: str = "", model: str = "qwen-flash") -> str:
        """调用 OpenAI 兼容接口"""
        url = f"{settings.OPENAI_BASE_URL}/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 2000
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]

    async def _call_deepseek(self, prompt: str, system: str = "") -> str:
        """调用 DeepSeek API"""
        url = f"{settings.DEEPSEEK_BASE_URL}/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": "deepseek-chat",
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 2000
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]

    async def _call_dashscope(self, prompt: str, system: str = "") -> str:
        """调用阿里云 DashScope API"""
        url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.DASHSCOPE_API_KEY}",
            "Content-Type": "application/json"
        }
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": "qwen-turbo",
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 2000
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]

    async def call(self, prompt: str, system: str = "") -> str:
        """统一调用接口"""
        try:
            if self.provider == "deepseek":
                return await self._call_deepseek(prompt, system)
            elif self.provider == "dashscope":
                return await self._call_dashscope(prompt, system)
            else:  # 默认使用 qwen (openai compatible)
                return await self._call_openai_compatible(prompt, system)
        except Exception as e:
            print(f"LLM 调用失败: {e}")
            return ""


class ProjectExtractor:
    """项目智能抽取器 - 混合匹配方案 + Embedding 增强"""

    # Embedding 相似度阈值
    EMBEDDING_HIGH_THRESHOLD = 0.85   # 高于此值自动匹配
    EMBEDDING_LOW_THRESHOLD = 0.60    # 低于此值视为不匹配

    # 第一阶段：原始项目提取
    EXTRACT_SYSTEM_PROMPT = """你是一个专业的项目信息抽取助手。从周报中提取所有项目/系统/产品的提及。

抽取规则：
1. 识别所有项目、系统、产品、平台的名称
2. 保留原始表述，不要自行归一化或合并
3. 不要把工作类型（如"功能开发"、"问题排查"、"会议"、"沟通"）当作项目
4. 提取工作类型分类统计

输出格式：必须严格按照 JSON 格式输出，不要有其他文字。"""

    EXTRACT_PROMPT_TEMPLATE = """请从以下周报内容中提取项目信息。

本周工作内容：
{work_content}

请输出 JSON 格式：
{{
  "raw_mentions": ["项目提及1", "项目提及2", ...],
  "work_categories": {{
    "功能开发": 数量,
    "问题排查": 数量,
    "系统维护": 数量,
    "需求沟通": 数量,
    "其他": 数量
  }}
}}"""

    # 第二阶段：智能匹配
    MATCH_SYSTEM_PROMPT = """你是一个项目名称匹配助手。判断提取到的项目提及是否属于已知项目。

匹配规则：
1. 如果提及明显是某个已知项目（包括其别名、简称、缩写），返回匹配的项目名
2. 如果提及是全新的项目（不在已知列表中），标记为新项目
3. 如果提及不是项目（是工作描述、会议、日常事务等），标记为忽略
4. 返回置信度（0-1），表示匹配的确定程度

输出格式：必须严格按照 JSON 格式输出。"""

    MATCH_PROMPT_TEMPLATE = """已知项目列表：
{known_projects}

待匹配的项目提及：
{mentions}

对每个提及进行匹配判断，输出 JSON：
{{
  "matches": [
    {{
      "mention": "原始提及",
      "matched_project": "匹配到的项目标准名" 或 null,
      "is_new_project": true/false,
      "should_ignore": true/false,
      "confidence": 0.0-1.0,
      "reason": "匹配理由"
    }}
  ],
  "suggested_aliases": [
    {{
      "project": "项目标准名",
      "new_alias": "建议添加的别名"
    }}
  ]
}}"""

    def __init__(self):
        self.llm = LLMService()
        self.embedding = EmbeddingService()
        self.projects_file = settings.PROJECTS_DATA_PATH
        self.embeddings_file = settings.PROJECTS_DATA_PATH.replace('.json', '_embeddings.json')
        self._ensure_projects_file()
        self._project_embeddings: Dict[str, List[float]] = {}  # 内存缓存

    def _ensure_projects_file(self):
        """确保项目数据文件存在"""
        os.makedirs(os.path.dirname(self.projects_file), exist_ok=True)
        if not os.path.exists(self.projects_file):
            initial_data = self._get_initial_data()
            with open(self.projects_file, 'w', encoding='utf-8') as f:
                json.dump(initial_data, f, ensure_ascii=False, indent=2)

    def _get_initial_data(self) -> dict:
        """获取初始数据结构"""
        return {
            "projects": [
                {
                    "name": "一省一报系统",
                    "aliases": ["一省一报"],
                    "category": "业务系统",
                    "status": "active",
                    "description": "省级媒体稿件报送系统",
                    "sub_items": [
                        {"name": "通道管理", "description": "稿件传输通道配置与维护"}
                    ]
                },
                {
                    "name": "大河云AI升级",
                    "aliases": ["大河云", "AI升级"],
                    "category": "AI项目",
                    "status": "active",
                    "description": "大河云平台AI能力升级",
                    "sub_items": []
                },
                {
                    "name": "智慧教育平台",
                    "aliases": ["智慧教育", "红干院"],
                    "category": "业务系统",
                    "status": "active",
                    "description": "智慧教育培训平台",
                    "sub_items": [
                        {"name": "红旗渠干部学院", "description": "红干院在线培训业务"}
                    ]
                },
                {
                    "name": "清明上河图网站",
                    "aliases": ["清图网站", "清图", "清明上河图"],
                    "category": "网站",
                    "status": "active",
                    "description": "清明上河图相关网站项目",
                    "sub_items": [
                        {"name": "河南科技传媒学院合作", "description": ""},
                        {"name": "清明上河园合作", "description": ""}
                    ]
                },
                {
                    "name": "河南日报广告业务系统",
                    "aliases": ["广告业务", "广告系统"],
                    "category": "业务系统",
                    "status": "active",
                    "description": "广告业务管理系统",
                    "sub_items": []
                },
                {
                    "name": "大语言模型",
                    "aliases": ["RAG", "LLM", "embedding", "langgraph"],
                    "category": "AI项目",
                    "status": "active",
                    "description": "大语言模型研发与应用",
                    "sub_items": []
                },
                {
                    "name": "服务器运维",
                    "aliases": ["服务器", "运维", "监控"],
                    "category": "运维",
                    "status": "active",
                    "description": "服务器日常运维工作",
                    "sub_items": []
                },
            ],
            "categories": ["业务系统", "AI项目", "网站", "运维", "其他"],
            "pending_projects": [],  # 待审核项目
            "rejected": []  # 已拒绝的（避免重复提示）
        }

    def load_known_projects(self) -> dict:
        """加载项目数据"""
        try:
            with open(self.projects_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 兼容旧数据结构
                if "pending_projects" not in data:
                    data["pending_projects"] = []
                if "rejected" not in data:
                    data["rejected"] = []
                return data
        except Exception:
            return self._get_initial_data()

    def save_projects(self, data: dict):
        """保存项目数据"""
        with open(self.projects_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_embeddings(self) -> Dict[str, List[float]]:
        """加载项目向量缓存"""
        if self._project_embeddings:
            return self._project_embeddings

        try:
            if os.path.exists(self.embeddings_file):
                with open(self.embeddings_file, 'r', encoding='utf-8') as f:
                    self._project_embeddings = json.load(f)
        except Exception:
            self._project_embeddings = {}

        return self._project_embeddings

    def save_embeddings(self, embeddings: Dict[str, List[float]]):
        """保存项目向量缓存"""
        self._project_embeddings = embeddings
        with open(self.embeddings_file, 'w', encoding='utf-8') as f:
            json.dump(embeddings, f, ensure_ascii=False)

    async def build_project_embeddings(self):
        """构建/更新所有项目的向量索引"""
        data = self.load_known_projects()
        embeddings = self.load_embeddings()

        # 收集需要计算向量的项目名和别名
        texts_to_embed = []
        text_to_project = {}  # 文本 -> 项目标准名 映射

        for proj in data.get("projects", []):
            if proj.get("status") == "archived":
                continue

            proj_name = proj["name"]
            # 项目名
            if proj_name not in embeddings:
                texts_to_embed.append(proj_name)
                text_to_project[proj_name] = proj_name

            # 别名
            for alias in proj.get("aliases", []):
                if alias not in embeddings:
                    texts_to_embed.append(alias)
                    text_to_project[alias] = proj_name

        if not texts_to_embed:
            print("所有项目向量已是最新")
            return

        print(f"计算 {len(texts_to_embed)} 个项目/别名的向量...")

        # 批量获取向量
        new_embeddings = await self.embedding.get_embeddings_batch(texts_to_embed)

        if len(new_embeddings) == len(texts_to_embed):
            for text, vec in zip(texts_to_embed, new_embeddings):
                embeddings[text] = vec
            self.save_embeddings(embeddings)
            print(f"向量索引更新完成，共 {len(embeddings)} 条")
        else:
            print(f"向量计算失败，预期 {len(texts_to_embed)} 条，实际 {len(new_embeddings)} 条")

    async def embedding_match(self, mention: str, projects: list) -> Optional[tuple]:
        """
        Embedding 语义匹配
        返回: (匹配的项目名, 相似度) 或 None
        """
        embeddings = self.load_embeddings()

        # 如果没有项目向量，跳过
        if not embeddings:
            return None

        # 获取查询文本的向量
        query_vec = await self.embedding.get_embedding(mention)
        if not query_vec:
            return None

        best_match = None
        best_score = 0.0

        for proj in projects:
            if proj.get("status") == "archived":
                continue

            proj_name = proj["name"]

            # 检查项目名
            if proj_name in embeddings:
                score = EmbeddingService.cosine_similarity(query_vec, embeddings[proj_name])
                if score > best_score:
                    best_score = score
                    best_match = proj_name

            # 检查别名
            for alias in proj.get("aliases", []):
                if alias in embeddings:
                    score = EmbeddingService.cosine_similarity(query_vec, embeddings[alias])
                    if score > best_score:
                        best_score = score
                        best_match = proj_name

        if best_match and best_score >= self.EMBEDDING_LOW_THRESHOLD:
            return (best_match, best_score)

        return None

    def exact_match(self, mention: str, projects: list) -> Optional[str]:
        """精确匹配：项目名或别名完全匹配"""
        mention_lower = mention.lower().strip()
        for proj in projects:
            if proj.get("status") == "archived":
                continue
            # 项目名匹配
            if mention_lower == proj["name"].lower():
                return proj["name"]
            # 别名匹配
            for alias in proj.get("aliases", []):
                if mention_lower == alias.lower():
                    return proj["name"]
                # 包含匹配（如 "清图网站更新" 包含 "清图"）
                if alias.lower() in mention_lower and len(alias) >= 2:
                    return proj["name"]
        return None

    def is_rejected(self, mention: str, rejected: list) -> bool:
        """检查是否在拒绝列表中"""
        mention_lower = mention.lower().strip()
        for r in rejected:
            if r.lower() == mention_lower:
                return True
        return False

    def is_pending(self, mention: str, pending: list) -> bool:
        """检查是否已在待审核列表中"""
        mention_lower = mention.lower().strip()
        for p in pending:
            if p["name"].lower() == mention_lower:
                return True
        return False

    async def phase1_extract(self, work_content: str) -> dict:
        """第一阶段：LLM 原始提取"""
        prompt = self.EXTRACT_PROMPT_TEMPLATE.format(work_content=work_content)

        try:
            response = await self.llm.call(prompt, self.EXTRACT_SYSTEM_PROMPT)
            response = self._clean_json_response(response)
            result = json.loads(response)
            return {
                "raw_mentions": result.get("raw_mentions", []),
                "work_categories": result.get("work_categories", {})
            }
        except Exception as e:
            print(f"第一阶段提取失败: {e}")
            return {"raw_mentions": [], "work_categories": {}}

    async def phase2_match(self, mentions: list, known_data: dict) -> dict:
        """第二阶段：智能匹配"""
        if not mentions:
            return {"matches": [], "suggested_aliases": []}

        # 生成已知项目列表
        projects_list = "\n".join([
            f"- {p['name']}（别名：{', '.join(p.get('aliases', []))}）"
            for p in known_data["projects"]
            if p.get("status") != "archived"
        ])

        prompt = self.MATCH_PROMPT_TEMPLATE.format(
            known_projects=projects_list or "暂无",
            mentions=json.dumps(mentions, ensure_ascii=False)
        )

        try:
            response = await self.llm.call(prompt, self.MATCH_SYSTEM_PROMPT)
            response = self._clean_json_response(response)
            return json.loads(response)
        except Exception as e:
            print(f"第二阶段匹配失败: {e}")
            return {"matches": [], "suggested_aliases": []}

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

    async def extract_from_text(self, work_content: str) -> dict:
        """混合匹配流程：提取并匹配项目"""
        known_data = self.load_known_projects()
        projects = known_data.get("projects", [])
        rejected = known_data.get("rejected", [])
        pending = known_data.get("pending_projects", [])

        # 第一阶段：原始提取
        phase1_result = await self.phase1_extract(work_content)
        raw_mentions = phase1_result.get("raw_mentions", [])
        work_categories = phase1_result.get("work_categories", {})

        # 分类处理
        matched_projects = {}  # {标准名: {mentions, work_items}}
        unmatched_mentions = []  # 需要进一步匹配的

        for mention in raw_mentions:
            # 检查拒绝列表
            if self.is_rejected(mention, rejected):
                continue

            # 精确匹配
            matched_name = self.exact_match(mention, projects)
            if matched_name:
                if matched_name not in matched_projects:
                    matched_projects[matched_name] = {"name": matched_name, "mentions": 0, "work_items": []}
                matched_projects[matched_name]["mentions"] += 1
                matched_projects[matched_name]["work_items"].append(mention)
            else:
                unmatched_mentions.append(mention)

        # 第1.5阶段：Embedding 语义匹配
        still_unmatched = []
        for mention in unmatched_mentions:
            embed_result = await self.embedding_match(mention, projects)
            if embed_result:
                matched_name, score = embed_result
                if score >= self.EMBEDDING_HIGH_THRESHOLD:
                    # 高置信度，自动匹配
                    if matched_name not in matched_projects:
                        matched_projects[matched_name] = {"name": matched_name, "mentions": 0, "work_items": []}
                    matched_projects[matched_name]["mentions"] += 1
                    matched_projects[matched_name]["work_items"].append(mention)
                    print(f"Embedding 匹配: {mention} -> {matched_name} (score={score:.2f})")
                else:
                    # 中等置信度，交给 LLM 确认
                    still_unmatched.append(mention)
            else:
                still_unmatched.append(mention)

        unmatched_mentions = still_unmatched

        # 第二阶段：LLM 智能匹配（仅处理未匹配的）
        new_pending = []
        if unmatched_mentions:
            phase2_result = await self.phase2_match(unmatched_mentions, known_data)

            for match in phase2_result.get("matches", []):
                mention = match.get("mention", "")
                matched_project = match.get("matched_project")
                is_new = match.get("is_new_project", False)
                should_ignore = match.get("should_ignore", False)
                confidence = match.get("confidence", 0)

                if should_ignore:
                    # 添加到拒绝列表（低置信度的忽略项）
                    if confidence > 0.7 and mention not in rejected:
                        rejected.append(mention)
                    continue

                if matched_project and confidence >= 0.6:
                    # 匹配成功
                    if matched_project not in matched_projects:
                        matched_projects[matched_project] = {"name": matched_project, "mentions": 0, "work_items": []}
                    matched_projects[matched_project]["mentions"] += 1
                    matched_projects[matched_project]["work_items"].append(mention)
                elif is_new and confidence >= 0.7:
                    # 新项目，加入待审核
                    if not self.is_pending(mention, pending) and mention not in rejected:
                        new_pending.append({
                            "name": mention,
                            "first_seen": datetime.now().strftime("%Y-%m-%d"),
                            "mentions": 1,
                            "source_texts": [mention],
                            "suggested_category": "其他",
                            "confidence": confidence
                        })

            # 处理别名建议
            for alias_suggestion in phase2_result.get("suggested_aliases", []):
                proj_name = alias_suggestion.get("project")
                new_alias = alias_suggestion.get("new_alias")
                if proj_name and new_alias:
                    for proj in projects:
                        if proj["name"] == proj_name and new_alias not in proj.get("aliases", []):
                            proj.setdefault("aliases", []).append(new_alias)
                            print(f"自动学习别名: {proj_name} <- {new_alias}")

        # 更新待审核列表
        for new_p in new_pending:
            # 检查是否已存在
            existing = next((p for p in pending if p["name"].lower() == new_p["name"].lower()), None)
            if existing:
                existing["mentions"] += 1
                existing["source_texts"].extend(new_p["source_texts"])
            else:
                pending.append(new_p)

        # 保存更新
        known_data["rejected"] = rejected
        known_data["pending_projects"] = pending
        self.save_projects(known_data)

        return {
            "projects": list(matched_projects.values()),
            "work_categories": work_categories,
            "new_projects": [p["name"] for p in new_pending]
        }

    async def extract_batch(self, reports: list) -> dict:
        """批量提取多人周报的项目信息"""
        all_work_content = []

        for report in reports:
            user_name = report.get("user_name", "未知")
            this_week = report.get("this_week_work", "")
            all_work_content.append(f"【{user_name}】本周工作：\n{this_week}")

        combined_content = "\n\n".join(all_work_content)

        # 调用混合匹配流程
        result = await self.extract_from_text(combined_content)

        # 统计项目参与情况
        project_involvement = {}
        for proj in result.get("projects", []):
            proj_name = proj.get("name", "")
            mentions = proj.get("mentions", 1)
            project_involvement[proj_name] = mentions

        return {
            "project_involvement": [
                {"name": k, "value": v}
                for k, v in sorted(project_involvement.items(), key=lambda x: -x[1])
            ],
            "work_categories": [
                {"name": k, "value": v}
                for k, v in result.get("work_categories", {}).items()
                if v > 0
            ],
            "raw_result": result
        }

    # ========== 项目管理 API ==========

    def get_pending_projects(self) -> list:
        """获取待审核项目列表"""
        data = self.load_known_projects()
        return data.get("pending_projects", [])

    def approve_pending_project(self, name: str, category: str = "其他") -> bool:
        """确认待审核项目"""
        data = self.load_known_projects()
        pending = data.get("pending_projects", [])

        # 找到待审核项目
        target = next((p for p in pending if p["name"] == name), None)
        if not target:
            return False

        # 添加到正式列表
        data["projects"].append({
            "name": name,
            "aliases": [],
            "category": category,
            "status": "active"
        })

        # 从待审核中移除
        data["pending_projects"] = [p for p in pending if p["name"] != name]
        self.save_projects(data)
        return True

    def merge_pending_to_existing(self, pending_name: str, target_project: str) -> bool:
        """将待审核项目作为别名合并到已有项目"""
        data = self.load_known_projects()
        pending = data.get("pending_projects", [])

        # 找到待审核项目
        target_pending = next((p for p in pending if p["name"] == pending_name), None)
        if not target_pending:
            return False

        # 找到目标项目并添加别名
        for proj in data["projects"]:
            if proj["name"] == target_project:
                if pending_name not in proj.get("aliases", []):
                    proj.setdefault("aliases", []).append(pending_name)
                break
        else:
            return False

        # 从待审核中移除
        data["pending_projects"] = [p for p in pending if p["name"] != pending_name]
        self.save_projects(data)
        return True

    def reject_pending_project(self, name: str) -> bool:
        """拒绝待审核项目"""
        data = self.load_known_projects()
        pending = data.get("pending_projects", [])

        # 从待审核中移除
        data["pending_projects"] = [p for p in pending if p["name"] != name]

        # 添加到拒绝列表
        if name not in data.get("rejected", []):
            data.setdefault("rejected", []).append(name)

        self.save_projects(data)
        return True

    def get_all_projects(self) -> list:
        """获取所有项目（用于下拉选择）"""
        data = self.load_known_projects()
        return [{"name": p["name"], "category": p.get("category", "其他")}
                for p in data.get("projects", [])
                if p.get("status") != "archived"]

    def add_alias(self, project_name: str, alias: str) -> bool:
        """为项目添加别名"""
        data = self.load_known_projects()
        for proj in data["projects"]:
            if proj["name"] == project_name:
                if alias not in proj.get("aliases", []):
                    proj.setdefault("aliases", []).append(alias)
                    self.save_projects(data)
                return True
        return False

    async def rebuild_embeddings(self):
        """重建所有项目向量索引"""
        # 清空缓存
        self._project_embeddings = {}
        if os.path.exists(self.embeddings_file):
            os.remove(self.embeddings_file)
        # 重新构建
        await self.build_project_embeddings()

    # ========== 项目完整管理 API ==========

    def get_project(self, name: str) -> Optional[dict]:
        """获取单个项目详情"""
        data = self.load_known_projects()
        for proj in data.get("projects", []):
            if proj["name"] == name:
                return proj
        return None

    def get_all_projects_detail(self) -> list:
        """获取所有项目详情（含子项目）"""
        data = self.load_known_projects()
        return data.get("projects", [])

    def create_project(self, name: str, category: str = "其他",
                       description: str = "", aliases: list = None,
                       sub_items: list = None) -> bool:
        """创建新项目"""
        data = self.load_known_projects()

        # 检查是否已存在
        for proj in data["projects"]:
            if proj["name"] == name:
                return False

        new_project = {
            "name": name,
            "aliases": aliases or [],
            "category": category,
            "status": "active",
            "description": description,
            "sub_items": sub_items or []
        }
        data["projects"].append(new_project)
        self.save_projects(data)
        return True

    def update_project(self, name: str, updates: dict) -> bool:
        """更新项目信息"""
        data = self.load_known_projects()

        for proj in data["projects"]:
            if proj["name"] == name:
                # 可更新字段
                allowed_fields = ["description", "category", "status", "aliases", "sub_items"]
                for field in allowed_fields:
                    if field in updates:
                        proj[field] = updates[field]
                self.save_projects(data)
                return True
        return False

    def rename_project(self, old_name: str, new_name: str) -> bool:
        """重命名项目"""
        data = self.load_known_projects()

        # 检查新名称是否已存在
        for proj in data["projects"]:
            if proj["name"] == new_name:
                return False

        for proj in data["projects"]:
            if proj["name"] == old_name:
                proj["name"] = new_name
                self.save_projects(data)
                return True
        return False

    def delete_project(self, name: str) -> bool:
        """删除项目"""
        data = self.load_known_projects()
        original_len = len(data["projects"])
        data["projects"] = [p for p in data["projects"] if p["name"] != name]

        if len(data["projects"]) < original_len:
            self.save_projects(data)
            return True
        return False

    def _normalize_sub_items(self, sub_items: list) -> list:
        """将子项目列表规范化为对象格式"""
        result = []
        for item in sub_items:
            if isinstance(item, str):
                result.append({"name": item, "description": ""})
            elif isinstance(item, dict):
                result.append(item)
        return result

    def _get_sub_item_name(self, item) -> str:
        """获取子项目名称，兼容字符串和对象格式"""
        if isinstance(item, str):
            return item
        return item.get("name", "")

    def add_sub_item(self, project_name: str, sub_name: str, description: str = "") -> bool:
        """添加子项目"""
        data = self.load_known_projects()

        for proj in data["projects"]:
            if proj["name"] == project_name:
                if "sub_items" not in proj:
                    proj["sub_items"] = []
                # 规范化现有数据
                proj["sub_items"] = self._normalize_sub_items(proj["sub_items"])
                # 检查是否已存在
                for item in proj["sub_items"]:
                    if item["name"] == sub_name:
                        return False
                proj["sub_items"].append({"name": sub_name, "description": description})
                self.save_projects(data)
                return True
        return False

    def remove_sub_item(self, project_name: str, sub_name: str) -> bool:
        """移除子项目"""
        data = self.load_known_projects()

        for proj in data["projects"]:
            if proj["name"] == project_name:
                if "sub_items" not in proj:
                    return False
                # 规范化现有数据
                proj["sub_items"] = self._normalize_sub_items(proj["sub_items"])
                original_len = len(proj["sub_items"])
                proj["sub_items"] = [s for s in proj["sub_items"] if s["name"] != sub_name]
                if len(proj["sub_items"]) < original_len:
                    self.save_projects(data)
                    return True
        return False

    def update_sub_item(self, project_name: str, sub_name: str, updates: dict) -> bool:
        """更新子项目信息"""
        data = self.load_known_projects()

        for proj in data["projects"]:
            if proj["name"] == project_name:
                # 规范化现有数据
                proj["sub_items"] = self._normalize_sub_items(proj.get("sub_items", []))
                for item in proj["sub_items"]:
                    if item["name"] == sub_name:
                        if "description" in updates:
                            item["description"] = updates["description"]
                        if "name" in updates and updates["name"] != sub_name:
                            item["name"] = updates["name"]
                        self.save_projects(data)
                        return True
        return False

    def add_category(self, category: str) -> bool:
        """添加项目类别"""
        data = self.load_known_projects()
        if category not in data.get("categories", []):
            data.setdefault("categories", []).append(category)
            self.save_projects(data)
            return True
        return False

    def remove_category(self, category: str) -> bool:
        """移除项目类别"""
        data = self.load_known_projects()
        if category in data.get("categories", []):
            data["categories"].remove(category)
            self.save_projects(data)
            return True
        return False

    def get_rejected_list(self) -> list:
        """获取已拒绝（黑名单）列表"""
        data = self.load_known_projects()
        return data.get("rejected", [])

    def get_categories(self) -> list:
        """获取所有项目类别"""
        data = self.load_known_projects()
        return data.get("categories", ["业务系统", "AI项目", "网站", "运维", "其他"])

    def remove_from_rejected(self, name: str) -> bool:
        """从黑名单中移除"""
        data = self.load_known_projects()
        rejected = data.get("rejected", [])
        if name in rejected:
            rejected.remove(name)
            data["rejected"] = rejected
            self.save_projects(data)
            return True
        return False


# 单例
_extractor: Optional[ProjectExtractor] = None


def get_project_extractor() -> ProjectExtractor:
    global _extractor
    if _extractor is None:
        _extractor = ProjectExtractor()
    return _extractor
