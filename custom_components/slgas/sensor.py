"""Sensor platform for slgas."""
from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the slgas sensors."""
    report_service = hass.data[DOMAIN][entry.entry_id]

    meter_sensor = SlgasMeterSensor(report_service, entry)
    status_sensor = SlgasReportSensor(report_service, entry)

    # 將 meter_sensor 引用存入 report_service，以便流程中更新
    report_service.meter_sensor = meter_sensor

    async_add_entities([meter_sensor, status_sensor], True)


class SlgasMeterSensor(SensorEntity, RestoreEntity):
    """Sensor to track the gas meter reading (supports Energy Dashboard)."""

    def __init__(self, report_service, entry):
        self._report_service = report_service
        self._entry = entry
        cus_no = entry.data.get("cus_no", "")
        self._attr_name = f"瓦斯度數 ({cus_no})"
        self._attr_unique_id = f"{entry.entry_id}_meter"
        self._attr_icon = "mdi:counter"
        self._attr_device_class = SensorDeviceClass.GAS
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_native_unit_of_measurement = UnitOfVolume.CUBIC_METERS
        self._attr_native_value = None

    async def async_added_to_hass(self):
        """Restore last known state on startup."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state and last_state.state not in ("unknown", "unavailable", None):
            try:
                self._attr_native_value = int(last_state.state)
                _LOGGER.info(
                    "已恢復瓦斯度數感測器上次狀態: %s", last_state.state
                )
            except (ValueError, TypeError):
                _LOGGER.warning(
                    "無法恢復瓦斯度數感測器狀態: %s", last_state.state
                )

    def update_meter(self, degree: int):
        """Update the meter reading and trigger state write."""
        self._attr_native_value = degree
        self.async_write_ha_state()

    async def async_update(self):
        """Update is handled via report_service, no polling needed."""
        pass


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
