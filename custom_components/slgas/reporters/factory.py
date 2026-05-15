"""Factory for creating reporter instances based on company."""
import logging
from typing import Dict, Any

from .base import BaseReporter

_LOGGER = logging.getLogger(__name__)


class ReporterFactory:
    """動態加載對應的 Reporter"""

    _reporters = {}

    @classmethod
    def register(cls, company: str, reporter_class):
        """註冊一個 Reporter 類別"""
        cls._reporters[company] = reporter_class
        _LOGGER.debug(f"已註冊 Reporter: {company} -> {reporter_class.__name__}")

    @classmethod
    def get_reporter(cls, hass, company: str, config: Dict[str, Any]) -> BaseReporter:
        """根據公司名稱實例化對應的 Reporter"""
        reporter_class = cls._reporters.get(company)
        if not reporter_class:
            raise ValueError(f"不支援的公司: {company}")

        return reporter_class(hass, config)

    @classmethod
    def list_reporters(cls) -> Dict[str, str]:
        """列出所有已註冊的 Reporter"""
        return {company: cls_.__name__ for company, cls_ in cls._reporters.items()}
