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
    async_add_entities([SlgasManualReportButton(report_service, entry)], True)

class SlgasManualReportButton(ButtonEntity):
    """Button to manually trigger the gas report."""

    def __init__(self, report_service, entry):
        self._report_service = report_service
        self._entry = entry
        self._attr_name = "立即回報瓦斯度數"
        self._attr_unique_id = f"{entry.entry_id}_manual_report"
        self._attr_icon = "mdi:send-check"

    async def async_press(self) -> None:
        """Handle the button press."""
        await self._report_service.execute_full_workflow()
