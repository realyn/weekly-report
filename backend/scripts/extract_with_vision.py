#!/usr/bin/env python3
"""
使用视觉模型提取周报表格数据
比传统的Word解析更准确，能够正确识别合并单元格中的内容
"""

import os
import sys
import json
import base64
import tempfile
import subprocess
from pathlib import Path

# 配置
SOFFICE_PATH = "/Applications/LibreOffice.app/Contents/MacOS/soffice"
TEAM_MEMBERS = ['杨宁', '翦磊', '朱迪', '张士健', '程志强', '闻世坤', '秦闪闪', '蒋奇朴']


def docx_to_pdf(docx_path: str, output_dir: str) -> str:
    """使用 LibreOffice 将 docx 转换为 PDF"""
    subprocess.run([
        SOFFICE_PATH,
        '--headless',
        '--convert-to', 'pdf',
        '--outdir', output_dir,
        docx_path
    ], check=True, capture_output=True)

    pdf_name = Path(docx_path).stem + '.pdf'
    return os.path.join(output_dir, pdf_name)


def pdf_to_images(pdf_path: str) -> list:
    """将 PDF 转换为图片列表"""
    from pdf2image import convert_from_path

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
    for i, img in enumerate(images):
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
        "this_week_work": "本周工作内容（完整内容）",
        "next_week_plan": "下周工作计划（完整内容）"
    }}
}}

注意事项：
1. 表格可能有合并单元格，请根据视觉位置判断内容归属
2. 本周工作和下周计划可能在不同的表格区域，请区分
3. 只返回JSON，不要其他文字
4. 如果某人的某项内容为空，设为null
5. 内容要完整，不要截断"""
    })

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[{"role": "user", "content": content}]
    )

    # 解析响应
    response_text = response.content[0].text

    # 提取JSON
    try:
        # 尝试直接解析
        return json.loads(response_text)
    except json.JSONDecodeError:
        # 尝试从markdown代码块中提取
        import re
        match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response_text)
        if match:
            return json.loads(match.group(1))
        raise ValueError(f"无法解析响应: {response_text[:200]}")


def extract_from_word(docx_path: str, api_key: str) -> dict:
    """从Word文档提取周报数据"""
    print(f"处理文件: {docx_path}")

    with tempfile.TemporaryDirectory() as tmpdir:
        # 转换为PDF
        print("  转换为PDF...")
        pdf_path = docx_to_pdf(docx_path, tmpdir)

        # 转换为图片
        print("  转换为图片...")
        images = pdf_to_images(pdf_path)
        print(f"  共 {len(images)} 页")

        # 使用Claude提取
        print("  使用视觉模型提取...")
        result = extract_with_claude(images, api_key)

    return result


def main():
    import argparse
    from dotenv import load_dotenv

    parser = argparse.ArgumentParser(description='使用视觉模型提取周报数据')
    parser.add_argument('docx_file', help='Word文档路径')
    parser.add_argument('--output', '-o', help='输出JSON文件路径')
    args = parser.parse_args()

    # 加载环境变量
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    load_dotenv(env_path)

    api_key = os.getenv('ANTHROPIC_API_KEY') or os.getenv('CLAUDE_API_KEY')
    if not api_key:
        print("错误: 未设置 ANTHROPIC_API_KEY 或 CLAUDE_API_KEY")
        sys.exit(1)

    result = extract_from_word(args.docx_file, api_key)

    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\n结果已保存到: {args.output}")
    else:
        print("\n提取结果:")
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
