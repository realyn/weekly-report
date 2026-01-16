# 项目同步操作指南

## 当前同步状态 (2025-01-16)

### 已同步到 mcp2 的内容

| 内容 | 路径 | 大小 | 方式 |
|------|------|------|------|
| 代码和数据文件 | /home/yn/projects/weekly-report/ | ~3MB | Git |
| 周报验证图片 | .../backend/data/validation_images/ | 36MB | rsync |

### mcp2 服务器信息
- 登录方式: `ssh mcp2`
- 项目路径: `/home/yn/projects/weekly-report`

---

## 回家后操作步骤

### 1. 从 mcp2 拉取代码到家里电脑

```bash
# 方式一：如果家里已有项目（推荐）
cd ~/projects/weekly-report
git pull origin main

# 方式二：如果是新电脑，先克隆
git clone git@github.com:realyn/weekly-report.git
cd weekly-report
```

### 2. 同步验证图片到家里电脑

```bash
# 从 mcp2 拉取图片（约36MB）
rsync -avz --progress mcp2:/home/yn/projects/weekly-report/backend/data/validation_images/ \
  ~/projects/weekly-report/backend/data/validation_images/
```

### 3. 验证同步完整性

```bash
cd ~/projects/weekly-report

# 检查图片目录
ls backend/data/validation_images/ | wc -l
# 应该显示 43 个目录

# 检查数据文件
ls -la backend/data/*.json
# 应该有: all_extracted_data.json, date_mapping.json 等
```

---

## 继续周报数据提取任务

### 当前进度
- ✅ 已提取: 24周数据 (在 all_extracted_data.json)
- ❌ 待提取: 20周数据

### 缺失的周
```
week_03 (2025-01-17), week_04 (2025-01-24)
week_06 (2025-02-08), week_07 (2025-02-14), week_08 (2025-02-21)
week_09 (2025-02-28), week_10 (2025-03-09)
week_12 (2025-03-21), week_13 (2025-03-28), week_14 (2025-04-04)
week_15 (2025-04-11), week_16 (2025-04-18)
week_18 (2025-04-30), week_19 (2025-05-09), week_20 (2025-05-16)
week_21 (2025-05-23), week_22 (2025-05-30), week_23 (2025-06-06)
week_43 (2025-10-24), week_44 (2025-10-31)
```

### 继续提取时的关键点

**重要**: 每次提取数据后必须**立即写入文件保存**，不要让数据只停留在会话上下文中！

建议流程:
1. 提取一周数据
2. 立即追加到 `all_extracted_data.json`
3. 确认保存成功
4. 再提取下一周

### 提取完成后的步骤

```bash
# 1. 运行对比脚本
cd backend
python scripts/batch_extract_and_compare.py --compare --show-stats

# 2. 生成修复SQL
python scripts/batch_extract_and_compare.py --generate-sql

# 3. 查看并执行SQL
cat data/fix_reports.sql
sqlite3 data/weekly_report.db < data/fix_reports.sql

# 4. 验证修复结果
python scripts/batch_extract_and_compare.py --compare --show-stats
```

---

## 双向同步命令参考

### 从本地推送到 mcp2
```bash
# 代码
git push origin main
ssh mcp2 "cd /home/yn/projects/weekly-report && git pull"

# 图片
rsync -avz --progress backend/data/validation_images/ \
  mcp2:/home/yn/projects/weekly-report/backend/data/validation_images/
```

### 从 mcp2 拉取到本地
```bash
# 代码
git pull origin main

# 图片
rsync -avz --progress mcp2:/home/yn/projects/weekly-report/backend/data/validation_images/ \
  backend/data/validation_images/
```

---

## 相关文件说明

| 文件 | 说明 |
|------|------|
| `backend/data/all_extracted_data.json` | 已提取的24周数据 |
| `backend/data/date_mapping.json` | 文件夹名→日期映射 |
| `backend/data/EXTRACTION_README.md` | 详细提取进度记录 |
| `backend/scripts/batch_extract_and_compare.py` | 数据对比脚本 |

---
更新时间: 2025-01-16
