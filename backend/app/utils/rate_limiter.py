"""登录失败次数限制"""
from datetime import datetime, timedelta
from collections import defaultdict
from threading import Lock

# 配置
MAX_ATTEMPTS = 5  # 最大尝试次数
LOCKOUT_MINUTES = 15  # 锁定时间（分钟）

# 内存存储（生产环境建议用 Redis）
_failed_attempts: dict[str, list[datetime]] = defaultdict(list)
_lock = Lock()


def _cleanup_old_attempts(attempts: list[datetime]) -> list[datetime]:
    """清理过期的失败记录"""
    cutoff = datetime.now() - timedelta(minutes=LOCKOUT_MINUTES)
    return [t for t in attempts if t > cutoff]


def check_rate_limit(identifier: str) -> tuple[bool, int]:
    """
    检查是否超过登录限制
    返回: (是否允许登录, 剩余锁定秒数)
    """
    with _lock:
        attempts = _cleanup_old_attempts(_failed_attempts[identifier])
        _failed_attempts[identifier] = attempts

        if len(attempts) >= MAX_ATTEMPTS:
            oldest = min(attempts)
            unlock_time = oldest + timedelta(minutes=LOCKOUT_MINUTES)
            remaining = (unlock_time - datetime.now()).total_seconds()
            return False, max(0, int(remaining))
        return True, 0


def record_failed_attempt(identifier: str) -> None:
    """记录一次失败的登录尝试"""
    with _lock:
        _failed_attempts[identifier] = _cleanup_old_attempts(_failed_attempts[identifier])
        _failed_attempts[identifier].append(datetime.now())


def clear_failed_attempts(identifier: str) -> None:
    """登录成功后清除失败记录"""
    with _lock:
        _failed_attempts.pop(identifier, None)
