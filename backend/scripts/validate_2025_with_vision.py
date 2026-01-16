#!/usr/bin/env python3
"""
使用视觉模型验证2025年全部周报数据
将Word文档转换为图片，通过Claude视觉API提取内容，与数据库对比
"""

import os
import sys
import json
import base64
import re
import sqlite3
import tempfile
import subprocess
from datetime import datetime
from pathlib import Path
from difflib import SequenceMatcher

# 配置
SOFFICE_PATH = "/Applications/LibreOffice.app/Contents/MacOS/soffice"
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'weekly_report.db')
WORD_DIR = '/Users/yn/Documents/工作/工时/2025/'
CACHE_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'validation_cache')
TEAM_MEMBERS = ['杨宁', '翦磊', '朱迪', '张士健', '程志强', '闻世坤', '秦闪闪', '蒋奇朴']


def get_week_from_filename(filename):
    """从文件名提取周数"""
    match = re.search(r'2025\.(\d{2})\.(\d{2})\.docx', filename)
    if match:
        month, day = int(match.group(1)), int(match.group(2))
        try:
            date = datetime(2025, month, day)
            return date.isocalendar()[1]
        except ValueError:
            return None
    return None


def docx_to_images(docx_path: str, output_dir: str) -> list:
    """将Word文档转换为图片列表"""
    from pdf2image import convert_from_path

    # 先转换为PDF
    subprocess.run([
        SOFFICE_PATH,
        '--headless',
        '--convert-to', 'pdf',
        '--outdir', output_dir,
        docx_path
    ], check=True, capture_output=True)

    pdf_name = Path(docx_path).stem + '.pdf'
    pdf_path = os.path.join(output_dir, pdf_name)

    # PDF转图片
    images = convert_from_path(pdf_path, dpi=150)
    return images


def image_to_base64(image) -> str:
    """将 PIL Image 转换为 base64"""
    import io
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    return base64.standard_b64encode(buffer.getvalue()).decode('utf-8')


def extract_with_claude(images: list, api_key: str) -> dict:
    """使用 Claude 视觉模型提取表格数据"""
    from anthropic import Anthropic

    client = Anthropic(api_key=api_key)

    # 构建消息内容
    content = []
    for img in images:
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/png",
                "data": image_to_base64(img)
            }
        })

    members_str = '、'.join(TEAM_MEMBERS)

    content.append({
        "type": "text",
        "text": f"""请仔细分析这份周报表格图片，提取每个人的工作内容。

团队成员：{members_str}

请按以下JSON格式返回每个人的数据：
{{
    "成员名": {{
        "this_week_work": "本周工作内容（完整内容，保持原有格式和序号）",
        "next_week_plan": "下周工作计划（完整内容，保持原有格式和序号）"
    }}
}}

注意事项：
1. 表格可能有合并单元格，请根据视觉位置判断内容归属
2. 本周工作和下周计划在不同的表格区域，请区分
3. 只返回JSON，不要其他文字
4. 如果某人的某项内容为空或未找到，设为null
5. 内容要完整，不要截断
6. 保持原文的序号格式（如1、2、或1.2.等）"""
    })

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8192,
        messages=[{"role": "user", "content": content}]
    )

    response_text = response.content[0].text

    # 解析响应
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        import re
        match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response_text)
        if match:
            return json.loads(match.group(1))
        raise ValueError(f"无法解析响应: {response_text[:500]}")


