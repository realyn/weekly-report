"""
测试不同 LLM 模型的解析效果和 token 使用量
"""
import asyncio
import sys
import time
import json
from pathlib import Path
import httpx

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.report_parser_service import ReportParserService
from app.config import get_settings

settings = get_settings()

# 测试用例
TEST_THIS_WEEK = """1. 清明上河园沟通对接
2. 一省一报系统功能优化
3. 大河云AI升级需求讨论
4. 服务器运维巡检
5. RAG知识库调研"""

TEST_NEXT_WEEK = """1. 继续清明上河园项目开发
2. 完成一省一报通道管理功能
3. 参加AI升级技术评审"""


def estimate_tokens(text: str) -> int:
    """估算中文文本的 token 数（粗略：1个中文字≈1.5 token）"""
    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    other_chars = len(text) - chinese_chars
    return int(chinese_chars * 1.5 + other_chars * 0.3)


async def call_dashscope(prompt: str, system: str, model: str) -> tuple[str, dict]:
    """调用 DashScope API，返回响应和 usage 信息"""
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
        "model": model,
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 2000
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        usage = result.get("usage", {})
        return content, usage


async def call_deepseek(prompt: str, system: str) -> tuple[str, dict]:
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
        content = result["choices"][0]["message"]["content"]
        usage = result.get("usage", {})
        return content, usage


async def test_model(model_name: str, provider: str):
    """测试单个模型"""
    print(f"\n{'='*60}")
    print(f"测试模型: {model_name} (provider: {provider})")
    print('='*60)

    # 创建服务实例
    parser = ReportParserService()

    # 获取项目列表
    known_projects = parser._get_known_projects_str()

    # 构建完整 prompt
    full_prompt = parser.PARSE_PROMPT_TEMPLATE.format(
        known_projects=known_projects,
        this_week_work=TEST_THIS_WEEK,
        next_week_plan=TEST_NEXT_WEEK
    )
    system_prompt = parser.PARSE_SYSTEM_PROMPT

    # Token 估算
    estimated_input = estimate_tokens(system_prompt + full_prompt)
    print(f"\n📊 Prompt 信息:")
    print(f"   System Prompt 字符数: {len(system_prompt)}")
    print(f"   项目列表字符数: {len(known_projects)}")
    print(f"   用户输入字符数: {len(TEST_THIS_WEEK + TEST_NEXT_WEEK)}")
    print(f"   总 Prompt 字符数: {len(system_prompt + full_prompt)}")

    start_time = time.time()
    try:
        if provider == "dashscope":
            response, usage = await call_dashscope(full_prompt, system_prompt, model_name)
        else:
            response, usage = await call_deepseek(full_prompt, system_prompt)

        elapsed = time.time() - start_time

        # 实际 token 使用量
        input_tokens = usage.get("prompt_tokens", estimated_input)
        output_tokens = usage.get("completion_tokens", estimate_tokens(response))
        total_tokens = usage.get("total_tokens", input_tokens + output_tokens)

        print(f"\n📊 实际 Token 使用量 (API 返回):")
        print(f"   输入 tokens: {input_tokens}")
        print(f"   输出 tokens: {output_tokens}")
        print(f"   总计 tokens: {total_tokens}")
        print(f"\n⏱️  响应时间: {elapsed:.2f}s")

        # 解析结果
        print(f"\n📝 原始响应 (前500字符):")
        print(response[:500] + "..." if len(response) > 500 else response)

        # 尝试解析 JSON
        parse_success = False
        try:
            cleaned = parser._clean_json_response(response)
            parsed = json.loads(cleaned)
            this_week_count = len(parsed.get("this_week_items", []))
            next_week_count = len(parsed.get("next_week_items", []))
            print(f"\n✅ 解析成功: 本周{this_week_count}条, 下周{next_week_count}条")
            parse_success = True

            # 显示解析结果
            print("\n本周工作解析:")
            for item in parsed.get("this_week_items", []):
                proj = item.get("project_name") or "未分类"
                content = item.get("content", "")[:40]
                print(f"   [{proj}] {content}")

        except json.JSONDecodeError as e:
            print(f"\n❌ JSON 解析失败: {e}")

    except Exception as e:
        print(f"\n❌ 调用失败: {e}")
        import traceback
        traceback.print_exc()
        return None

    return {
        "model": model_name,
        "provider": provider,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "response_time": elapsed,
        "parse_success": parse_success
    }


async def main():
    print("="*60)
    print("LLM 模型效果与 Token 使用量测试")
    print("="*60)

    # 测试模型列表
    models = [
        ("qwen-turbo", "dashscope"),      # 最快最便宜
        ("qwen-plus", "dashscope"),       # 平衡
        ("deepseek-chat", "deepseek"),    # DeepSeek
    ]

    results = []
    for model_name, provider in models:
        result = await test_model(model_name, provider)
        if result:
            results.append(result)

    # 汇总对比
    print("\n" + "="*60)
    print("📊 模型对比汇总")
    print("="*60)
    print(f"{'模型':<20} {'响应时间':>10} {'输入tokens':>12} {'输出tokens':>12} {'总tokens':>10}")
    print("-"*60)
    for r in results:
        print(f"{r['model']:<20} {r['response_time']:>8.2f}s {r['input_tokens']:>12} {r['output_tokens']:>12} {r['total_tokens']:>10}")

    # 费用估算（按通义千问定价）
    print("\n💰 费用估算 (每次解析):")
    print("   qwen-turbo:  输入 ¥0.0003/1K + 输出 ¥0.0006/1K")
    print("   qwen-plus:   输入 ¥0.0008/1K + 输出 ¥0.002/1K")
    print("   deepseek:    输入 ¥0.001/1K  + 输出 ¥0.002/1K")


if __name__ == "__main__":
    asyncio.run(main())
