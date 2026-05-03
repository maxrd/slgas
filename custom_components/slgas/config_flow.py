"""Config flow for slgas integration."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
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
    CONF_NOTIFY_SCRIPT,
    CONF_HISTORY_DAYS,
    CONF_PROMPT,
    CONF_OCR_SOURCE,
    CONF_DEGREE_ENTITY,
    OCR_SOURCE_GOOGLE_AI,
    OCR_SOURCE_EXTERNAL,
    DEFAULT_HISTORY_DAYS,
    DEFAULT_PROMPT,
)

OCR_SOURCE_OPTIONS = [
    selector.SelectOptionDict(value=OCR_SOURCE_GOOGLE_AI, label="Google AI (攝影機 + AI 辨識)"),
    selector.SelectOptionDict(value=OCR_SOURCE_EXTERNAL, label="外部實體 (input_text / sensor)"),
]


class SlgasConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for slgas."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return SlgasOptionsFlowHandler()

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
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
            vol.Required(CONF_OCR_SOURCE, default=OCR_SOURCE_GOOGLE_AI): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=OCR_SOURCE_OPTIONS,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional(CONF_CAMERA_ENTITY): selector.EntitySelector(
                {"domain": "camera"}
            ),
            vol.Optional(CONF_DEGREE_ENTITY): selector.EntitySelector(
                {"domain": ["input_text", "sensor"]}
            ),
            vol.Required(CONF_TEXT_ENTITY): selector.EntitySelector(
                {"domain": "input_text"}
            ),
            vol.Required(CONF_SCHEDULE_TIME, default="08:00:00"): selector.TimeSelector(),
            vol.Optional(CONF_NOTIFY_SCRIPT): selector.EntitySelector(
                {"domain": "script"}
            ),
            vol.Optional(CONF_HISTORY_DAYS, default=DEFAULT_HISTORY_DAYS): selector.NumberSelector(
                {"min": 1, "max": 365, "step": 1, "mode": "box"}
            ),
            vol.Optional(CONF_PROMPT, default=DEFAULT_PROMPT): selector.TextSelector(
                {"multiline": True}
            ),
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )


class SlgasOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for slgas."""

    def __init__(self):
        """Initialize options flow."""
        pass

    async def async_step_init(self, user_input=None):
        """Redirect to user step."""
        return await self.async_step_user(user_input)

    async def async_step_user(self, user_input=None):
        """Manage the options."""
        errors = {}
        config = {**self.config_entry.data, **self.config_entry.options}

        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        schema = {
            vol.Required(
                CONF_CUS_NO, default=config.get(CONF_CUS_NO, "")
            ): str,
            vol.Required(
                CONF_CUS_NAME, default=config.get(CONF_CUS_NAME, "")
            ): str,
            vol.Required(
                CONF_CUS_PHONE, default=config.get(CONF_CUS_PHONE, "")
            ): str,
            vol.Required(
                CONF_OCR_SOURCE, default=config.get(CONF_OCR_SOURCE, OCR_SOURCE_GOOGLE_AI)
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=OCR_SOURCE_OPTIONS,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional(
                CONF_CAMERA_ENTITY, default=config.get(CONF_CAMERA_ENTITY, "")
            ): selector.EntitySelector(
                {"domain": "camera"}
            ),
            vol.Optional(
                CONF_DEGREE_ENTITY, default=config.get(CONF_DEGREE_ENTITY, "")
            ): selector.EntitySelector(
                {"domain": ["input_text", "sensor"]}
            ),
            vol.Required(
                CONF_TEXT_ENTITY, default=config.get(CONF_TEXT_ENTITY, "")
            ): selector.EntitySelector(
                {"domain": "input_text"}
            ),
            vol.Required(
                CONF_SCHEDULE_TIME, default=config.get(CONF_SCHEDULE_TIME, "08:00:00")
            ): selector.TimeSelector(),
            vol.Optional(
                CONF_NOTIFY_SCRIPT, default=config.get(CONF_NOTIFY_SCRIPT, "")
            ): selector.EntitySelector(
                {"domain": "script"}
            ),
            vol.Optional(
                CONF_HISTORY_DAYS, default=config.get(CONF_HISTORY_DAYS, DEFAULT_HISTORY_DAYS)
            ): selector.NumberSelector(
                {"min": 1, "max": 365, "step": 1, "mode": "box"}
            ),
            vol.Optional(
                CONF_PROMPT, default=config.get(CONF_PROMPT, DEFAULT_PROMPT)
            ): selector.TextSelector(
                {"multiline": True}
            ),
        }

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(schema),
            errors=errors,
        )
