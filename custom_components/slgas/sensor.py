"""Sensor platform for slgas."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the slgas sensors."""
    report_service = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([SlgasReportSensor(report_service, entry)], True)

class SlgasReportSensor(SensorEntity):
    """Sensor to track the last reporting status."""

    def __init__(self, report_service, entry):
        self._report_service = report_service
        self._entry = entry
        self._attr_name = f"瓦斯回報狀態 ({entry.data.get('cus_no')})"
        self._attr_unique_id = f"{entry.entry_id}_status"
        self._attr_icon = "mdi:gas-burner"

    @property
    def native_value(self):
        """Return the last status."""
        return self._report_service.last_status

    @property
    def extra_state_attributes(self):
        """Return history records."""
        return {
            "history": self._report_service.history
        }

    async def async_update(self):
        """Update is handled via the service, no polling needed."""
        pass
