"""Taiwan Water Corporation (臺灣自來水) water meter reporter."""
import base64
import logging
import os
import re

import aiohttp

from .base import BaseReporter
from ..const import (
    CONF_APPLICANT_NAME,
    CONF_EMAIL,
    CONF_PHONE,
    CONF_WATER_NUM1,
    CONF_WATER_NUM2,
    CONF_WATER_NUM3,
    CONF_WATER_NO,
    CONF_WATER_ADDR_CITY,
    CONF_WATER_ADDR_DIST,
    CONF_WATER_ADDR,
    DEFAULT_CAPTCHA_IMAGE_PATH,
)

_LOGGER = logging.getLogger(__name__)

_BASE = "https://www.water.gov.tw"
_FORM_URL = f"{_BASE}/ch/ECounter/Apply?NodeId=752&type=17&UseCertificate=0"
_APPLY_URL = f"{_BASE}/ch/ECounter/Apply?Length=8"
_UPLOAD_URL = f"{_BASE}/ch/ServerFile/UploadMultiFile?folderNameType=19&limitFileCount=2"
_CAPTCHA_URL = f"{_BASE}/ch/ECounter/ChangeVerificationCode"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
}


class WaterTaipeiReporter(BaseReporter):
    """臺灣自來水公司上報模組"""

    def __init__(self, hass, config: dict):
        super().__init__(hass, config)
        self.name = config.get(CONF_APPLICANT_NAME, "")
        self.phone = config.get(CONF_PHONE, "")
        self.email = config.get(CONF_EMAIL, "")
        # 水號三段 (優先用新格式，fallback 舊 WATER_NO)
        self.water_num1 = config.get(CONF_WATER_NUM1, "")
        self.water_num2 = config.get(CONF_WATER_NUM2, "")
        self.water_num3 = config.get(CONF_WATER_NUM3, "")
        if not self.water_num1:
            self._parse_legacy_water_no(config.get(CONF_WATER_NO, ""))
        # 地址
        self.addr_city = config.get(CONF_WATER_ADDR_CITY, "")
        self.addr_dist = config.get(CONF_WATER_ADDR_DIST, "")
        self.addr = config.get(CONF_WATER_ADDR, "")

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def validate_config(self) -> bool:
        return all([self.name, self.water_num1, self.water_num2, self.water_num3,
                    self.phone, self.email])

    def get_required_fields(self) -> list:
        return [CONF_APPLICANT_NAME, CONF_WATER_NUM1, CONF_WATER_NUM2,
                CONF_WATER_NUM3, CONF_PHONE, CONF_EMAIL,
                CONF_WATER_ADDR_CITY, CONF_WATER_ADDR_DIST, CONF_WATER_ADDR]

    async def submit(self, degree: str, image_path: str = None) -> bool:
        if not image_path:
            image_path = self.config.get("image_path", "")

        _LOGGER.info("[台水] 準備上報度數: %s", degree)

        try:
            async with aiohttp.ClientSession(headers=_HEADERS) as session:
                # 1. GET 表單頁 → session cookie + CSRF token
                self.last_status = "取得 Session..."
                csrf_token = await self._fetch_csrf_token(session)
                _LOGGER.info("[台水] 已取得 CSRF Token")

                # 2. 上傳照片 → MultiFileId
                self.last_status = "上傳照片..."
                file_id = await self._upload_photo(session, image_path)
                _LOGGER.info("[台水] 照片上傳完成，FileId: %s", file_id)

                # 3. 取得驗證碼圖片 → AI OCR
                self.last_status = "AI 辨識驗證碼..."
                captcha_code = await self._solve_captcha(session)
                _LOGGER.info("[台水] 驗證碼辨識結果: %s", captcha_code)

                # 4. POST 表單
                self.last_status = "送出表單..."
                return await self._post_form(session, csrf_token, degree,
                                             file_id, captcha_code)

        except Exception as exc:
            _LOGGER.error("[台水] 上報失敗: %s", exc, exc_info=True)
            self.last_status = f"錯誤: {exc}"
            return False

    # ------------------------------------------------------------------
    # Step 1: CSRF token
    # ------------------------------------------------------------------

    async def _fetch_csrf_token(self, session: aiohttp.ClientSession) -> str:
        async with session.get(_FORM_URL) as resp:
            html = await resp.text(encoding="utf-8", errors="ignore")

        m = re.search(
            r'<input[^>]*name="__RequestVerificationToken"[^>]*value="([^"]+)"',
            html,
        )
        if not m:
            raise RuntimeError("找不到 CSRF Token，頁面結構可能已改變")
        return m.group(1)

    # ------------------------------------------------------------------
    # Step 2: Photo upload
    # ------------------------------------------------------------------

    async def _upload_photo(self, session: aiohttp.ClientSession,
                            image_path: str) -> str:
        if not image_path or not os.path.exists(image_path):
            _LOGGER.warning("[台水] 照片不存在，跳過上傳: %s", image_path)
            return ""

        filename = os.path.basename(image_path)
        content_type = "image/png" if filename.lower().endswith(".png") else "image/jpeg"

        data = aiohttp.FormData()
        with open(image_path, "rb") as f:
            data.add_field("files", f, filename=filename, content_type=content_type)

        headers = {"Referer": _FORM_URL, "X-Requested-With": "XMLHttpRequest"}
        async with session.post(_UPLOAD_URL, data=data, headers=headers) as resp:
            if resp.status != 200:
                _LOGGER.warning("[台水] 照片上傳失敗，HTTP %s", resp.status)
                return ""
            result = await resp.json(content_type=None)

        if isinstance(result, dict) and result.get("success"):
            file_ids = result.get("fileIds", [])
            return ",".join(str(fid) for fid in file_ids)

        _LOGGER.warning("[台水] 照片上傳回應異常: %s", result)
        return ""

    # ------------------------------------------------------------------
    # Step 3: CAPTCHA → AI OCR
    # ------------------------------------------------------------------

    async def _solve_captcha(self, session: aiohttp.ClientSession) -> str:
        headers = {
            "Referer": _FORM_URL,
            "X-Requested-With": "XMLHttpRequest",
        }
        async with session.get(_CAPTCHA_URL, headers=headers) as resp:
            data = await resp.json(content_type=None)

        b64 = data.get("ImageBase64Str", "")
        if not b64:
            raise RuntimeError("無法取得驗證碼圖片")

        # 直接存 GIF，Google AI 可直接讀取
        gif_bytes = base64.b64decode(b64)
        with open(DEFAULT_CAPTCHA_IMAGE_PATH, "wb") as f:
            f.write(gif_bytes)
        _LOGGER.debug("[台水] 驗證碼已存至 %s", DEFAULT_CAPTCHA_IMAGE_PATH)

        return await self._ai_recognize_captcha()

    async def _ai_recognize_captcha(self) -> str:
        filename = os.path.basename(DEFAULT_CAPTCHA_IMAGE_PATH)
        media_id = f"media-source://media_source/local/{filename}"

        service_data = {
            "task_name": "water captcha",
            "entity_id": "ai_task.google_ai_task",
            "attachments": {
                "media_content_id": media_id,
                "media_content_type": "image/gif",
                "metadata": {
                    "title": filename,
                    "thumbnail": None,
                    "media_class": "image",
                    "children_media_class": None,
                    "navigateIds": [
                        {},
                        {
                            "media_content_type": "app",
                            "media_content_id": "media-source://media_source",
                        },
                    ],
                },
            },
            "instructions": "只回傳5位數字",
        }

        response = await self.hass.services.async_call(
            "ai_task", "generate_data", service_data,
            blocking=True, return_response=True,
        )

        raw = None
        if isinstance(response, dict):
            raw = response.get("text")
            if not raw:
                inner = response.get("data")
                raw = (inner.get("text") if isinstance(inner, dict) else inner)

        if not raw:
            raise RuntimeError(f"AI 未回傳有效結果: {response}")

        code = re.sub(r"[^A-Za-z0-9]", "", raw.strip())
        if not code:
            raise RuntimeError(f"AI 辨識結果無效: {raw!r}")
        return code

    # ------------------------------------------------------------------
    # Step 4: POST form
    # ------------------------------------------------------------------

    async def _post_form(self, session: aiohttp.ClientSession,
                         csrf_token: str, degree: str,
                         file_id: str, captcha_code: str) -> bool:
        tel = self._parse_phone()
        email_account, _ = self.email.split("@", 1) if "@" in self.email else (self.email, "")

        data = aiohttp.FormData()

        # CSRF + hidden fixed
        data.add_field("__RequestVerificationToken", csrf_token)
        data.add_field("Lang", "tw")
        data.add_field("TYPE", "17")
        data.add_field("NodeId", "752")
        data.add_field("SiteId", "")
        data.add_field("CertificateType", "不使用")
        data.add_field("IsMyData", "False")
        data.add_field("ECounterViewModel.IsMyData", "False")
        data.add_field("WaterNoChangeMessage", "")

        # 申請人
        data.add_field("NAME", self.name)

        # 電話
        data.add_field("TEL1", tel.get("TEL1", ""))
        data.add_field("TEL2", tel.get("TEL2", ""))
        data.add_field("TEL3", tel.get("TEL3", ""))
        data.add_field("TEL4", "")
        data.add_field("MTEL1", tel.get("MTEL1", ""))
        data.add_field("MTEL2", tel.get("MTEL2", ""))

        # Email
        data.add_field("emailAccount", email_account)
        data.add_field("EMAIL", self.email)

        # 水號三段
        data.add_field("WATER_NUM1", self.water_num1.upper())
        data.add_field("WATER_NUM2", self.water_num2)
        data.add_field("WATER_NUM3", self.water_num3.upper())

        # 地址
        data.add_field("WATER_ADDR_addx", self.addr_city)
        data.add_field("WATER_ADDR_addx_COUN", self.addr_dist)
        data.add_field("WATER_ADDR", self.addr)

        # 指針數
        data.add_field("indexnumber", degree)

        # 照片 ID
        data.add_field("MultiFileId", file_id)
        data.add_field("TempOnServerFileIds", f",{file_id}" if file_id else "")

        # 驗證碼
        data.add_field("VerificationCode", captcha_code)

        headers = {
            "Referer": _FORM_URL,
            "X-Requested-With": "XMLHttpRequest",
        }
        async with session.post(_APPLY_URL, data=data, headers=headers) as resp:
            if resp.status != 200:
                self.last_status = f"POST 失敗: HTTP {resp.status}"
                return False
            body = await resp.text(encoding="utf-8", errors="ignore")

        _LOGGER.debug("[台水] 回應內容: %s", body[:200])

        if "申辦成功" in body or "成功" in body:
            self.last_status = f"上報成功: {degree}"
            _LOGGER.info("[台水] 上報成功！度數: %s", degree)
            return True

        if "驗證碼" in body or "verificationcode" in body.lower():
            self.last_status = "驗證碼錯誤，請重試"
        else:
            self.last_status = f"上報失敗 ({body[:80]})"
        _LOGGER.warning("[台水] 上報失敗，回應: %s", body[:300])
        return False

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _parse_phone(self) -> dict:
        """將電話號碼拆分成 TEL1/TEL2/TEL3 或 MTEL1/MTEL2。"""
        digits = re.sub(r"[\s\-()]", "", self.phone)
        if digits.startswith("09") and len(digits) >= 10:
            return {"MTEL1": digits[:4], "MTEL2": digits[4:10],
                    "TEL1": "", "TEL2": "", "TEL3": ""}
        # 市話: 02 → 2碼區碼；其他縣市 → 3碼區碼
        area_len = 2 if digits.startswith("02") else 3
        area = digits[:area_len]
        rest = digits[area_len:]
        return {"TEL1": area, "TEL2": rest[:4], "TEL3": rest[4:8],
                "MTEL1": "", "MTEL2": ""}

    def _parse_legacy_water_no(self, water_no: str) -> None:
        """將舊格式 'XX-XXXXXXXX-X' 拆分填入 NUM1/2/3。"""
        parts = water_no.replace(" ", "").split("-")
        if len(parts) >= 3:
            self.water_num1 = parts[0]
            self.water_num2 = parts[1]
            self.water_num3 = parts[2]
        elif len(parts) == 2:
            self.water_num1 = parts[0]
            self.water_num2 = parts[1]
            self.water_num3 = ""
