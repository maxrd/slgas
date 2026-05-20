"""Taipower (台灣電力) reporter - stub implementation."""
import logging
from .base import BaseReporter

_LOGGER = logging.getLogger(__name__)

TAIPOWER_REPORT_URL = "https://www.taipower.com.tw/fake-report"


class TaipowerReporter(BaseReporter):
    """台灣電力公司上報模組 (尚未實作，預留介面)"""

    async def submit(self, degree: str, image_path: str = None) -> bool:
        taipower_id = self.config.get("taipower_id", "")
        _LOGGER.info(
            "台電上報 (stub) - 用戶編號: %s, 度數: %s, URL: %s",
            taipower_id, degree, TAIPOWER_REPORT_URL,
        )
        self.last_status = "尚未實作"
        return True

    def validate_config(self) -> bool:
        return bool(self.config.get("taipower_id"))

    def get_required_fields(self) -> list:
        return ["taipower_id"]
