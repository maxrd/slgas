"""Config flow for slgas integration."""
from __future__ import annotations

import re
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    CONF_METER_TYPE,
    CONF_COMPANY,
    CONF_CUS_NO,
    CONF_CUS_NAME,
    CONF_CUS_PHONE,
    CONF_WATER_NO,
    CONF_APPLICANT_NAME,
    CONF_EMAIL,
    CONF_PHONE,
    CONF_TAIPOWER_ID,
    CONF_CAMERA_ENTITY,
    CONF_TEXT_ENTITY,
    CONF_SCHEDULE_TIME,
    CONF_NOTIFY_SCRIPT,
    CONF_NOTIFY_TITLE,
    CONF_HISTORY_DAYS,
    CONF_PROMPT,
    CONF_OCR_SOURCE,
    CONF_DEGREE_ENTITY,
    METER_TYPE_GAS,
    METER_TYPE_WATER,
    METER_TYPE_ELECTRICITY,
    COMPANY_SLGAS,
    COMPANY_WATER_TAIPEI,
    COMPANY_TAIPOWER,
    OCR_SOURCE_GOOGLE_AI,
    OCR_SOURCE_EXTERNAL,
    DEFAULT_HISTORY_DAYS,
    DEFAULT_NOTIFY_TITLE_GAS,
    DEFAULT_NOTIFY_TITLE_WATER,
    DEFAULT_NOTIFY_TITLE_ELECTRICITY,
    DEFAULT_PROMPT_GAS,
    DEFAULT_PROMPT_WATER,
    DEFAULT_PROMPT_ELECTRICITY,
)


class SlgasConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """SLGAS 整合設定流 - 支援瓦斯和水錶"""

    VERSION = 1

    def __init__(self):
        """初始化設定流"""
        self._user_input: dict = {}
        self.meter_type: str | None = None
        self.company: str | None = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """取得此處理器的選項流"""
        return SlgasOptionsFlowHandler()

    async def async_step_user(self, user_input=None):
        """步驟 1: 選擇類型 (瓦斯/水)"""
        errors = {}

        if user_input is not None:
            self.meter_type = user_input.get(CONF_METER_TYPE)
            self._user_input[CONF_METER_TYPE] = self.meter_type
            return await self.async_step_company()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_METER_TYPE): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(value=METER_TYPE_GAS, label="⛽ 瓦斯"),
                            selector.SelectOptionDict(value=METER_TYPE_WATER, label="💧 水錶"),
                            selector.SelectOptionDict(value=METER_TYPE_ELECTRICITY, label="⚡ 電力"),
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            }),
            errors=errors,
            description_placeholders={"step_count": "6"},
        )

    async def async_step_company(self, user_input=None):
        """步驟 2: 選擇公司 (根據類型動態過濾)"""
        errors = {}

        if user_input is not None:
            self.company = user_input.get(CONF_COMPANY)
            self._user_input[CONF_COMPANY] = self.company
            return await self.async_step_basic_info()

        # 根據 meter_type 過濾公司清單
        if self.meter_type == METER_TYPE_WATER:
            companies = {
                COMPANY_WATER_TAIPEI: "台灣自來水",
            }
        elif self.meter_type == METER_TYPE_ELECTRICITY:
            companies = {
                COMPANY_TAIPOWER: "台灣電力公司",
            }
        else:  # GAS
            companies = {
                COMPANY_SLGAS: "欣隆天然瓦斯",
            }

        return self.async_show_form(
            step_id="company",
            data_schema=vol.Schema({
                vol.Required(CONF_COMPANY): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(value=k, label=v)
                            for k, v in companies.items()
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            }),
            errors=errors,
        )

    async def async_step_basic_info(self, user_input=None):
        """步驟 3: 基本資訊 (動態欄位)"""
        errors = {}

        if user_input is not None:
            # 驗證欄位
            if self.company == COMPANY_WATER_TAIPEI:
                # 驗證水號格式 (XXX-XXX)
                water_no = user_input.get(CONF_WATER_NO, "")
                if water_no and not re.match(r"^\d{1,3}-\d{1,3}$", water_no):
                    errors[CONF_WATER_NO] = "invalid_water_no_format"
                # 驗證電郵格式
                email = user_input.get(CONF_EMAIL, "")
                if email and email.strip():
                    if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
                        errors[CONF_EMAIL] = "invalid_email"

            if not errors:
                self._user_input.update(user_input)
                return await self.async_step_ocr_config()

        # 根據公司動態生成欄位
        schema_dict = {}

        if self.company == COMPANY_WATER_TAIPEI:
            schema_dict = {
                vol.Required(CONF_APPLICANT_NAME): str,
                vol.Required(CONF_WATER_NO): str,
                vol.Required(CONF_PHONE): str,
                vol.Required(CONF_EMAIL): str,
            }
        elif self.company == COMPANY_TAIPOWER:
            schema_dict = {
                vol.Required(CONF_TAIPOWER_ID): str,
            }
        else:  # SLGAS
            schema_dict = {
                vol.Required(CONF_CUS_NO): str,
                vol.Required(CONF_CUS_NAME): str,
                vol.Required(CONF_CUS_PHONE): str,
            }

        return self.async_show_form(
            step_id="basic_info",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
        )

    async def async_step_ocr_config(self, user_input=None):
        """步驟 4: OCR 設定 (攝影機 + 提示詞)"""
        errors = {}

        if user_input is not None:
            ocr_source = user_input.get(CONF_OCR_SOURCE, OCR_SOURCE_GOOGLE_AI)

            # 驗證必填欄位
            if ocr_source == OCR_SOURCE_GOOGLE_AI:
                if not user_input.get(CONF_CAMERA_ENTITY):
                    errors[CONF_CAMERA_ENTITY] = "camera_required"
            else:
                if not user_input.get(CONF_DEGREE_ENTITY):
                    errors[CONF_DEGREE_ENTITY] = "degree_entity_required"

            if not errors:
                self._user_input.update(user_input)
                return await self.async_step_advanced()

        # 根據 meter_type 推薦 prompt
        if self.meter_type == METER_TYPE_WATER:
            default_prompt = DEFAULT_PROMPT_WATER
        elif self.meter_type == METER_TYPE_ELECTRICITY:
            default_prompt = DEFAULT_PROMPT_ELECTRICITY
        else:
            default_prompt = DEFAULT_PROMPT_GAS

        ocr_source = self._user_input.get(CONF_OCR_SOURCE, OCR_SOURCE_GOOGLE_AI)

        # 根據現有的 ocr_source 選擇顯示不同的欄位
        schema_dict = {
            vol.Required(
                CONF_OCR_SOURCE, default=ocr_source
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectOptionDict(
                            value=OCR_SOURCE_GOOGLE_AI,
                            label="Google AI (攝影機 + AI 辨識)"
                        ),
                        selector.SelectOptionDict(
                            value=OCR_SOURCE_EXTERNAL,
                            label="外部實體 (input_text / sensor)"
                        ),
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            )
        }

        if ocr_source == OCR_SOURCE_GOOGLE_AI:
            schema_dict[vol.Required(
                CONF_CAMERA_ENTITY,
                default=self._user_input.get(CONF_CAMERA_ENTITY, "")
            )] = selector.EntitySelector({"domain": "camera"})
            schema_dict[vol.Required(
                CONF_PROMPT,
                default=self._user_input.get(CONF_PROMPT, default_prompt)
            )] = selector.TextSelector({"multiline": True})
        else:
            schema_dict[vol.Required(
                CONF_DEGREE_ENTITY,
                default=self._user_input.get(CONF_DEGREE_ENTITY, "")
            )] = selector.EntitySelector(
                {"domain": ["input_text", "sensor"]}
            )

        return self.async_show_form(
            step_id="ocr_config",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
        )

    async def async_step_advanced(self, user_input=None):
        """步驟 6: 進階選項"""
        errors = {}

        if user_input is not None:
            full_data = {**self._user_input, **user_input}

            # 設定唯一 ID
            if self.meter_type == METER_TYPE_WATER:
                unique_id = full_data.get(CONF_WATER_NO, "water")
                title = f"💧 水錶 ({unique_id})"
            elif self.meter_type == METER_TYPE_ELECTRICITY:
                unique_id = full_data.get(CONF_TAIPOWER_ID, "electricity")
                title = f"⚡ 電力 ({unique_id})"
            else:
                unique_id = full_data.get(CONF_CUS_NO, "gas")
                title = f"⛽ 瓦斯 ({unique_id})"

            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=title,
                data=full_data,
            )

        config = {**self._user_input}

        # 根據 meter_type 設定預設通知標題
        if self.meter_type == METER_TYPE_WATER:
            default_notify_title = DEFAULT_NOTIFY_TITLE_WATER
        elif self.meter_type == METER_TYPE_ELECTRICITY:
            default_notify_title = DEFAULT_NOTIFY_TITLE_ELECTRICITY
        else:
            default_notify_title = DEFAULT_NOTIFY_TITLE_GAS

        return self.async_show_form(
            step_id="advanced",
            data_schema=vol.Schema({
                vol.Required(
                    CONF_TEXT_ENTITY,
                    default=config.get(CONF_TEXT_ENTITY, "")
                ): selector.EntitySelector({"domain": "input_text"}),
                vol.Required(
                    CONF_SCHEDULE_TIME,
                    default=config.get(CONF_SCHEDULE_TIME, "08:00:00")
                ): selector.TimeSelector(),
                vol.Optional(
                    CONF_NOTIFY_SCRIPT,
                    default=config.get(CONF_NOTIFY_SCRIPT, "")
                ): selector.EntitySelector({"domain": "script"}),
                vol.Optional(
                    CONF_NOTIFY_TITLE,
                    default=config.get(CONF_NOTIFY_TITLE, default_notify_title)
                ): str,
                vol.Optional(
                    CONF_HISTORY_DAYS,
                    default=config.get(CONF_HISTORY_DAYS, DEFAULT_HISTORY_DAYS)
                ): selector.NumberSelector({
                    "min": 1,
                    "max": 365,
                    "step": 1,
                    "mode": "box"
                }),
            }),
            errors=errors,
        )


