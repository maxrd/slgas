"""Button platform for slgas."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, CONF_METER_TYPE, METER_TYPE_WATER, METER_TYPE_ELECTRICITY

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the slgas buttons."""
    report_service = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        SlgasManualReportButton(report_service, entry),
        SlgasOcrOnlyButton(report_service, entry)
    ], True)

class SlgasManualReportButton(ButtonEntity):
    """通用上報按鈕 - 支援瓦斯和水錶"""

    def __init__(self, report_service, entry):
        self._report_service = report_service
        self._entry = entry

        meter_type = entry.data.get(CONF_METER_TYPE, "gas")
        if meter_type == METER_TYPE_WATER:
            self._attr_name = "確認並立即上報水錶度數"
            self._attr_icon = "mdi:water"
        elif meter_type == METER_TYPE_ELECTRICITY:
            self._attr_name = "確認並立即上報電力度數"
            self._attr_icon = "mdi:transmission-tower"
        else:
            self._attr_name = "確認並立即上報瓦斯度數"
            self._attr_icon = "mdi:send-check"

        self._attr_unique_id = f"{entry.entry_id}_manual_report"

    async def async_press(self) -> None:
        """處理按鈕按下事件"""
        await self._report_service.submit_current_degree()


class SlgasOcrOnlyButton(ButtonEntity):
    """僅分析度數按鈕（不提交）"""

    def __init__(self, report_service, entry):
        self._report_service = report_service
        self._entry = entry

        meter_type = entry.data.get(CONF_METER_TYPE, "gas")
        if meter_type == METER_TYPE_WATER:
            self._attr_name = "手動分析水錶度數 (不提交)"
        elif meter_type == METER_TYPE_ELECTRICITY:
            self._attr_name = "手動分析電力度數 (不提交)"
        else:
            self._attr_name = "手動分析度數 (不提交)"
        self._attr_icon = "mdi:camera-retake"

        self._attr_unique_id = f"{entry.entry_id}_ocr_only"

    async def async_press(self) -> None:
        """處理按鈕按下事件"""
        await self._report_service.execute_full_workflow(submit=False)
