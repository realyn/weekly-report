# 周报数据提取与验证说明

## 项目目标

验证2025年全部周报数据的完整性和准确性，从原始图片中提取数据并与数据库对比修复。

## 当前进展

### 已完成
1. **日期映射建立** - 43周的文件夹名与实际日期映射
2. **图片准备** - 所有周报图片已复制到验证目录
3. **数据提取完成** - 已从图片中提取全部44周数据
   - 原有24周数据（all_extracted_data.json）
   - 新提取20周数据（2025-01-16通过图片OCR提取）

### 待完成
1. 整合20周新数据到 all_extracted_data.json
2. 与数据库对比找出差异
3. 生成修复SQL并执行
4. 验证修复结果

## 数据提取状态

| 状态 | 周数 | 说明 |
|------|------|------|
| ✅ 完整 | 44周 | 全部成员数据已提取 |
| ⚠️ 待整合 | 20周 | 新提取数据待合并 |

### 原有数据（24周）
- 第1-2周 (2025-01-03, 2025-01-10)
- 第24-26周 (2025-06-13 ~ 2025-06-27)
- 第29-38周 (2025-07-18 ~ 2025-09-19)
- 第40周 (2025-09-30)
- 第42周, 第45-48周, 第50周, 第52周

### 新提取数据（20周，2025-01-16完成）
- week_03 (2025-01-17), week_04 (2025-01-24) - 7人
- week_06 (2025-02-08), week_07 (2025-02-14), week_08 (2025-02-21) - 7人
- week_09 (2025-02-28), week_10 (2025-03-09) - 7人
- week_12 (2025-03-21), week_13 (2025-03-28), week_14 (2025-04-04), week_15 (2025-04-11), week_16 (2025-04-18) - 7人
- week_18 (2025-04-30), week_19 (2025-05-09), week_20 (2025-05-16), week_21 (2025-05-23), week_22 (2025-05-30), week_23 (2025-06-06) - 7人
- week_43 (2025-10-24), week_44 (2025-10-31) - 8人

## 相关文件位置

### 源数据
```
/Users/yn/Documents/工作/工时/每周总结/
├── week_01/ ~ week_52/     # 原始周报图片目录
```

### 验证用图片（已复制）
```
/Users/yn/projects/weekly-report/backend/data/validation_images/
├── week_01/ ~ week_52/     # 43个周的图片副本
│   ├── page_1.png
│   ├── page_2.png
│   └── page_3.png (部分周有page_4.png)
```

### 提取数据文件
```
/Users/yn/projects/weekly-report/backend/data/
├── date_mapping.json           # 文件夹名→日期映射（43周）
├── extracted_raw_data.json     # 早期提取的数据（week_01, week_02）
├── all_extracted_data.json     # 整合后的提取数据（28周）
└── validation_progress.json    # 验证进度记录
```

### Subagent缓存（包含已提取的原始数据）
```
~/.claude/projects/-Users-yn-projects/0ae868a4-1326-4fb3-a669-ef6728f9a021/
├── subagents/
│   ├── agent-a248f13.jsonl    # week_12-16 数据
│   ├── agent-a6ddb2c.jsonl    # week_24-31 数据（完整）
│   ├── agent-a7c1afd.jsonl    # week_09-10 数据
│   ├── agent-a809f53.jsonl    # week_40-52 数据
│   ├── agent-aa0814e.jsonl    # week_06-08 数据
│   ├── agent-aa5015f.jsonl    # week_32-38 数据（完整）
│   ├── agent-abe3e20.jsonl    # week_18-23 数据
│   └── agent-adf8180.jsonl    # week_03-04 数据
```

### 脚本文件
```
/Users/yn/projects/weekly-report/backend/scripts/
└── batch_extract_and_compare.py  # 批量对比脚本
```

## 数据格式说明

### date_mapping.json
```json
{
  "mapping": {
    "week_01": {"date": "2025-01-03", "display": "1月3日"},
    ...
  }
}
```

### all_extracted_data.json
```json
{
  "data": {
    "2025-01-03": {
      "iso_week": 1,
      "folder": "week_01",
      "members": {
        "杨宁": {
          "this_week_work": "...",
          "next_week_plan": "..."
        },
        ...
      }
    }
  }
}
```

## 团队成员
杨宁、翦磊、朱迪、张士健、程志强、闻世坤、秦闪闪、蒋奇朴（共8人）

注：蒋奇朴从第29周（2025-07-18）开始出现在周报中，之前周报仅7人

## 下一步操作

1. **整合新提取数据**（当前步骤）
   ```bash
   # 将20周新数据合并到 all_extracted_data.json
   ```

2. **运行对比脚本**
   ```bash
   cd /Users/yn/projects/weekly-report/backend
   python scripts/batch_extract_and_compare.py --compare --show-stats
   ```

3. **生成修复SQL**
   ```bash
   python scripts/batch_extract_and_compare.py --generate-sql
   # SQL将保存到 data/fix_reports.sql
   ```

4. **验证修复结果**
   ```bash
   python scripts/batch_extract_and_compare.py --compare --show-stats
   # 确认差异数为0
   ```

## 注意事项

1. **周次计算**：以日期为准，使用ISO周次标准计算，不依赖图片中显示的周号
2. **文件夹名不可靠**：week_xx文件夹名与实际周次可能不一致
3. **调休影响**：部分周可能因节假日调休导致周报日期不规律
4. **成员变动**：蒋奇朴于第29周(2025-07-18)加入，之前周报仅含7位成员

---
更新时间：2025-01-16 (数据提取完成)
