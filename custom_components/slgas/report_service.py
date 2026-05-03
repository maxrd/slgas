"""Report service for slgas."""
import logging
import re
import asyncio
import aiohttp
from bs4 import BeautifulSoup
from datetime import datetime

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

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
    DEFAULT_IMAGE_PATH,
)

_LOGGER = logging.getLogger(__name__)

class SlgasReportService:
    """Handle the reporting workflow."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        self.hass = hass
        self.entry = entry
        self.history = []
        self.last_status = "尚未執行"

    @property
    def config(self):
        """Return merged config (options + data)."""
        return {**self.entry.data, **self.entry.options}

    async def execute_full_workflow(self, submit: bool = True):
        """Execute the entire workflow based on OCR source setting."""
        try:
            ocr_source = self.config.get(CONF_OCR_SOURCE, OCR_SOURCE_GOOGLE_AI)

            if ocr_source == OCR_SOURCE_EXTERNAL:
                # === 外部實體模式：直接讀取 degree_entity 的值 ===
                ocr_degree = await self._read_external_degree()
            else:
                # === Google AI 模式：拍照 + AI OCR ===
                ocr_degree = await self._google_ai_ocr()

            # 驗證度數是否為有效數字
            if not ocr_degree or not ocr_degree.isdigit():
                raise Exception(f"取得度數失敗 (結果: {ocr_degree})")

            # 寫入 text_entity
            text_id = self.config.get(CONF_TEXT_ENTITY)
            if text_id:
                await self.hass.services.async_call(
                    "input_text",
                    "set_value",
                    {"entity_id": text_id, "value": ocr_degree},
                    blocking=True
                )
                _LOGGER.info(f"已更新 {text_id} 為 {ocr_degree}")

            # 上報或待確認
            if submit:
                self.last_status = f"正在上報網站 (度數: {ocr_degree})..."
                success = await self._submit_to_slgas(ocr_degree)
                if success:
                    self.last_status = f"上報成功: {ocr_degree}"
                else:
                    self.last_status = f"回報失敗 (度數: {ocr_degree})"
            else:
                self.last_status = f"辨識完成: {ocr_degree} (待確認)"
                _LOGGER.info(f"排程執行：已完成取得度數 ({ocr_degree})，跳過自動上報。")

            self._add_to_history(ocr_degree, self.last_status)

            # 發送通知
            await self._send_notification(ocr_degree)

        except Exception as e:
            _LOGGER.error(f"瓦斯回報流程出錯: {e}")
            self.last_status = f"錯誤: {str(e)}"
            self._add_to_history("N/A", self.last_status)

    async def _google_ai_ocr(self):
        """Google AI mode: snapshot + OCR."""
        # 1. 拍照
        self.last_status = "正在拍攝照片..."
        camera_id = self.config.get(CONF_CAMERA_ENTITY)
        if not camera_id:
            raise Exception("Google AI 模式需要設定攝影機實體")

        await self.hass.services.async_call(
            "camera",
            "snapshot",
            {"entity_id": camera_id, "filename": DEFAULT_IMAGE_PATH},
            blocking=True
        )
        _LOGGER.info(f"已拍攝照片並存於 {DEFAULT_IMAGE_PATH}")

        # 等待檔案完全寫入磁碟
        await asyncio.sleep(2)

        # 2. AI OCR
        self.last_status = "正在進行 AI OCR 辨識..."
        return await self._perform_ocr()

    async def _read_external_degree(self):
        """External mode: read degree from degree_entity."""
        degree_entity_id = self.config.get(CONF_DEGREE_ENTITY)
        if not degree_entity_id:
            raise Exception("外部實體模式需要設定度數實體 (degree_entity)")

        self.last_status = f"正在讀取 {degree_entity_id}..."
        state = self.hass.states.get(degree_entity_id)

        if state is None:
            raise Exception(f"找不到實體: {degree_entity_id}")

        value = state.state
        if value in ("unknown", "unavailable", None, ""):
            raise Exception(f"{degree_entity_id} 目前狀態無效: {value}")

        _LOGGER.info(f"從 {degree_entity_id} 讀取到度數: {value}")

        # 提取數字部分 (例如 sensor 可能帶有單位)
        match = re.search(r"(\d{4})", value)
        if match:
            return match.group(1)

        # 如果整個值就是數字
        cleaned = value.strip()
        if cleaned.isdigit():
            return cleaned

        _LOGGER.warning(f"從 {degree_entity_id} 取得的值無法解析為度數: {value}")
        return value

    async def _perform_ocr(self):
        """Call Google AI OCR service to recognize degree."""
        _LOGGER.info("正在啟動 Google AI OCR 辨識流程...")
        
        # 1. 準備圖片資料
        try:
            import os
            if not os.path.exists(DEFAULT_IMAGE_PATH):
                _LOGGER.error(f"找不到圖片檔案: {DEFAULT_IMAGE_PATH}")
                return None
                
            # 讀取圖片並轉換為 base64 (某些服務需要) 或直接傳路徑
            # 在 HA 官方 Google AI 整合中，我們通常使用 generate_content 服務
        except Exception as e:
            _LOGGER.error(f"處理圖片檔案失敗: {e}")
            return None

        # 2. 呼叫 Google Generative AI 服務
        # 註：這裡假設使用者已安裝官方的 google_generative_ai 整合
        prompt = self.config.get(CONF_PROMPT, DEFAULT_PROMPT)
        
        try:
            # 使用 HA 的服務呼叫方式
            # 官方整合通常會註冊在 google_generative_ai domain
            # 我們傳入圖片路徑讓 AI 讀取
            response = await self.hass.services.async_call(
                "google_generative_ai_conversation",
                "generate_content",
                {
                    "prompt": prompt,
                    "filenames": [DEFAULT_IMAGE_PATH],
                },
                blocking=True,
                return_response=True
            )
            
            if response and "text" in response:
                raw_result = response["text"]
                _LOGGER.info(f"AI 原始辨識結果: {raw_result}")
                
                # 使用正則表達式提取數字 (取前 4 位數字)
                import re
                match = re.search(r"(\d{4})", raw_result)
                if match:
                    ocr_result = match.group(1)
                    _LOGGER.info(f"成功提取度數: {ocr_result}")
                    return ocr_result
                else:
                    _LOGGER.warning(f"辨識結果中找不到 4 位數字: {raw_result}")
                    return None
            else:
                _LOGGER.error("Google AI 服務未回傳有效文字內容")
                return None
                
        except Exception as e:
            _LOGGER.error(f"呼叫 Google AI 服務時發生錯誤: {e}")
            return None

    async def _submit_to_slgas(self, degree):
        """The two-step POST logic."""
        url = "https://www.slgas.com.tw/GetDegree_SQL.asp"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        async with aiohttp.ClientSession(headers=headers) as session:
            # Step 1: POST for validation (ChkField=Check)
            payload1 = {
                "CusNo": self.config.get(CONF_CUS_NO, ""),
                "CusName": (self.config.get(CONF_CUS_NAME) or "").encode("big5"),
                "Cuscallno": self.config.get(CONF_CUS_PHONE, ""),
                "ChkField": "Check",
                "Send": "送出".encode("big5")
            }
            
            async with session.post(url, data=payload1) as resp1:
                if resp1.status != 200:
                    _LOGGER.error(f"Step 1 POST failed: {resp1.status}")
                    return False
                
                html1 = await resp1.text(encoding="big5", errors="ignore")
                soup = BeautifulSoup(html1, "html.parser")
                
                # Step 2: Prepare second POST (ChkField=Append)
                # Extract hidden fields or default values from Step 1 response
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
                
                async with session.post(url, data=payload2) as resp2:
                    if resp2.status != 200:
                        _LOGGER.error(f"Step 2 POST failed: {resp2.status}")
                        return False
                    
                    html2 = await resp2.text(encoding="big5", errors="ignore")
                    
                    # Check for success message
                    if "瓦斯錶度數已登錄完成" in html2:
                        _LOGGER.info("瓦斯度數上報成功！")
                        return True
                    else:
                        _LOGGER.warning("網站未顯示成功訊息，請檢查回傳內容。")
                        return False

    def _get_input_value(self, soup, name):
        """Extract value from input field by name."""
        tag = soup.find("input", {"name": name})
        return tag.get("value", "") if tag else ""

    async def _send_notification(self, degree):
        """Call the user-configured HA script for notification."""
        script_entity = self.config.get(CONF_NOTIFY_SCRIPT)
        if not script_entity:
            _LOGGER.debug("未設定通知腳本，略過通知")
            return

        try:
            # Read current value from input_text entity
            text_entity = self.config.get(CONF_TEXT_ENTITY)
            state = self.hass.states.get(text_entity)
            current_degree = state.state if state else degree

            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            message = f"\n{now_str}  目前瓦斯使用度數為:{current_degree}"

            # Call the script with message and image file
            await self.hass.services.async_call(
                "script",
                "turn_on",
                {
                    "entity_id": script_entity,
                    "variables": {
                        "message": message,
                        "data": {
                            "file": DEFAULT_IMAGE_PATH,
                        },
                    },
                },
                blocking=True,
            )
            _LOGGER.info(f"已呼叫通知腳本 {script_entity}")

        except Exception as e:
            _LOGGER.error(f"呼叫通知腳本失敗: {e}")

    def _add_to_history(self, degree, status):
        """Add record to history and keep within configured limit."""
        max_records = int(self.config.get(CONF_HISTORY_DAYS, DEFAULT_HISTORY_DAYS))
        
        now = datetime.now()
        today_str = now.strftime("%Y-%m-%d")
        now_full_str = now.strftime("%Y-%m-%d %H:%M:%S")
        
        # Check if we already have a record for today
        updated_index = -1
        for i, record in enumerate(self.history):
            if record["date"].startswith(today_str):
                updated_index = i
                break
        
        if updated_index != -1:
            # Update existing record and move to top (length stays same)
            record = self.history.pop(updated_index)
            record["date"] = now_full_str
            record["degree"] = degree
            record["status"] = status
            self.history.insert(0, record)
        else:
            # Add new record (length increases)
            record = {
                "date": now_full_str,
                "degree": degree,
                "status": status
            }
            self.history.insert(0, record)
            
            # Remove the oldest record if we exceed the limit
            if len(self.history) > max_records:
                self.history.pop()
