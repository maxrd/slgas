"""Base reporter class defining the standard interface."""
from abc import ABC, abstractmethod
from typing import Dict, Any
import logging

_LOGGER = logging.getLogger(__name__)


class BaseReporter(ABC):
    """所有上報模組的標準接口"""

    def __init__(self, hass, config: Dict[str, Any]):
        self.hass = hass
        self.config = config
        self.last_status = "未初始化"

    @abstractmethod
    async def submit(self, degree: str, image_path: str = None) -> bool:
        """上報度數到遠端伺服器

        Args:
            degree: 度數 (字串格式)
            image_path: 可選的圖片路徑

        Returns:
            bool: 成功為 True，失敗為 False
        """
        pass

    def validate_config(self) -> bool:
        """驗證配置的完整性"""
        raise NotImplementedError

    def get_required_fields(self) -> list:
        """回傳此模組需要的設定欄位清單"""
        raise NotImplementedError
