"""Config flow for slgas integration."""
from __future__ import annotations

import re
import aiohttp
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
    CONF_WATER_NUM1,
    CONF_WATER_NUM2,
    CONF_WATER_NUM3,
    CONF_WATER_ADDR_CITY,
    CONF_WATER_ADDR_DIST,
    CONF_WATER_ADDR,
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
    DEFAULT_DEGREE_DIFF_THRESHOLD,
    CONF_DEGREE_DIFF_THRESHOLD,
    DEFAULT_NOTIFY_TITLE_GAS,
    DEFAULT_NOTIFY_TITLE_WATER,
    DEFAULT_NOTIFY_TITLE_ELECTRICITY,
    DEFAULT_PROMPT_GAS,
    DEFAULT_PROMPT_WATER,
    DEFAULT_PROMPT_ELECTRICITY,
    WATER_TAIPEI_CITIES,
)

_TAIWAN_AREA_URL = "https://www.water.gov.tw/ch/ECounter/TaiwanAreaDropDownList"
_TAIWAN_FORM_URL = "https://www.water.gov.tw/ch/ECounter/Apply?NodeId=752&type=17&UseCertificate=0"
_FETCH_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
    "Referer": _TAIWAN_FORM_URL,
    "X-Requested-With": "XMLHttpRequest",
}

import logging
_LOGGER = logging.getLogger(__name__)


async def _fetch_districts(city_code: str) -> list[dict]:
    """從台水 API 取得鄉鎮區選項，不需要 session。"""
    if not city_code:
        return []
    try:
        async with aiohttp.ClientSession(headers=_FETCH_HEADERS) as session:
            async with session.post(
                _TAIWAN_AREA_URL,
                data={"cityCode": city_code},
                timeout=aiohttp.ClientTimeout(total=10),
                ssl=False,
            ) as resp:
                data = await resp.json(content_type=None)
                _LOGGER.debug("[台水] 鄉鎮區 API 回應: %s", data)
                return data if isinstance(data, list) else []
    except Exception as exc:
        _LOGGER.warning("[台水] 無法取得鄉鎮區清單 (cityCode=%s): %s", city_code, exc)
        return []


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
            if self.company == COMPANY_WATER_TAIPEI:
                # 水號格式驗證
                num1 = user_input.get(CONF_WATER_NUM1, "")
                num2 = user_input.get(CONF_WATER_NUM2, "")
                num3 = user_input.get(CONF_WATER_NUM3, "")
                if not re.match(r"^[A-Za-z0-9]{2}$", num1):
                    errors[CONF_WATER_NUM1] = "invalid_water_num1"
                if not re.match(r"^\d{8}$", num2):
                    errors[CONF_WATER_NUM2] = "invalid_water_num2"
                if not re.match(r"^[A-Za-z0-9]{1}$", num3):
                    errors[CONF_WATER_NUM3] = "invalid_water_num3"
                email = user_input.get(CONF_EMAIL, "")
                if email and not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
                    errors[CONF_EMAIL] = "invalid_email"

            if not errors:
                self._user_input.update(user_input)
                if self.company == COMPANY_WATER_TAIPEI:
                    return await self.async_step_water_district()
                return await self.async_step_ocr_config()

        # 根據公司動態生成欄位
        schema_dict = {}

        if self.company == COMPANY_WATER_TAIPEI:
            schema_dict = {
                vol.Required(CONF_APPLICANT_NAME): str,
                vol.Required(CONF_WATER_NUM1): str,
                vol.Required(CONF_WATER_NUM2): str,
                vol.Required(CONF_WATER_NUM3): str,
                vol.Required(CONF_PHONE): str,
                vol.Required(CONF_EMAIL): str,
                vol.Required(CONF_WATER_ADDR_CITY): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(value=v, label=label)
                            for v, label in WATER_TAIPEI_CITIES
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
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

    async def async_step_water_district(self, user_input=None):
        """步驟 3b: 用水地址 (台水專用) — 動態載入鄉鎮區"""
        errors = {}

        if user_input is not None:
            if not user_input.get(CONF_WATER_ADDR_DIST):
                errors[CONF_WATER_ADDR_DIST] = "district_required"
            if not user_input.get(CONF_WATER_ADDR, "").strip():
                errors[CONF_WATER_ADDR] = "address_required"
            if not errors:
                self._user_input.update(user_input)
                return await self.async_step_ocr_config()

        city_code = self._user_input.get(CONF_WATER_ADDR_CITY, "")
        districts = await _fetch_districts(city_code)

        dist_options = [selector.SelectOptionDict(value="", label="請選擇")] + [
            selector.SelectOptionDict(value=d["Value"], label=d["Text"])
            for d in districts
        ]

        return self.async_show_form(
            step_id="water_district",
            data_schema=vol.Schema({
                vol.Required(CONF_WATER_ADDR_DIST): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=dist_options,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(CONF_WATER_ADDR): str,
            }),
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
                n1 = full_data.get(CONF_WATER_NUM1, "")
                n2 = full_data.get(CONF_WATER_NUM2, "")
                n3 = full_data.get(CONF_WATER_NUM3, "")
                unique_id = f"{n1}-{n2}-{n3}" if n1 else full_data.get(CONF_WATER_NO, "water")
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
                    **({} if not config.get(CONF_NOTIFY_SCRIPT) else {"default": config[CONF_NOTIFY_SCRIPT]})
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
                vol.Optional(
                    CONF_DEGREE_DIFF_THRESHOLD,
                    default=config.get(CONF_DEGREE_DIFF_THRESHOLD, DEFAULT_DEGREE_DIFF_THRESHOLD)
                ): selector.NumberSelector({
                    "min": 1,
                    "max": 9999,
                    "step": 1,
                    "mode": "box"
                }),
            }),
            errors=errors,
        )


