"""Button platform for slgas."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

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
    """Button to manually trigger the full gas report (OCR + Submit)."""

    def __init__(self, report_service, entry):
        self._report_service = report_service
        self._entry = entry
        self._attr_name = "確認並立即上報瓦斯度數"
        self._attr_unique_id = f"{entry.entry_id}_manual_report"
        self._attr_icon = "mdi:send-check"

    async def async_press(self) -> None:
        """Handle the button press."""
        await self._report_service.execute_full_workflow(submit=True)

class SlgasOcrOnlyButton(ButtonEntity):
    """Button to manually trigger only the OCR analysis."""

    def __init__(self, report_service, entry):
        self._report_service = report_service
        self._entry = entry
        self._attr_name = "手動分析度數 (不提交)"
        self._attr_unique_id = f"{entry.entry_id}_ocr_only"
        self._attr_icon = "mdi:camera-retake"

    async def async_press(self) -> None:
        """Handle the button press."""
        await self._report_service.execute_full_workflow(submit=False)