class SlgasOptionsFlowHandler(config_entries.OptionsFlow):
    """處理選項流程"""

    def __init__(self):
        """初始化選項流"""
        self._user_input: dict = {}

    async def async_step_init(self, user_input=None):
        """初始選項步驟"""
        errors = {}
        config = {**self.config_entry.data, **self.config_entry.options}

        if user_input is not None:
            meter_type = config.get(CONF_METER_TYPE, METER_TYPE_GAS)
            company = config.get(CONF_COMPANY, COMPANY_SLGAS)

            # 驗證欄位
            if meter_type == METER_TYPE_WATER and company == COMPANY_WATER_TAIPEI:
                email = user_input.get(CONF_EMAIL, "")
                if email and email.strip():
                    if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
                        errors[CONF_EMAIL] = "invalid_email"

            # 驗證 OCR 來源相關欄位
            ocr_source = user_input.get(CONF_OCR_SOURCE, OCR_SOURCE_GOOGLE_AI)
            if ocr_source == OCR_SOURCE_GOOGLE_AI:
                if not user_input.get(CONF_CAMERA_ENTITY):
                    errors[CONF_CAMERA_ENTITY] = "camera_required"
            else:
                if not user_input.get(CONF_DEGREE_ENTITY):
                    errors[CONF_DEGREE_ENTITY] = "degree_entity_required"

            if not errors:
                return self.async_create_entry(title="", data=user_input)

        meter_type = config.get(CONF_METER_TYPE, METER_TYPE_GAS)

        # 根據 meter_type 顯示不同的欄位
        schema_dict = {}

        if meter_type == METER_TYPE_WATER:
            schema_dict = {
                vol.Required(
                    CONF_APPLICANT_NAME,
                    default=config.get(CONF_APPLICANT_NAME, "")
                ): str,
                vol.Required(
                    CONF_WATER_NO,
                    default=config.get(CONF_WATER_NO, "")
                ): str,
                vol.Required(
                    CONF_PHONE,
                    default=config.get(CONF_PHONE, "")
                ): str,
                vol.Required(
                    CONF_EMAIL,
                    default=config.get(CONF_EMAIL, "")
                ): str,
            }
        elif meter_type == METER_TYPE_ELECTRICITY:
            schema_dict = {
                vol.Required(
                    CONF_TAIPOWER_ID,
                    default=config.get(CONF_TAIPOWER_ID, "")
                ): str,
            }
        else:  # GAS
            schema_dict = {
                vol.Required(
                    CONF_CUS_NO,
                    default=config.get(CONF_CUS_NO, "")
                ): str,
                vol.Required(
                    CONF_CUS_NAME,
                    default=config.get(CONF_CUS_NAME, "")
                ): str,
                vol.Required(
                    CONF_CUS_PHONE,
                    default=config.get(CONF_CUS_PHONE, "")
                ): str,
            }

        # 根據 meter_type 設定預設通知標題
        if meter_type == METER_TYPE_WATER:
            default_notify_title = DEFAULT_NOTIFY_TITLE_WATER
        elif meter_type == METER_TYPE_ELECTRICITY:
            default_notify_title = DEFAULT_NOTIFY_TITLE_ELECTRICITY
        else:
            default_notify_title = DEFAULT_NOTIFY_TITLE_GAS

        # OCR 來源設定
        ocr_source = config.get(CONF_OCR_SOURCE, OCR_SOURCE_GOOGLE_AI)
        schema_dict[vol.Required(
            CONF_OCR_SOURCE, default=ocr_source
        )] = selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[
                    selector.SelectOptionDict(
                        value=OCR_SOURCE_GOOGLE_AI,
                        label="Google AI (攝影機 + AI 辨識)"
                    ),
                    selector.SelectOptionDict(
                        value=OCR_SOURCE_EXTERNAL,
                        label="外部實體 (input_text / sensor)"
                    ),
                ],
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        )

        # 根據 OCR 來源顯示對應欄位
        if ocr_source == OCR_SOURCE_GOOGLE_AI:
            default_prompt = DEFAULT_PROMPT_WATER if meter_type == METER_TYPE_WATER else DEFAULT_PROMPT_GAS
            schema_dict[vol.Required(
                CONF_CAMERA_ENTITY,
                default=config.get(CONF_CAMERA_ENTITY, "")
            )] = selector.EntitySelector({"domain": "camera"})
            schema_dict[vol.Required(
                CONF_PROMPT,
                default=config.get(CONF_PROMPT, default_prompt)
            )] = selector.TextSelector({"multiline": True})
        else:
            schema_dict[vol.Required(
                CONF_DEGREE_ENTITY,
                default=config.get(CONF_DEGREE_ENTITY, "")
            )] = selector.EntitySelector(
                {"domain": ["input_text", "sensor"]}
            )

        schema_dict.update({
            vol.Required(
                CONF_TEXT_ENTITY,
                default=config.get(CONF_TEXT_ENTITY, "")
            ): selector.EntitySelector({"domain": "input_text"}),
            vol.Required(
                CONF_SCHEDULE_TIME,
                default=config.get(CONF_SCHEDULE_TIME, "08:00:00")
            ): selector.TimeSelector(),
            vol.Optional(
                CONF_NOTIFY_SCRIPT,
                default=config.get(CONF_NOTIFY_SCRIPT, "")
            ): selector.EntitySelector({"domain": "script"}),
            vol.Optional(
                CONF_NOTIFY_TITLE,
                default=config.get(CONF_NOTIFY_TITLE, default_notify_title)
            ): str,
            vol.Optional(
                CONF_HISTORY_DAYS,
                default=config.get(CONF_HISTORY_DAYS, DEFAULT_HISTORY_DAYS)
            ): selector.NumberSelector({
                "min": 1,
                "max": 365,
                "step": 1,
                "mode": "box"
            }),
        })

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
        )
