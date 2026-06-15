"""The slgas integration."""
from __future__ import annotations

import logging
from datetime import datetime, time

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers import entity_registry as er
from homeassistant.const import Platform

from .const import (
    DOMAIN,
    CONF_SCHEDULE_TIME,
    CONF_METER_TYPE,
    METER_TYPE_GAS,
    METER_TYPE_WATER,
    METER_TYPE_ELECTRICITY,
    SERVICE_EXECUTE_REPORT,
    COMPANY_SLGAS,
    COMPANY_SHINHAI,
    COMPANY_WATER_TAIPEI,
    COMPANY_TAIPOWER,
)
from .report_service import SlgasReportService
from .reporters.factory import ReporterFactory
from .reporters.slgas import SlgasReporter
from .reporters.shinhai import ShinhaiReporter
from .reporters.water_taipei import WaterTaipeiReporter
from .reporters.taipower import TaipowerReporter

_LOGGER = logging.getLogger(__name__)

# Register reporters
ReporterFactory.register(COMPANY_SLGAS, SlgasReporter)
ReporterFactory.register(COMPANY_SHINHAI, ShinhaiReporter)
ReporterFactory.register(COMPANY_WATER_TAIPEI, WaterTaipeiReporter)
ReporterFactory.register(COMPANY_TAIPOWER, TaipowerReporter)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BUTTON]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up slgas from a config entry."""
    
    # Initialize report service
    report_service = SlgasReportService(hass, entry)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = report_service

    # Register update listener
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    # Register platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Setup daily schedule (read from merged options + data)
    schedule_str = entry.options.get(CONF_SCHEDULE_TIME, entry.data.get(CONF_SCHEDULE_TIME, "08:00:00"))
    meter_type = entry.data.get(CONF_METER_TYPE, METER_TYPE_GAS)
    meter_label = {METER_TYPE_WATER: "水錶", METER_TYPE_ELECTRICITY: "電力"}.get(meter_type, "瓦斯")

    try:
        t = time.fromisoformat(schedule_str)

        async def async_scheduled_run(now):
            _LOGGER.info(f"執行定時{meter_label}辨識作業 (不自動上報)")
            registry = er.async_get(hass)
            btn_entity_id = registry.async_get_entity_id(
                "button", DOMAIN, f"{entry.entry_id}_ocr_only"
            )
            if btn_entity_id:
                await hass.services.async_call(
                    "button", "press", {"entity_id": btn_entity_id}, blocking=True
                )
            else:
                _LOGGER.warning(f"找不到{meter_label} OCR 按鈕實體，直接執行流程")
                await report_service.execute_full_workflow(submit=False)

        # Track daily time change
        entry.async_on_unload(
            async_track_time_change(
                hass,
                async_scheduled_run,
                hour=t.hour,
                minute=t.minute,
                second=t.second,
            )
        )
        _LOGGER.info(f"已設定每日{meter_label}回報排程於: {schedule_str}")
    except ValueError:
        _LOGGER.error(f"無效的時間格式: {schedule_str}")

    # Register service (only once); runs ALL active entries
    if not hass.services.has_service(DOMAIN, SERVICE_EXECUTE_REPORT):
        async def handle_execute_report(call: ServiceCall):
            submit = call.data.get("submit", True)
            for entry_data in list(hass.data.get(DOMAIN, {}).values()):
                await entry_data.execute_full_workflow(submit=submit)

        hass.services.async_register(DOMAIN, SERVICE_EXECUTE_REPORT, handle_execute_report)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    # Unregister service if no more entries
    if not hass.data.get(DOMAIN):
        hass.services.async_remove(DOMAIN, SERVICE_EXECUTE_REPORT)

    return unload_ok

async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)
