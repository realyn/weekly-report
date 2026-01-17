"""
数据库备份服务
功能：
- 创建 SQLite 数据库备份
- 自动清理过期备份
- 支持手动和定时触发
"""
import shutil
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# 配置
BACKUP_DIR = Path(__file__).parent.parent.parent / "data" / "backups"
DB_PATH = Path(__file__).parent.parent.parent / "data" / "weekly_report.db"
RETENTION_DAYS = 30  # 备份保留天数


async def create_backup() -> Optional[Path]:
    """
    创建数据库备份

    Returns:
        备份文件路径，失败返回 None
    """
    try:
        # 确保备份目录存在
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)

        # 检查源数据库是否存在
        if not DB_PATH.exists():
            logger.error(f"数据库文件不存在: {DB_PATH}")
            return None

        # 生成备份文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = BACKUP_DIR / f"weekly_report_backup_{timestamp}.db"

        # 执行备份（使用 copy2 保留元数据）
        shutil.copy2(DB_PATH, backup_file)
        logger.info(f"数据库备份完成: {backup_file}")

        # 清理旧备份
        await cleanup_old_backups()

        return backup_file

    except Exception as e:
        logger.error(f"数据库备份失败: {e}")
        return None


async def cleanup_old_backups() -> int:
    """
    清理超过保留期限的备份

    Returns:
        删除的备份文件数量
    """
    if not BACKUP_DIR.exists():
        return 0

    cutoff = datetime.now() - timedelta(days=RETENTION_DAYS)
    deleted_count = 0

    for backup in BACKUP_DIR.glob("weekly_report_backup_*.db"):
        try:
            # 从文件名解析时间戳
            ts_str = backup.stem.replace("weekly_report_backup_", "")
            file_time = datetime.strptime(ts_str, "%Y%m%d_%H%M%S")

            if file_time < cutoff:
                backup.unlink()
                deleted_count += 1
                logger.info(f"删除过期备份: {backup.name}")

        except ValueError:
            # 文件名格式不符，跳过
            logger.warning(f"跳过非标准备份文件: {backup.name}")
            continue

    if deleted_count > 0:
        logger.info(f"清理完成，共删除 {deleted_count} 个过期备份")

    return deleted_count


async def list_backups() -> list[dict]:
    """
    列出所有备份文件

    Returns:
        备份文件信息列表
    """
    if not BACKUP_DIR.exists():
        return []

    backups = []
    for backup in sorted(BACKUP_DIR.glob("weekly_report_backup_*.db"), reverse=True):
        try:
            ts_str = backup.stem.replace("weekly_report_backup_", "")
            file_time = datetime.strptime(ts_str, "%Y%m%d_%H%M%S")
            size_mb = backup.stat().st_size / (1024 * 1024)

            backups.append({
                "filename": backup.name,
                "path": str(backup),
                "created_at": file_time.isoformat(),
                "size_mb": round(size_mb, 2)
            })
        except ValueError:
            continue

    return backups


async def get_backup_stats() -> dict:
    """
    获取备份统计信息

    Returns:
        统计信息字典
    """
    backups = await list_backups()
    total_size = sum(b["size_mb"] for b in backups)

    return {
        "backup_count": len(backups),
        "total_size_mb": round(total_size, 2),
        "retention_days": RETENTION_DAYS,
        "backup_dir": str(BACKUP_DIR),
        "latest_backup": backups[0] if backups else None
    }
