"""Config flow for slgas integration."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector
import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN,
    CONF_CUS_NO,
    CONF_CUS_NAME,
    CONF_CUS_PHONE,
    CONF_CAMERA_ENTITY,
    CONF_TEXT_ENTITY,
    CONF_SCHEDULE_TIME,
)

class SlgasConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for slgas."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # Check if already configured
            await self.async_set_unique_id(user_input[CONF_CUS_NO])
            self._abort_if_unique_id_configured()
            
            return self.async_create_entry(
                title=f"瓦斯自動回報 ({user_input[CONF_CUS_NO]})",
                data=user_input,
            )

        data_schema = vol.Schema({
            vol.Required(CONF_CUS_NO): str,
            vol.Required(CONF_CUS_NAME): str,
            vol.Required(CONF_CUS_PHONE): str,
            vol.Required(CONF_CAMERA_ENTITY): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="camera")
            ),
            vol.Required(CONF_TEXT_ENTITY): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="input_text")
            ),
            vol.Required(CONF_SCHEDULE_TIME, default="08:00:00"): selector.TimeSelector(),
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )
