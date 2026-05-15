"""Report service for slgas."""
import logging
import re
import asyncio
from datetime import datetime

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .const import (
    CONF_CUS_NO,
    CONF_CAMERA_ENTITY,
    CONF_TEXT_ENTITY,
    CONF_NOTIFY_SCRIPT,
    CONF_NOTIFY_TITLE,
    CONF_HISTORY_DAYS,
    CONF_PROMPT,
    CONF_OCR_SOURCE,
    CONF_DEGREE_ENTITY,
    CONF_METER_TYPE,
    CONF_COMPANY,
    CONF_WATER_NO,
    OCR_SOURCE_GOOGLE_AI,
    OCR_SOURCE_EXTERNAL,
    DEFAULT_HISTORY_DAYS,
    DEFAULT_NOTIFY_TITLE_GAS,
    DEFAULT_NOTIFY_TITLE_WATER,
    DEFAULT_PROMPT,
    DEFAULT_IMAGE_DIR,
    METER_TYPE_GAS,
    METER_TYPE_WATER,
    COMPANY_SLGAS,
)
from .reporters.factory import ReporterFactory

_LOGGER = logging.getLogger(__name__)

class SlgasReportService:
    """Handle the reporting workflow."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        self.hass = hass
        self.entry = entry
        self.history = []
        self.last_status = "尚未執行"
        self.meter_sensor = None   # 由 sensor.py 設定引用
        self.status_sensor = None  # 由 sensor.py 設定引用

        # 初始化 Reporter（支持多公司）
        self.meter_type = entry.data.get(CONF_METER_TYPE, METER_TYPE_GAS)
        self.company = entry.data.get(CONF_COMPANY, COMPANY_SLGAS)
        self.reporter = self._init_reporter()

    def _init_reporter(self):
        """根據公司初始化 Reporter"""
        try:
            config_with_image_path = {
                **self.config,
                "image_path": self.image_path
            }
            reporter = ReporterFactory.get_reporter(
                self.hass,
                self.company,
                config_with_image_path
            )
            _LOGGER.info(f"已初始化 {self.company} Reporter")
            return reporter
        except ValueError as e:
            _LOGGER.error(f"無法初始化 Reporter: {e}")
            raise

    def _update_status(self, msg: str) -> None:
        """Update last_status and push state to HA immediately."""
        self.last_status = msg
        if self.status_sensor is not None:
            self.status_sensor.async_write_ha_state()

    @property
    def image_path(self) -> str:
        """Return per-entry snapshot path based on meter_type and company."""
        if self.meter_type == METER_TYPE_WATER:
            # 水錶: slgas_water_<water_no>.png
            water_no = self.config.get(CONF_WATER_NO, self.entry.entry_id[:8])
            water_no_clean = water_no.replace("-", "")  # 移除格式符號
            filename = f"slgas_water_{water_no_clean}.png"
        else:
            # 瓦斯: slgas_gas_<company>_<cus_no>.png
            cus_no = self.config.get(CONF_CUS_NO, self.entry.entry_id[:8])
            filename = f"slgas_gas_{self.company}_{cus_no}.png"

        return f"{DEFAULT_IMAGE_DIR}/{filename}"

    @property
    def config(self):
        """Return merged config (options + data)."""
        return {**self.entry.data, **self.entry.options}

    async def execute_full_workflow(self, submit: bool = True):
        """Execute the entire workflow based on OCR source setting."""
        cus_no = self.config.get(CONF_CUS_NO, self.entry.entry_id[:6])
        try:
            ocr_source = self.config.get(CONF_OCR_SOURCE, OCR_SOURCE_GOOGLE_AI)
            _LOGGER.info(f"[{cus_no}] 開始執行流程 (submit={submit}, ocr_source={ocr_source})")

            if ocr_source == OCR_SOURCE_EXTERNAL:
                # === 外部實體模式：直接讀取 degree_entity 的值 ===
                ocr_degree = await self._read_external_degree()
            else:
                # === Google AI 模式：拍照 + AI OCR ===
                ocr_degree = await self._google_ai_ocr()

            # 驗證度數是否為有效數字
            if not ocr_degree or not ocr_degree.isdigit():
                raise Exception(f"取得度數失敗 (結果: {ocr_degree})")

            # 優先更新原生能源感測器
            if self.meter_sensor is not None:
                self.meter_sensor.update_meter(int(ocr_degree))
                _LOGGER.info(f"[{cus_no}] 已更新原生瓦斯度數感測器為 {ocr_degree}")

            # 選填：同步寫入 text_entity (若有設定)
            text_id = self.config.get(CONF_TEXT_ENTITY)
            if text_id:
                await self.hass.services.async_call(
                    "input_text",
                    "set_value",
                    {"entity_id": text_id, "value": ocr_degree},
                    blocking=True
                )
                _LOGGER.info(f"[{cus_no}] 已同步更新 {text_id} 為 {ocr_degree}")

            # 上報或待確認
            if submit:
                self._update_status(f"正在上報網站 (度數: {ocr_degree})...")
                success = await self._submit_to_slgas(ocr_degree)
                if success:
                    self._update_status(f"上報成功: {ocr_degree}")
                else:
                    self._update_status(f"回報失敗 (度數: {ocr_degree})")
            else:
                self._update_status(f"辨識完成: {ocr_degree} (待確認)")
                _LOGGER.info(f"[{cus_no}] 已完成取得度數 ({ocr_degree})，跳過自動上報。")

            self._add_to_history(ocr_degree, self.last_status)

            # 發送通知
            await self._send_notification(ocr_degree)

        except Exception as e:
            _LOGGER.error(f"[{cus_no}] 瓦斯回報流程出錯: {e}")
            self._update_status(f"錯誤: {str(e)}")
            self._add_to_history("N/A", self.last_status)

    async def _google_ai_ocr(self):
        """Google AI mode: snapshot + OCR."""
        cus_no = self.config.get(CONF_CUS_NO, self.entry.entry_id[:6])
        camera_id = self.config.get(CONF_CAMERA_ENTITY)
        if not camera_id:
            raise Exception("Google AI 模式需要設定攝影機實體")

        # 1. 拍照
        self._update_status("正在拍攝照片...")
        _LOGGER.info(f"[{cus_no}] 正在拍攝 {camera_id} ...")
        try:
            await self.hass.services.async_call(
                "camera",
                "snapshot",
                {"entity_id": camera_id, "filename": self.image_path},
                blocking=True
            )
        except Exception as snap_err:
            raise Exception(f"camera.snapshot 失敗 ({camera_id}): {snap_err}") from snap_err
        _LOGGER.info(f"[{cus_no}] 已拍攝照片並存於 {self.image_path}")

        # 等待檔案完全寫入磁碟
        await asyncio.sleep(2)

        # 2. AI OCR
        self._update_status("正在進行 AI OCR 辨識...")
        return await self._perform_ocr()

    async def _read_external_degree(self):
        """External mode: read degree from degree_entity."""
        degree_entity_id = self.config.get(CONF_DEGREE_ENTITY)
        if not degree_entity_id:
            raise Exception("外部實體模式需要設定度數實體 (degree_entity)")

        self._update_status(f"正在讀取 {degree_entity_id}...")
        state = self.hass.states.get(degree_entity_id)

        if state is None:
            raise Exception(f"找不到實體: {degree_entity_id}")

        value = state.state
        if value in ("unknown", "unavailable", None, ""):
            raise Exception(f"{degree_entity_id} 目前狀態無效: {value}")

        _LOGGER.info(f"從 {degree_entity_id} 讀取到度數: {value}")

        # 提取數字部分 (例如 sensor 可能帶有單位)
        matches = re.findall(r"(\d+)", value)
        if matches:
            # 取得最長的數字序列並轉為整數（移除所有前導 0）
            return str(int(max(matches, key=len)))

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
        import os
        if not os.path.exists(self.image_path):
            _LOGGER.error(f"找不到圖片檔案: {self.image_path}")
            return None

        # 2. 呼叫 AI 任務服務
        prompt = self.config.get(CONF_PROMPT, DEFAULT_PROMPT)
        filename = os.path.basename(self.image_path)
        content_type = "image/jpeg" if filename.lower().endswith((".jpg", ".jpeg")) else "image/png"

        try:
            response = await self.hass.services.async_call(
                "ai_task",
                "generate_data",
                {
                    "task_name": "gas ai",
                    "entity_id": "ai_task.google_ai_task",
                    "attachments": {
                        "media_content_id": f"media-source://media_source/local/{filename}",
                        "media_content_type": content_type,
                        "metadata": {
                            "title": filename,
                            "thumbnail": None,
                            "media_class": "image",
                            "children_media_class": None,
                            "navigateIds": [
                                {},
                                {
                                    "media_content_type": "app",
                                    "media_content_id": "media-source://media_source"
                                }
                            ]
                        }
                    },
                    "instructions": prompt,
                },
                blocking=True,
                return_response=True
            )
            
            if response and "text" in response:
                raw_result = response["text"]
                _LOGGER.info(f"AI 原始辨識結果: {raw_result}")
                
                # 尋找所有數字序列，選取最長的，並轉為整數以移除前導 0
                import re
                matches = re.findall(r"(\d+)", raw_result)
                if matches:
                    # 取得最長序列 (避免雜訊) 並轉為整數 (移除 0001 -> 1)
                    ocr_result = str(int(max(matches, key=len)))
                    _LOGGER.info(f"成功提取度數: {ocr_result} (原始結果: {raw_result})")
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
        """使用 Reporter 上報度數 (支援多公司)"""
        success = await self.reporter.submit(degree, self.image_path)
        self.last_status = self.reporter.last_status
        return success

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
            message = f"\n{now_str}  目前度數為:{current_degree}"

            # Get notification title based on meter type and config
            if self.meter_type == METER_TYPE_WATER:
                default_title = DEFAULT_NOTIFY_TITLE_WATER
            else:
                default_title = DEFAULT_NOTIFY_TITLE_GAS

            notify_title = self.config.get(CONF_NOTIFY_TITLE, default_title)

            # Call the script with message and image file
            await self.hass.services.async_call(
                "script",
                "turn_on",
                {
                    "entity_id": script_entity,
                    "variables": {
                        "title": notify_title,
                        "message": message,
                        "data": {
                            "file": self.image_path,
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
