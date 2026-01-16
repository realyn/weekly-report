#!/usr/bin/env python3
"""
基于视觉识别的朱迪数据修复脚本
从图片中手动提取的正确数据（已通过Claude视觉模型验证）
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'weekly_report.db')

# 基于视觉识别提取的正确数据（通过Claude视觉模型从Word转换的图片中提取）
# 修复朱迪2025年6月的数据错误（this_week_work 和 next_week_plan 都被错误替换为其他人的内容）
CORRECTIONS = {
    # Week 23 (2025-06-06)
    23: {
        'this_week_work': """1、大河云AI 使用随机策略分流 comfyui 请求
2、大河云AI 测试comfyui接口调用链接断开问题
3、运维 排查服务器无法连接外部网站问题
4、5g消息 修改程序ip绑定、防火墙策略等
5、5g消息 排查卡片消息发送失败的问题
6、新界 排查新闻同步到顶端失败问题""",
        'next_week_plan': """1、文明航空港区 进行项目测试
2、5g消息 跟踪问题解决情况
3、软著申请 准备大河云写作助手项目材料，司法厅答题项目材料"""
    },
    # Week 24 (2025-06-13)
    24: {
        'this_week_work': """1、航空港投资官网 排查产业布局链接修改后未生效问题
2、软著申请 准备司法厅答题项目材料
3、大河云AI 排查图片生成没有图片地址问题
4、大河云AI 图片上传模块，关闭https验证，增加单独异常处理
5、文明航空港区 调试消息模板中部分字段超度超出问题
6、文明航空港区 myAllList接口增加检索功能；修改操作手册
7、运维 检查服务器磁盘状况""",
        'next_week_plan': """1、文明航空港区 测试和修改问题
2、软著申请 准备智能问答项目材料"""
    },
    # Week 25 (2025-06-20)
    25: {
        'this_week_work': """1、软著申请 准备智能问答项目材料
2、航空港投资官网 去除华锐光电栏目；更换首页二维码
3、大河云AI 文生图并发测试；优化文生图提示词拼接兼容性
4、文明航空港区 后端服务开启守护进程，转为生产模式
5、文明航空港区 测试项目；准备演示数据
6、运维 检查服务器磁盘状况""",
        'next_week_plan': """1、文明航空港区 使用操作培训；收集甲方意见"""
    },
    # Week 26 (2025-06-27)
    26: {
        'this_week_work': """1、文明航空港区 使用操作培训；收集甲方意见
2、文明航空港区 设计、实现小程序扫码登录方案
3、文明航空港区 优化小程序登录管理员账号流程；增加一键登录功能
4、司法厅答题 筛选、抽取省内抽奖号码
5、新界 检查新界首页专题配置
6、运维 检查服务器磁盘状况""",
        'next_week_plan': """1、文明航空港区 使用操作培训；收集甲方意见"""
    }
}


def get_zhudi_report(week_num):
    """获取朱迪的周报记录"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT r.id, r.this_week_work, r.next_week_plan
        FROM reports r
        JOIN users u ON r.user_id = u.id
        WHERE r.year = 2025 AND r.week_num = ? AND u.real_name = '朱迪'
    ''', (week_num,))

    row = cursor.fetchone()
    conn.close()

    if row:
        return {'id': row[0], 'this_week_work': row[1], 'next_week_plan': row[2]}
    return None


def apply_fix(report_id, field, value, dry_run=True):
    """应用修复"""
    if dry_run:
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(f'UPDATE reports SET {field} = ? WHERE id = ?', (value, report_id))
    conn.commit()
    conn.close()


def main():
    import sys
    dry_run = '--apply' not in sys.argv

    print(f"运行模式: {'DRY RUN' if dry_run else 'APPLY'}")
    print("=" * 60)

    fixes = []

    for week_num, correct_data in CORRECTIONS.items():
        db_record = get_zhudi_report(week_num)
        if not db_record:
            print(f"Week {week_num}: 朱迪无记录，跳过")
            continue

        # 检查 this_week_work
        if correct_data['this_week_work']:
            db_content = (db_record['this_week_work'] or '')[:50]
            correct_content = correct_data['this_week_work'][:50]

            if db_content != correct_content:
                fixes.append({
                    'week': week_num,
                    'id': db_record['id'],
                    'field': 'this_week_work',
                    'old': db_record['this_week_work'][:60] + '...' if db_record['this_week_work'] else 'NULL',
                    'new': correct_data['this_week_work']
                })
                print(f"\nWeek {week_num} - this_week_work 需要修复")
                print(f"  当前: {db_content}...")
                print(f"  正确: {correct_content}...")

        # 检查 next_week_plan
        if correct_data['next_week_plan']:
            db_content = (db_record['next_week_plan'] or '')[:50]
            correct_content = correct_data['next_week_plan'][:50]

            if db_content != correct_content:
                fixes.append({
                    'week': week_num,
                    'id': db_record['id'],
                    'field': 'next_week_plan',
                    'old': db_record['next_week_plan'][:60] + '...' if db_record['next_week_plan'] else 'NULL',
                    'new': correct_data['next_week_plan']
                })
                print(f"\nWeek {week_num} - next_week_plan 需要修复")
                print(f"  当前: {db_content}...")
                print(f"  正确: {correct_content}...")

    print("\n" + "=" * 60)
    print(f"共发现 {len(fixes)} 处需要修复")

    if fixes and not dry_run:
        for fix in fixes:
            apply_fix(fix['id'], fix['field'], fix['new'], dry_run=False)
            print(f"已修复: Week {fix['week']} - {fix['field']}")
        print(f"\n修复完成")
    elif dry_run and fixes:
        print("\n使用 --apply 参数执行实际修复")


if __name__ == '__main__':
    main()
