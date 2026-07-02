"""SLGAS (欣隆) gas company reporter."""
import logging
import re
from urllib.parse import quote
import aiohttp
from bs4 import BeautifulSoup

from .base import BaseReporter
from ..const import CONF_CUS_NO, CONF_CUS_NAME, CONF_CUS_PHONE

_LOGGER = logging.getLogger(__name__)


def _encode_form_field(value) -> str:
    """Percent-encode a form field, preserving raw (e.g. Big5) bytes."""
    if isinstance(value, bytes):
        return quote(value)
    return quote(str(value), safe="")


def _build_form_body(fields: dict) -> str:
    """Build an application/x-www-form-urlencoded body without letting
    aiohttp reinterpret bytes values as a multipart file upload."""
    return "&".join(f"{quote(k)}={_encode_form_field(v)}" for k, v in fields.items())


class SlgasReporter(BaseReporter):
    """欣隆天然瓦斯 (SLGAS) 上報模組"""

    BASE_URL = "https://www.slgas.com.tw"
    SUBMIT_URL = f"{BASE_URL}/GetDegree_SQL.asp"

    def __init__(self, hass, config: dict):
        super().__init__(hass, config)
        self.cus_no = config.get(CONF_CUS_NO, "")
        self.cus_name = config.get(CONF_CUS_NAME, "")
        self.cus_phone = config.get(CONF_CUS_PHONE, "")

    def validate_config(self) -> bool:
        """驗證必要設定"""
        required = [CONF_CUS_NO, CONF_CUS_NAME, CONF_CUS_PHONE]
        return all(self.config.get(key) for key in required)

    def get_required_fields(self) -> list:
        """回傳欣隆瓦斯需要的欄位"""
        return [CONF_CUS_NO, CONF_CUS_NAME, CONF_CUS_PHONE]

    async def submit(self, degree: str, image_path: str = None) -> bool:
        """上報瓦斯度數到欣隆網站"""
        _LOGGER.info(f"[欣隆] 準備上報度數: {degree}")

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        try:
            async with aiohttp.ClientSession(headers=headers) as session:
                # Step 1: POST for validation (ChkField=Check)
                payload1 = {
                    "CusNo": self.cus_no,
                    "CusName": self.cus_name.encode("big5"),
                    "Cuscallno": self.cus_phone,
                    "ChkField": "Check",
                    "Send": "送出".encode("big5")
                }

                async with session.post(self.SUBMIT_URL, data=_build_form_body(payload1)) as resp1:
                    if resp1.status != 200:
                        _LOGGER.error(f"[欣隆] Step 1 POST 失敗: {resp1.status}")
                        self.last_status = f"POST 失敗: {resp1.status}"
                        return False

                    html1 = await resp1.text(encoding="big5", errors="ignore")
                    soup = BeautifulSoup(html1, "html.parser")

                    # Step 2: Prepare second POST (ChkField=Append)
                    payload2 = {
                        "CusTel": self._get_input_value(soup, "CusTel"),
                        "CusEMail": self._get_input_value(soup, "CusEMail"),
                        "cus_sDegree": self._get_input_value(soup, "cus_sDegree"),
                        "cus_sLOG_DAY": self._get_input_value(soup, "cus_sLOG_DAY"),
                        "cus_sLOG_DEG0": self._get_input_value(soup, "cus_sLOG_DEG0"),
                        "CusDegree": str(degree),
                        "ChkField": "Append",
                        "send": "送出".encode("big5")
                    }

                    async with session.post(self.SUBMIT_URL, data=_build_form_body(payload2)) as resp2:
                        if resp2.status != 200:
                            _LOGGER.error(f"[欣隆] Step 2 POST 失敗: {resp2.status}")
                            self.last_status = f"POST 失敗: {resp2.status}"
                            return False

                        html2 = await resp2.text(encoding="big5", errors="ignore")

                        if "瓦斯錶度數已登錄完成" in html2:
                            _LOGGER.info("[欣隆] 瓦斯度數上報成功！")
                            self.last_status = f"上報成功: {degree}"
                            return True
                        else:
                            _LOGGER.warning("[欣隆] 網站未顯示成功訊息")
                            self.last_status = "上報失敗: 未得到確認訊息"
                            return False

        except Exception as e:
            _LOGGER.error(f"[欣隆] 上報時出錯: {e}")
            self.last_status = f"錯誤: {str(e)}"
            return False

    def _get_input_value(self, soup, name):
        """Extract value from input field by name."""
        tag = soup.find("input", {"name": name})
        return tag.get("value", "") if tag else ""