class SlgasOptionsFlowHandler(config_entries.OptionsFlow):
    """處理選項流程"""

    def __init__(self):
        self._user_input: dict = {}

    # ------------------------------------------------------------------ routing
    async def async_step_init(self, user_input=None):
        config = {**self.config_entry.data, **self.config_entry.options}
        if (config.get(CONF_METER_TYPE) == METER_TYPE_WATER
                and config.get(CONF_COMPANY) == COMPANY_WATER_TAIPEI):
            return await self.async_step_water_basic(user_input)
        return await self.async_step_general(user_input)

    # ------------------------------------------------------------------ water_taipei: step 1
    async def async_step_water_basic(self, user_input=None):
        """台水選項步驟 1：基本資訊 + 縣市"""
        errors = {}
        config = {**self.config_entry.data, **self.config_entry.options}

        if user_input is not None:
            if not re.match(r"^[A-Za-z0-9]{2}$", user_input.get(CONF_WATER_NUM1, "")):
                errors[CONF_WATER_NUM1] = "invalid_water_num1"
            if not re.match(r"^\d{8}$", user_input.get(CONF_WATER_NUM2, "")):
                errors[CONF_WATER_NUM2] = "invalid_water_num2"
            if not re.match(r"^[A-Za-z0-9]{1}$", user_input.get(CONF_WATER_NUM3, "")):
                errors[CONF_WATER_NUM3] = "invalid_water_num3"
            email = user_input.get(CONF_EMAIL, "")
            if email and not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
                errors[CONF_EMAIL] = "invalid_email"
            if not errors:
                self._user_input.update(user_input)
                return await self.async_step_water_district_opts(None)

        return self.async_show_form(
            step_id="water_basic",
            data_schema=vol.Schema({
                vol.Required(CONF_APPLICANT_NAME,
                             default=config.get(CONF_APPLICANT_NAME, "")): str,
                vol.Required(CONF_WATER_NUM1,
                             default=config.get(CONF_WATER_NUM1, "")): str,
                vol.Required(CONF_WATER_NUM2,
                             default=config.get(CONF_WATER_NUM2, "")): str,
                vol.Required(CONF_WATER_NUM3,
                             default=config.get(CONF_WATER_NUM3, "")): str,
                vol.Required(CONF_PHONE,
                             default=config.get(CONF_PHONE, "")): str,
                vol.Required(CONF_EMAIL,
                             default=config.get(CONF_EMAIL, "")): str,
                vol.Required(CONF_WATER_ADDR_CITY,
                             default=config.get(CONF_WATER_ADDR_CITY, "")): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[selector.SelectOptionDict(value=v, label=lbl)
                                 for v, lbl in WATER_TAIPEI_CITIES],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            }),
            errors=errors,
        )

    # ------------------------------------------------------------------ water_taipei: step 2
    async def async_step_water_district_opts(self, user_input=None):
        """台水選項步驟 2：鄉鎮區 + 地址 + OCR + 進階"""
        errors = {}
        config = {**self.config_entry.data, **self.config_entry.options}
        ocr_source = config.get(CONF_OCR_SOURCE, OCR_SOURCE_GOOGLE_AI)

        if user_input is not None:
            if not user_input.get(CONF_WATER_ADDR_DIST):
                errors[CONF_WATER_ADDR_DIST] = "district_required"
            if not user_input.get(CONF_WATER_ADDR, "").strip():
                errors[CONF_WATER_ADDR] = "address_required"
            src = user_input.get(CONF_OCR_SOURCE, OCR_SOURCE_GOOGLE_AI)
            if src == OCR_SOURCE_GOOGLE_AI and not user_input.get(CONF_CAMERA_ENTITY):
                errors[CONF_CAMERA_ENTITY] = "camera_required"
            elif src == OCR_SOURCE_EXTERNAL and not user_input.get(CONF_DEGREE_ENTITY):
                errors[CONF_DEGREE_ENTITY] = "degree_entity_required"
            if not errors:
                return self.async_create_entry(title="", data={**self._user_input, **user_input})

        city_code = self._user_input.get(CONF_WATER_ADDR_CITY,
                                         config.get(CONF_WATER_ADDR_CITY, ""))
        districts = await _fetch_districts(city_code)
        dist_options = [selector.SelectOptionDict(value="", label="請選擇")] + [
            selector.SelectOptionDict(value=d["Value"], label=d["Text"])
            for d in districts
        ]

        schema_dict: dict = {
            vol.Required(CONF_WATER_ADDR_DIST,
                         default=config.get(CONF_WATER_ADDR_DIST, "")): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=dist_options,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Required(CONF_WATER_ADDR,
                         default=config.get(CONF_WATER_ADDR, "")): str,
            vol.Required(CONF_OCR_SOURCE, default=ocr_source): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectOptionDict(value=OCR_SOURCE_GOOGLE_AI,
                                                  label="Google AI (攝影機 + AI 辨識)"),
                        selector.SelectOptionDict(value=OCR_SOURCE_EXTERNAL,
                                                  label="外部實體 (input_text / sensor)"),
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
        }
        if ocr_source == OCR_SOURCE_GOOGLE_AI:
            schema_dict[vol.Required(CONF_CAMERA_ENTITY,
                                     default=config.get(CONF_CAMERA_ENTITY, ""))] = \
                selector.EntitySelector({"domain": "camera"})
            schema_dict[vol.Required(CONF_PROMPT,
                                     default=config.get(CONF_PROMPT, DEFAULT_PROMPT_WATER))] = \
                selector.TextSelector({"multiline": True})
        else:
            schema_dict[vol.Required(CONF_DEGREE_ENTITY,
                                     default=config.get(CONF_DEGREE_ENTITY, ""))] = \
                selector.EntitySelector({"domain": ["input_text", "sensor"]})

        schema_dict.update(self._advanced_schema(config, DEFAULT_NOTIFY_TITLE_WATER))

        return self.async_show_form(
            step_id="water_district_opts",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
        )

    # ------------------------------------------------------------------ gas / electricity
    async def async_step_general(self, user_input=None):
        """瓦斯 / 電力 單頁選項"""
        errors = {}
        config = {**self.config_entry.data, **self.config_entry.options}
        meter_type = config.get(CONF_METER_TYPE, METER_TYPE_GAS)
        ocr_source = config.get(CONF_OCR_SOURCE, OCR_SOURCE_GOOGLE_AI)

        if user_input is not None:
            src = user_input.get(CONF_OCR_SOURCE, OCR_SOURCE_GOOGLE_AI)
            if src == OCR_SOURCE_GOOGLE_AI and not user_input.get(CONF_CAMERA_ENTITY):
                errors[CONF_CAMERA_ENTITY] = "camera_required"
            elif src == OCR_SOURCE_EXTERNAL and not user_input.get(CONF_DEGREE_ENTITY):
                errors[CONF_DEGREE_ENTITY] = "degree_entity_required"
            if not errors:
                return self.async_create_entry(title="", data=user_input)

        if meter_type == METER_TYPE_ELECTRICITY:
            id_schema = {vol.Required(CONF_TAIPOWER_ID,
                                      default=config.get(CONF_TAIPOWER_ID, "")): str}
            default_title = DEFAULT_NOTIFY_TITLE_ELECTRICITY
            default_prompt = DEFAULT_PROMPT_ELECTRICITY
        else:
            id_schema = {
                vol.Required(CONF_CUS_NO, default=config.get(CONF_CUS_NO, "")): str,
                vol.Required(CONF_CUS_NAME, default=config.get(CONF_CUS_NAME, "")): str,
                vol.Required(CONF_CUS_PHONE, default=config.get(CONF_CUS_PHONE, "")): str,
            }
            default_title = DEFAULT_NOTIFY_TITLE_GAS
            default_prompt = DEFAULT_PROMPT_GAS

        schema_dict = {**id_schema,
                       vol.Required(CONF_OCR_SOURCE, default=ocr_source): selector.SelectSelector(
                           selector.SelectSelectorConfig(
                               options=[
                                   selector.SelectOptionDict(value=OCR_SOURCE_GOOGLE_AI,
                                                             label="Google AI (攝影機 + AI 辨識)"),
                                   selector.SelectOptionDict(value=OCR_SOURCE_EXTERNAL,
                                                             label="外部實體 (input_text / sensor)"),
                               ],
                               mode=selector.SelectSelectorMode.DROPDOWN,
                           )
                       )}
        if ocr_source == OCR_SOURCE_GOOGLE_AI:
            schema_dict[vol.Required(CONF_CAMERA_ENTITY,
                                     default=config.get(CONF_CAMERA_ENTITY, ""))] = \
                selector.EntitySelector({"domain": "camera"})
            schema_dict[vol.Required(CONF_PROMPT,
                                     default=config.get(CONF_PROMPT, default_prompt))] = \
                selector.TextSelector({"multiline": True})
        else:
            schema_dict[vol.Required(CONF_DEGREE_ENTITY,
                                     default=config.get(CONF_DEGREE_ENTITY, ""))] = \
                selector.EntitySelector({"domain": ["input_text", "sensor"]})

        schema_dict.update(self._advanced_schema(config, default_title))

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
        )

    # ------------------------------------------------------------------ shared helper
    @staticmethod
    def _advanced_schema(config: dict, default_title: str) -> dict:
        return {
            vol.Required(CONF_TEXT_ENTITY,
                         default=config.get(CONF_TEXT_ENTITY, "")): selector.EntitySelector(
                {"domain": "input_text"}),
            vol.Required(CONF_SCHEDULE_TIME,
                         default=config.get(CONF_SCHEDULE_TIME, "08:00:00")): selector.TimeSelector(),
            vol.Optional(CONF_NOTIFY_SCRIPT,
                         **({} if not config.get(CONF_NOTIFY_SCRIPT) else {"default": config[CONF_NOTIFY_SCRIPT]})): selector.EntitySelector(
                {"domain": "script"}),
            vol.Optional(CONF_NOTIFY_TITLE,
                         default=config.get(CONF_NOTIFY_TITLE, default_title)): str,
            vol.Optional(CONF_HISTORY_DAYS,
                         default=config.get(CONF_HISTORY_DAYS, DEFAULT_HISTORY_DAYS)): selector.NumberSelector(
                {"min": 1, "max": 365, "step": 1, "mode": "box"}),
            vol.Optional(CONF_DEGREE_DIFF_THRESHOLD,
                         default=config.get(CONF_DEGREE_DIFF_THRESHOLD, DEFAULT_DEGREE_DIFF_THRESHOLD)): selector.NumberSelector(
                {"min": 1, "max": 9999, "step": 1, "mode": "box"}),
        }
