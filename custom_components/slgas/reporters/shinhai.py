"""新海瓦斯 (ShinHai Gas) reporter."""
import base64
import json
import logging

import aiohttp

from .base import BaseReporter
from ..const import (
    CONF_SHINHAI_NO1,
    CONF_SHINHAI_NO2,
    CONF_SHINHAI_NO3,
    CONF_SHINHAI_TEL_AREA,
    CONF_SHINHAI_TEL,
    CONF_SHINHAI_MOBILE,
)

_LOGGER = logging.getLogger(__name__)

_BASE_URL = "https://www.shinhaigas.com.tw"
_CAPTCHA_URL = f"{_BASE_URL}/API/shgasweb/VertifyCode"
_VERIFY_URL  = f"{_BASE_URL}/API/shgasweb/Vertify"
_DATA_URL    = f"{_BASE_URL}/API/shgasweb/Data"

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": f"{_BASE_URL}/Apply/Degree.html",
    "Origin": _BASE_URL,
    "Content-Type": "application/json;charset=UTF-8",
}


def _decode_jwt_payload(token: str) -> dict:
    """Decode JWT payload without verifying signature."""
    payload_b64 = token.split(".")[1]
    padding = 4 - len(payload_b64) % 4
    if padding != 4:
        payload_b64 += "=" * padding
    payload_b64 = payload_b64.replace("-", "+").replace("_", "/")
    return json.loads(base64.b64decode(payload_b64).decode("utf-8"))


class ShinhaiReporter(BaseReporter):
    """新海瓦斯自報度數模組"""

    def __init__(self, hass, config: dict):
        super().__init__(hass, config)
        self.no1 = config.get(CONF_SHINHAI_NO1, "")
        self.no2 = config.get(CONF_SHINHAI_NO2, "")
        self.no3 = config.get(CONF_SHINHAI_NO3, "")
        self.tel_area = config.get(CONF_SHINHAI_TEL_AREA, "")
        self.tel = config.get(CONF_SHINHAI_TEL, "")
        self.mobile = config.get(CONF_SHINHAI_MOBILE, "")

    @property
    def user_no(self) -> str:
        return f"{self.no1}{self.no2}{self.no3}"

    def validate_config(self) -> bool:
        has_no = self.no1 and self.no2 and self.no3
        has_contact = (self.tel_area and self.tel) or self.mobile
        return bool(has_no and has_contact)

    def get_required_fields(self) -> list:
        return [
            CONF_SHINHAI_NO1, CONF_SHINHAI_NO2, CONF_SHINHAI_NO3,
            CONF_SHINHAI_TEL_AREA, CONF_SHINHAI_TEL, CONF_SHINHAI_MOBILE,
        ]

    async def submit(self, degree: str, image_path: str = None) -> bool:
        _LOGGER.info("[新海] 準備上報度數: %s", degree)

        try:
            async with aiohttp.ClientSession(headers=_HEADERS) as session:
                # Step 1: 取得驗證碼 (JWT jti 欄位即為答案)
                async with session.get(_CAPTCHA_URL) as r:
                    if r.status != 200:
                        self.last_status = f"取得驗證碼失敗: HTTP {r.status}"
                        return False
                    captcha_data = await r.json(content_type=None)

                hash_jwt = captcha_data["Hash"]
                jwt_payload = _decode_jwt_payload(hash_jwt)
                captcha_answer = jwt_payload["jti"]
                _LOGGER.debug("[新海] 驗證碼: %s", captcha_answer)

                # Step 2: 驗證碼驗證
                async with session.post(_VERIFY_URL, json={
                    "Captcha": captcha_answer,
                    "Hash": hash_jwt,
                }) as r:
                    if r.status != 200:
                        self.last_status = f"驗證碼驗證失敗: HTTP {r.status}"
                        return False

                # Step 3: 查詢用戶資料 (取得 addressPure)
                async with session.post(_DATA_URL, json={
                    "FUNNAME": "WebQueryHouseNo",
                    "FUN_CODE": "Q001",
                    "BODY": {
                        "QUERY_TYPE": "1",
                        "QUERY_USER_NO": self.user_no,
                    },
                }) as r:
                    if r.status != 200:
                        self.last_status = f"查詢用戶失敗: HTTP {r.status}"
                        return False
                    query_resp = await r.json(content_type=None)

                error_code = query_resp["DOCDATA"]["HEAD"]["ERROR_CODE"]
                if error_code != "0000":
                    desc = query_resp["DOCDATA"]["HEAD"].get("ERROR_CODE_DESC", error_code)
                    self.last_status = f"查詢失敗: {desc}"
                    _LOGGER.error("[新海] 查詢用戶失敗: %s", desc)
                    return False

                address_pure = query_resp["DOCDATA"]["BODY"]["QUERY_DATA1"]

                # Step 4: 提交度數
                async with session.post(_DATA_URL, json={
                    "FUNNAME": "WebWriteToDegreeNew",
                    "FUN_CODE": "I002",
                    "BODY": {
                        "DEGREE_USER_NO": self.user_no,
                        "DEGREE_ADDRESS": address_pure,
                        "DEGREE_TEL": f"{self.tel_area}{self.tel}",
                        "DEGREE_MOBILE": self.mobile,
                        "DEGREE_NUMBER": str(degree),
                        "DEGREE_QUERY_COUNT": 3,
                    },
                }) as r:
                    if r.status != 200:
                        self.last_status = f"提交失敗: HTTP {r.status}"
                        return False
                    submit_resp = await r.json(content_type=None)

                s_error = submit_resp["DOCDATA"]["HEAD"]["ERROR_CODE"]
                if s_error == "0000":
                    _LOGGER.info("[新海] 度數上報成功: %s", degree)
                    self.last_status = f"上報成功: {degree}"
                    return True
                else:
                    desc = submit_resp["DOCDATA"]["HEAD"].get("ERROR_CODE_DESC", s_error)
                    _LOGGER.error("[新海] 提交失敗: %s", desc)
                    self.last_status = f"上報失敗: {desc}"
                    return False

        except Exception as e:
            _LOGGER.error("[新海] 上報時出錯: %s", e)
            self.last_status = f"錯誤: {e}"
            return False
