"""Cookie Manager 数据模型"""
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class Cookie(BaseModel):
    """单个 Cookie 数据模型"""
    name: str
    value: str
    domain: str
    path: str = "/"
    expires: Optional[float] = None
    httpOnly: bool = False
    secure: bool = False
    sameSite: Optional[str] = None
    
    def to_netscape_line(self) -> str:
        """转换为 Netscape cookies.txt 格式的一行"""
        return "\t".join([
            self.domain,
            "TRUE" if self.domain.startswith(".") else "FALSE",
            self.path,
            "TRUE" if self.secure else "FALSE",
            str(int(self.expires)) if self.expires else "0",
            self.name,
            self.value
        ])
    
    def is_expired(self) -> bool:
        """检查 cookie 是否已过期"""
        if self.expires is None:
            return False
        return datetime.now().timestamp() > self.expires


class CookieMetadata(BaseModel):
    """Cookie 元数据"""
    last_updated: str = Field(default_factory=lambda: datetime.now().isoformat())
    last_validated: Optional[str] = None
    source: str = "unknown"  # manual_import, auto_refresh
    refresh_count: int = 0
    validation_status: str = "unknown"  # valid, invalid, unknown
    
    def mark_refreshed(self):
        """标记为已刷新"""
        self.last_updated = datetime.now().isoformat()
        self.last_validated = datetime.now().isoformat()
        self.refresh_count += 1
        self.validation_status = "valid"
    
    def mark_validated(self, is_valid: bool):
        """标记验证结果"""
        self.last_validated = datetime.now().isoformat()
        self.validation_status = "valid" if is_valid else "invalid"


class CookieManagerConfig(BaseModel):
    """Cookie Manager 配置"""
    
    # Cookie 存储路径 - 使用用户主目录
    cookie_store_path: Path = Field(
        default_factory=lambda: Path.home() / ".cookies.json",
        description="Cookie 存储文件路径"
    )
    
    # Netscape 格式导出路径（用于 yt-dlp）- 使用用户主目录
    netscape_cookie_path: Path = Field(
        default_factory=lambda: Path.home() / ".cookies",
        description="Netscape 格式 cookie 文件路径（yt-dlp 使用）"
    )
    
    # 刷新间隔（小时）
    refresh_interval_hours: int = Field(
        default=6,
        ge=1,
        le=24,
        description="Cookie 刷新间隔（小时）"
    )
    
    # 浏览器类型
    browser_type: str = Field(
        default="chromium",
        description="浏览器类型：chromium, firefox, webkit"
    )
    
    # 浏览器超时时间（秒）
    browser_timeout: int = Field(
        default=30,
        description="浏览器操作超时时间（秒）"
    )
    
    # 重试配置
    max_retry_count: int = Field(
        default=3,
        description="连续失败最大重试次数"
    )
    
    retry_delay_minutes: int = Field(
        default=5,
        description="重试延迟时间（分钟）"
    )
    
    # PID 文件路径
    pid_file_path: Path = Field(
        default=Path("/tmp/youtube-cookie-manager.pid"),
        description="PID 文件路径"
    )
    
    # 日志级别
    log_level: str = Field(
        default="INFO",
        description="日志级别"
    )
    
    class Config:
        arbitrary_types_allowed = True
    
    @classmethod
    def from_env(cls) -> "CookieManagerConfig":
        """从环境变量加载配置"""
        import os
        from . import config as app_config
        
        return cls(
            cookie_store_path=getattr(app_config, 'COOKIE_STORE_PATH', Path.home() / ".cookies.json"),
            netscape_cookie_path=getattr(app_config, 'COOKIES_FILE', Path.home() / ".cookies"),
            refresh_interval_hours=int(os.getenv("COOKIE_REFRESH_INTERVAL", "6")),
            browser_type=os.getenv("COOKIE_BROWSER_TYPE", "chromium"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )
