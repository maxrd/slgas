"""Taiwan Water Corporation (台灣自來水) water meter reporter."""
import logging
import os
import aiohttp

from .base import BaseReporter
from ..const import (
    CONF_WATER_NO,
    CONF_APPLICANT_NAME,
    CONF_EMAIL,
    CONF_PHONE,
)

_LOGGER = logging.getLogger(__name__)


class WaterTaipeiReporter(BaseReporter):
    """台灣自來水公司 (Taiwan Water Corporation) 上報模組"""

    BASE_URL = "https://www.water.gov.tw/ch/ECounter"
    APPLY_URL = f"{BASE_URL}/ch/ECounter/Apply?Length=8"

    def __init__(self, hass, config: dict):
        super().__init__(hass, config)
        self.applicant_name = config.get(CONF_APPLICANT_NAME, "")
        self.water_no = config.get(CONF_WATER_NO, "")
        self.phone = config.get(CONF_PHONE, "")
        self.email = config.get(CONF_EMAIL, "")
        self.image_path = config.get("image_path", "")

    def validate_config(self) -> bool:
        """驗證必要設定"""
        required = [CONF_APPLICANT_NAME, CONF_WATER_NO, CONF_PHONE, CONF_EMAIL]
        return all(self.config.get(key) for key in required)

    def get_required_fields(self) -> list:
        """回傳台灣自來水需要的欄位"""
        return [CONF_APPLICANT_NAME, CONF_WATER_NO, CONF_PHONE, CONF_EMAIL]

    async def submit(self, degree: str, image_path: str = None) -> bool:
        """上報水表度數到台灣自來水

        注意：因為台水系統有圖形驗證碼，無法完全自動化。
        驗證碼應在 config_flow 中由用戶提供。
        """
        if not image_path:
            image_path = self.image_path

        _LOGGER.info(f"[台水] 準備上報度數: {degree}, 圖片: {image_path}")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        try:
            # 驗證圖片存在
            if not os.path.exists(image_path):
                _LOGGER.error(f"[台水] 找不到圖片: {image_path}")
                self.last_status = "錯誤: 找不到圖片"
                return False

            # 讀取圖片二進制資料
            with open(image_path, "rb") as f:
                image_data = f.read()

            async with aiohttp.ClientSession(headers=headers) as session:
                # 建立 multipart/form-data
                data = aiohttp.FormData()

                # 基本資訊欄位
                # ⚠️ 以下欄位名稱待確認：需根據台水實際表單調整
                data.add_field("applicant_name", self.applicant_name)
                data.add_field("water_no", self.water_no)
                data.add_field("phone", self.phone)
                data.add_field("email", self.email)
                data.add_field("meter_reading", degree)

                # 上傳圖片
                filename = os.path.basename(image_path)
                data.add_field(
                    "meter_photo",  # ← 根據台水實際欄位名調整
                    open(image_path, "rb"),
                    filename=filename,
                    content_type="image/png"
                )

                # 驗證碼 (若已在 config_flow 取得)
                if "captcha_code" in self.config:
                    data.add_field("captcha_code", self.config.get("captcha_code"))

                # 合同同意 (假設欄位名稱)
                data.add_field("agree_rules", "1")
                data.add_field("agree_privacy", "1")
                data.add_field("agree_terms", "1")

                # 提交 POST
                async with session.post(self.APPLY_URL, data=data) as response:
                    if response.status != 200:
                        _LOGGER.error(f"[台水] POST 失敗，狀態碼: {response.status}")
                        self.last_status = f"POST 失敗: {response.status}"
                        return False

                    html_response = await response.text(encoding="utf-8", errors="ignore")

                    # 判斷成功訊息
                    success_keywords = [
                        "自報水表指數已登錄完成",
                        "成功",
                        "已登錄",
                    ]
                    if any(keyword in html_response for keyword in success_keywords):
                        _LOGGER.info("[台水] 水表度數上報成功！")
                        self.last_status = f"上報成功: {degree}"
                        return True
                    else:
                        _LOGGER.warning(f"[台水] 未找到成功訊息，回傳內容片段: {html_response[:200]}")
                        self.last_status = "上報失敗: 未得到確認訊息"
                        return False

        except FileNotFoundError:
            _LOGGER.error(f"[台水] 找不到圖片: {image_path}")
            self.last_status = "錯誤: 找不到圖片"
            return False

        except Exception as e:
            _LOGGER.error(f"[台水] 上報時出錯: {e}")
            self.last_status = f"錯誤: {str(e)}"
            return False