def get_db_records(week_num: int) -> dict:
    """获取数据库中该周所有人的记录"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT u.real_name, r.this_week_work, r.next_week_plan
        FROM reports r
        JOIN users u ON r.user_id = u.id
        WHERE r.year = 2025 AND r.week_num = ?
    ''', (week_num,))

    records = {}
    for row in cursor.fetchall():
        records[row[0]] = {
            'this_week_work': row[1],
            'next_week_plan': row[2]
        }

    conn.close()
    return records


def normalize_text(text: str) -> str:
    """标准化文本用于比较"""
    if not text:
        return ""
    # 移除多余空白，统一标点
    text = re.sub(r'\s+', '', text)
    text = text.replace('，', ',').replace('。', '.').replace('；', ';')
    text = text.replace('：', ':').replace('、', ',')
    return text[:200]  # 只比较前200字符


def similarity(text1: str, text2: str) -> float:
    """计算两段文本的相似度"""
    t1 = normalize_text(text1)
    t2 = normalize_text(text2)
    if not t1 and not t2:
        return 1.0
    if not t1 or not t2:
        return 0.0
    return SequenceMatcher(None, t1, t2).ratio()


def check_content_swap(vision_data: dict, db_records: dict) -> list:
    """检查是否有内容交换错误（A的内容出现在B的记录中）"""
    issues = []

    for member, vision_content in vision_data.items():
        if member not in db_records:
            continue

        db_content = db_records.get(member, {})

        for field in ['this_week_work', 'next_week_plan']:
            vision_text = vision_content.get(field) or ""
            db_text = db_content.get(field) or ""

            if not vision_text:
                continue

            # 检查数据库中的内容是否与视觉提取的匹配
            sim = similarity(vision_text, db_text)

            if sim < 0.5:  # 相似度低于50%，可能有问题
                # 检查是否是其他人的内容
                for other_member, other_content in db_records.items():
                    if other_member == member:
                        continue
                    other_text = other_content.get(field) or ""
                    if similarity(vision_text, other_text) > 0.7:
                        issues.append({
                            'member': member,
                            'field': field,
                            'issue_type': 'content_swap',
                            'similarity': sim,
                            'db_content_preview': db_text[:80] if db_text else 'NULL',
                            'vision_content_preview': vision_text[:80],
                            'possibly_from': other_member
                        })
                        break
                else:
                    # 不是内容交换，可能是其他问题
                    if sim < 0.3:
                        issues.append({
                            'member': member,
                            'field': field,
                            'issue_type': 'mismatch',
                            'similarity': sim,
                            'db_content_preview': db_text[:80] if db_text else 'NULL',
                            'vision_content_preview': vision_text[:80]
                        })

    return issues


def validate_week(filename: str, api_key: str, use_cache: bool = True) -> dict:
    """验证单个周的数据"""
    week_num = get_week_from_filename(filename)
    if week_num is None:
        return {'error': f'无法从文件名解析周数: {filename}'}

    cache_file = os.path.join(CACHE_DIR, f'week_{week_num}_vision.json')

    # 检查缓存
    vision_data = None
    if use_cache and os.path.exists(cache_file):
        with open(cache_file, 'r', encoding='utf-8') as f:
            vision_data = json.load(f)
        print(f"  使用缓存数据")

    if vision_data is None:
        # 转换并提取
        doc_path = os.path.join(WORD_DIR, filename)

        with tempfile.TemporaryDirectory() as tmpdir:
            print(f"  转换为图片...")
            images = docx_to_images(doc_path, tmpdir)
            print(f"  共 {len(images)} 页，调用视觉API...")
            vision_data = extract_with_claude(images, api_key)

        # 保存缓存
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(vision_data, f, ensure_ascii=False, indent=2)

    # 获取数据库记录
    db_records = get_db_records(week_num)

    # 比较检查
    issues = check_content_swap(vision_data, db_records)

    return {
        'week_num': week_num,
        'filename': filename,
        'vision_data': vision_data,
        'db_records': db_records,
        'issues': issues
    }


def main():
    import argparse
    from dotenv import load_dotenv

    parser = argparse.ArgumentParser(description='验证2025年周报数据')
    parser.add_argument('--week', type=int, help='只验证指定周')
    parser.add_argument('--member', help='只验证指定成员')
    parser.add_argument('--no-cache', action='store_true', help='不使用缓存')
    parser.add_argument('--output', '-o', help='输出报告文件路径')
    parser.add_argument('--api-key', help='Anthropic API密钥')
    args = parser.parse_args()

    # 加载环境变量
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    env_local_path = os.path.join(os.path.dirname(__file__), '..', '.env.local')
    load_dotenv(env_local_path)  # 优先加载本地配置
    load_dotenv(env_path)

    api_key = args.api_key or os.getenv('ANTHROPIC_API_KEY') or os.getenv('CLAUDE_API_KEY')

    if not api_key:
        print("错误: 未设置 ANTHROPIC_API_KEY")
        print("请使用 --api-key 参数或设置环境变量")
        sys.exit(1)

    # 获取所有Word文件
    files = sorted([f for f in os.listdir(WORD_DIR)
                   if f.endswith('.docx') and not f.startswith('~')])

    if args.week:
        files = [f for f in files if get_week_from_filename(f) == args.week]

    print(f"共 {len(files)} 个文件待验证")
    print("=" * 70)

    all_issues = []

    for i, filename in enumerate(files):
        week_num = get_week_from_filename(filename)
        print(f"\n[{i+1}/{len(files)}] Week {week_num}: {filename}")

        try:
            result = validate_week(filename, api_key, use_cache=not args.no_cache)

            if 'error' in result:
                print(f"  错误: {result['error']}")
                continue

            issues = result['issues']
            if args.member:
                issues = [i for i in issues if i['member'] == args.member]

            if issues:
                print(f"  发现 {len(issues)} 个问题:")
                for issue in issues:
                    print(f"    - {issue['member']}.{issue['field']}: {issue['issue_type']}")
                    print(f"      数据库: {issue['db_content_preview']}...")
                    print(f"      视觉:   {issue['vision_content_preview']}...")
                    if 'possibly_from' in issue:
                        print(f"      可能来自: {issue['possibly_from']}")
                all_issues.extend([{**issue, 'week_num': week_num} for issue in issues])
            else:
                print(f"  ✓ 数据正确")

        except Exception as e:
            print(f"  处理失败: {e}")
            import traceback
            traceback.print_exc()

    # 汇总报告
    print("\n" + "=" * 70)
    print("验证汇总报告")
    print("=" * 70)

    if all_issues:
        print(f"\n共发现 {len(all_issues)} 个问题:\n")

        # 按成员分组
        by_member = {}
        for issue in all_issues:
            member = issue['member']
            if member not in by_member:
                by_member[member] = []
            by_member[member].append(issue)

        for member, issues in sorted(by_member.items()):
            print(f"\n【{member}】 {len(issues)} 个问题:")
            for issue in issues:
                print(f"  Week {issue['week_num']} - {issue['field']}: {issue['issue_type']}")
    else:
        print("\n✓ 所有数据验证通过，未发现问题")

    # 保存报告
    if args.output:
        report = {
            'generated_at': datetime.now().isoformat(),
            'total_files': len(files),
            'total_issues': len(all_issues),
            'issues': all_issues
        }
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\n报告已保存到: {args.output}")


if __name__ == '__main__':
    main()
