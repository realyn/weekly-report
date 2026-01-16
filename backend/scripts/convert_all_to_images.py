#!/usr/bin/env python3
"""
批量将2025年Word文档转换为图片，供人工/Claude Code视觉验证
"""

import os
import subprocess
from pathlib import Path
from datetime import datetime
import re

SOFFICE_PATH = "/Applications/LibreOffice.app/Contents/MacOS/soffice"
WORD_DIR = '/Users/yn/Documents/工作/工时/2025/'
OUTPUT_DIR = '/tmp/weekly_report_2025_images'


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


def convert_docx_to_images(docx_path, output_subdir):
    """将Word转换为图片"""
    from pdf2image import convert_from_path
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        # Word -> PDF
        subprocess.run([
            SOFFICE_PATH,
            '--headless',
            '--convert-to', 'pdf',
            '--outdir', tmpdir,
            docx_path
        ], check=True, capture_output=True)

        pdf_name = Path(docx_path).stem + '.pdf'
        pdf_path = os.path.join(tmpdir, pdf_name)

        # PDF -> Images
        images = convert_from_path(pdf_path, dpi=150)

        os.makedirs(output_subdir, exist_ok=True)
        saved_paths = []
        for i, img in enumerate(images):
            img_path = os.path.join(output_subdir, f'page_{i+1}.png')
            img.save(img_path, 'PNG')
            saved_paths.append(img_path)

        return saved_paths


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    files = sorted([f for f in os.listdir(WORD_DIR)
                   if f.endswith('.docx') and not f.startswith('~')])

    print(f"共 {len(files)} 个文件待转换")
    print(f"输出目录: {OUTPUT_DIR}")
    print("=" * 60)

    for i, filename in enumerate(files):
        week_num = get_week_from_filename(filename)
        if week_num is None:
            print(f"[{i+1}/{len(files)}] 跳过: {filename} (无法解析周数)")
            continue

        output_subdir = os.path.join(OUTPUT_DIR, f'week_{week_num:02d}')

        # 检查是否已转换
        if os.path.exists(output_subdir) and os.listdir(output_subdir):
            print(f"[{i+1}/{len(files)}] Week {week_num}: 已存在，跳过")
            continue

        print(f"[{i+1}/{len(files)}] Week {week_num}: {filename}")
        try:
            doc_path = os.path.join(WORD_DIR, filename)
            paths = convert_docx_to_images(doc_path, output_subdir)
            print(f"  -> 生成 {len(paths)} 张图片")
        except Exception as e:
            print(f"  -> 错误: {e}")

    print("\n" + "=" * 60)
    print("转换完成！")
    print(f"图片保存在: {OUTPUT_DIR}")


if __name__ == '__main__':
    main()
