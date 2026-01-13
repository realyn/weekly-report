from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
import os
from datetime import datetime
from app.config import get_settings

settings = get_settings()


def set_cell_font(cell, font_name="宋体", font_size=12, bold=False):
    """设置单元格字体"""
    for paragraph in cell.paragraphs:
        for run in paragraph.runs:
            run.font.name = font_name
            run._element.rPr.rFonts.set(qn('w:eastAsia'), font_name)
            run.font.size = Pt(font_size)
            run.font.bold = bold


def generate_weekly_word(summary_data: dict, output_path: str = None) -> str:
    """生成周报Word文档"""
    doc = Document()

    # 标题
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("产品研发部")
    run.font.name = "宋体"
    run._element.rPr.rFonts.set(qn('w:eastAsia'), "宋体")
    run.font.size = Pt(18)
    run.bold = True

    # 日期标题
    year = summary_data["year"]
    week_num = summary_data["week_num"]
    date_range = summary_data["date_range"]

    subtitle = doc.add_paragraph()
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = subtitle.add_run(f"{year}年第{week_num}周工作周报 ({date_range})")
    run.font.name = "宋体"
    run._element.rPr.rFonts.set(qn('w:eastAsia'), "宋体")
    run.font.size = Pt(12)

    # 本周工作表格
    doc.add_paragraph()
    doc.add_paragraph("【本周工作】").runs[0].bold = True

    # 创建表格
    table = doc.add_table(rows=1, cols=5)
    table.style = 'Table Grid'
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    # 表头
    headers = ["项目", "本周工作说明", "执行人", "完成情况", "备注"]
    header_cells = table.rows[0].cells
    for i, header in enumerate(headers):
        header_cells[i].text = header
        set_cell_font(header_cells[i], bold=True)

    # 填充数据
    for report in summary_data.get("reports", []):
        row = table.add_row().cells
        row[0].text = ""
        row[1].text = report.get("this_week_work", "") or ""
        row[2].text = report.get("user_name", "")
        row[3].text = "完成"
        row[4].text = ""
        for cell in row:
            set_cell_font(cell)

    # 下周计划表格
    doc.add_paragraph()
    doc.add_paragraph("【下周计划】").runs[0].bold = True

    table2 = doc.add_table(rows=1, cols=5)
    table2.style = 'Table Grid'
    table2.alignment = WD_TABLE_ALIGNMENT.CENTER

    headers2 = ["项目", "内容说明", "执行人", "起止时间", "备注"]
    header_cells2 = table2.rows[0].cells
    for i, header in enumerate(headers2):
        header_cells2[i].text = header
        set_cell_font(header_cells2[i], bold=True)

    for report in summary_data.get("reports", []):
        row = table2.add_row().cells
        row[0].text = ""
        row[1].text = report.get("next_week_plan", "") or ""
        row[2].text = report.get("user_name", "")
        row[3].text = "周一至周五"
        row[4].text = ""
        for cell in row:
            set_cell_font(cell)

    # 保存文件
    if not output_path:
        os.makedirs(settings.DOCUMENTS_PATH, exist_ok=True)
        output_path = os.path.join(
            settings.DOCUMENTS_PATH,
            f"周报_{year}年第{week_num}周_{datetime.now().strftime('%Y%m%d%H%M%S')}.docx"
        )

    doc.save(output_path)
    return output_path
