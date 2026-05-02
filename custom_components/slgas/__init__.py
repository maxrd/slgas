"""The slgas integration."""
from __future__ import annotations

import logging
from datetime import datetime, time

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.event import async_track_time_change
from homeassistant.const import Platform

from .const import (
    DOMAIN,
    CONF_SCHEDULE_TIME,
    SERVICE_EXECUTE_REPORT,
)
from .report_service import SlgasReportService

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BUTTON]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up slgas from a config entry."""
    
    # Initialize report service
    report_service = SlgasReportService(hass, entry)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = report_service

    # Register platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Setup daily schedule
    schedule_str = entry.data.get(CONF_SCHEDULE_TIME, "08:00:00")
    try:
        t = time.fromisoformat(schedule_str)
        
        async def async_scheduled_run(now):
            _LOGGER.info("執行定時瓦斯回報作業")
            await report_service.execute_full_workflow()

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
        _LOGGER.info(f"已設定每日瓦斯回報排程於: {schedule_str}")
    except ValueError:
        _LOGGER.error(f"無效的時間格式: {schedule_str}")

    # Register service
    async def handle_execute_report(call: ServiceCall):
        await report_service.execute_full_workflow()

    hass.services.async_register(DOMAIN, SERVICE_EXECUTE_REPORT, handle_execute_report)

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
