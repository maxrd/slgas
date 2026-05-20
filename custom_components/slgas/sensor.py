"""Sensor platform for slgas."""
from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfVolume, UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN, CONF_METER_TYPE, METER_TYPE_WATER, METER_TYPE_GAS, METER_TYPE_ELECTRICITY

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the slgas sensors."""
    report_service = hass.data[DOMAIN][entry.entry_id]

    meter_type = entry.data.get(CONF_METER_TYPE, "gas")
    meter_sensor = UniversalMeterSensor(report_service, entry, meter_type)
    status_sensor = SlgasReportSensor(report_service, entry)

    # 將感測器引用存入 report_service，以便流程中主動推送狀態
    report_service.meter_sensor = meter_sensor
    report_service.status_sensor = status_sensor

    async_add_entities([meter_sensor, status_sensor], True)


class UniversalMeterSensor(SensorEntity, RestoreEntity):
    """通用度數感應器 - 支援瓦斯和水錶 (能源面板支援)"""

    def __init__(self, report_service, entry, meter_type="gas"):
        self._report_service = report_service
        self._entry = entry
        self._meter_type = meter_type

        # 根據 meter_type 設定名稱和圖示
        if meter_type == METER_TYPE_WATER:
            water_no = entry.data.get("water_no", "")
            self._attr_name = f"水錶度數 ({water_no})"
            self._attr_icon = "mdi:water"
            self._attr_device_class = SensorDeviceClass.WATER
            self._attr_native_unit_of_measurement = UnitOfVolume.CUBIC_METERS
        elif meter_type == METER_TYPE_ELECTRICITY:
            taipower_id = entry.data.get("taipower_id", "")
            self._attr_name = f"電力度數 ({taipower_id})"
            self._attr_icon = "mdi:transmission-tower"
            self._attr_device_class = SensorDeviceClass.ENERGY
            self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        elif meter_type == METER_TYPE_GAS:
            cus_no = entry.data.get("cus_no", "")
            self._attr_name = f"瓦斯度數 ({cus_no})"
            self._attr_icon = "mdi:counter"
            self._attr_device_class = SensorDeviceClass.GAS
            self._attr_native_unit_of_measurement = UnitOfVolume.CUBIC_METERS
        else:
            self._attr_name = f"度數 ({entry.entry_id[:8]})"
            self._attr_icon = "mdi:counter"
            self._attr_device_class = SensorDeviceClass.GAS
            self._attr_native_unit_of_measurement = UnitOfVolume.CUBIC_METERS

        self._attr_unique_id = f"{entry.entry_id}_meter"
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_native_value = None

    async def async_added_to_hass(self):
        """啟動時恢復上次狀態"""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state and last_state.state not in ("unknown", "unavailable", None):
            try:
                self._attr_native_value = int(last_state.state)
                if self._meter_type == METER_TYPE_WATER:
                    meter_type_str = "水錶"
                elif self._meter_type == METER_TYPE_ELECTRICITY:
                    meter_type_str = "電力"
                else:
                    meter_type_str = "瓦斯"
                _LOGGER.info(
                    f"已恢復{meter_type_str}度數感測器上次狀態: {last_state.state}"
                )
            except (ValueError, TypeError):
                _LOGGER.warning(
                    f"無法恢復度數感測器狀態: {last_state.state}"
                )

    def update_meter(self, degree: int):
        """由 report_service 呼叫更新度數"""
        self._attr_native_value = degree
        self.async_write_ha_state()

    async def async_update(self):
        """更新由 report_service 處理，無需輪詢"""
        pass


# 向後相容性別名
SlgasMeterSensor = UniversalMeterSensor


class SlgasReportSensor(SensorEntity):
    """感應器追蹤最後回報狀態"""

    def __init__(self, report_service, entry):
        self._report_service = report_service
        self._entry = entry
        meter_type = entry.data.get("meter_type", "gas")

        if meter_type == METER_TYPE_WATER:
            water_no = entry.data.get("water_no", "")
            status_name = f"水錶回報狀態 ({water_no})"
            icon = "mdi:water"
        elif meter_type == METER_TYPE_ELECTRICITY:
            taipower_id = entry.data.get("taipower_id", "")
            status_name = f"電力回報狀態 ({taipower_id})"
            icon = "mdi:transmission-tower"
        else:
            cus_no = entry.data.get("cus_no", "")
            status_name = f"瓦斯回報狀態 ({cus_no})"
            icon = "mdi:gas-burner"

        self._attr_name = status_name
        self._attr_unique_id = f"{entry.entry_id}_status"
        self._attr_icon = icon

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
