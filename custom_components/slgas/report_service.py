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
    CONF_WATER_NUM1,
    CONF_WATER_NUM2,
    CONF_WATER_NUM3,
    OCR_SOURCE_GOOGLE_AI,
    OCR_SOURCE_EXTERNAL,
    DEFAULT_HISTORY_DAYS,
    DEFAULT_NOTIFY_TITLE_GAS,
    DEFAULT_NOTIFY_TITLE_WATER,
    DEFAULT_PROMPT,
    DEFAULT_IMAGE_DIR,
    METER_TYPE_GAS,
    METER_TYPE_WATER,
    METER_TYPE_ELECTRICITY,
    CONF_TAIPOWER_ID,
    CONF_DEGREE_DIFF_THRESHOLD,
    DEFAULT_DEGREE_DIFF_THRESHOLD,
    COMPANY_SLGAS,
)
from .reporters.factory import ReporterFactory
from .image_processor import preprocess_meter_image

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
    def _entry_label(self) -> str:
        """Return a readable identifier for this entry used in log messages."""
        if self.meter_type == METER_TYPE_WATER:
            n1 = self.config.get(CONF_WATER_NUM1, "")
            n2 = self.config.get(CONF_WATER_NUM2, "")
            n3 = self.config.get(CONF_WATER_NUM3, "")
            return f"{n1}-{n2}-{n3}" if n1 else self.entry.entry_id[:8]
        if self.meter_type == METER_TYPE_ELECTRICITY:
            return self.config.get(CONF_TAIPOWER_ID, self.entry.entry_id[:8])
        return self.config.get(CONF_CUS_NO, self.entry.entry_id[:8])

    @property
    def _meter_label(self) -> str:
        """Return Chinese name for this meter type."""
        return {METER_TYPE_WATER: "水錶", METER_TYPE_ELECTRICITY: "電力"}.get(self.meter_type, "瓦斯")

    @property
    def image_path(self) -> str:
        """Return per-entry snapshot path based on meter_type and company."""
        if self.meter_type == METER_TYPE_WATER:
            # 優先用新三段水號，fallback 舊 CONF_WATER_NO
            n1 = self.config.get(CONF_WATER_NUM1, "")
            n2 = self.config.get(CONF_WATER_NUM2, "")
            n3 = self.config.get(CONF_WATER_NUM3, "")
            if n1:
                water_id = f"{n1}{n2}{n3}"
            else:
                water_id = self.config.get(CONF_WATER_NO, self.entry.entry_id[:8]).replace("-", "")
            filename = f"slgas_water_{water_id}.png"
        elif self.meter_type == METER_TYPE_ELECTRICITY:
            taipower_id = self.config.get(CONF_TAIPOWER_ID, self.entry.entry_id[:8])
            filename = f"slgas_taipower_{taipower_id}.png"
        else:
            cus_no = self.config.get(CONF_CUS_NO, self.entry.entry_id[:8])
            filename = f"slgas_{cus_no}.png"

        return f"{DEFAULT_IMAGE_DIR}/{filename}"

    @property
    def config(self):
        """Return merged config (options + data)."""
        return {**self.entry.data, **self.entry.options}

    async def submit_current_degree(self):
        """確認並上報：若今天已有照片且有度數則直接上報，否則先拍照+OCR再上報。"""
        import os as _os
        cus_no = self._entry_label
        try:
            has_today_photo = (
                _os.path.exists(self.image_path) and
                datetime.fromtimestamp(_os.path.getmtime(self.image_path)).date() == datetime.now().date()
            )
            has_degree = (
                self.meter_sensor is not None and
                self.meter_sensor._attr_native_value is not None
            )

            if has_today_photo and has_degree:
                degree = str(self.meter_sensor._attr_native_value)
                _LOGGER.info(f"[{cus_no}] 今天已有照片和度數 ({degree})，直接上報")
            else:
                _LOGGER.info(f"[{cus_no}] 尚無今日照片或度數，先執行拍照+OCR")
                ocr_source = self.config.get(CONF_OCR_SOURCE, OCR_SOURCE_GOOGLE_AI)
                degree = (
                    await self._read_external_degree()
                    if ocr_source == OCR_SOURCE_EXTERNAL
                    else await self._google_ai_ocr()
                )
                if not degree or not degree.isdigit():
                    raise Exception(f"取得度數失敗 (結果: {degree})")
                anomaly_msg = self._check_degree_anomaly(int(degree))
                if anomaly_msg:
                    _LOGGER.warning(f"[{cus_no}] {anomaly_msg}")
                    self._update_status(f"⚠ {anomaly_msg}")
                    self._add_to_history(degree, self.last_status)
                    return
                if self.meter_sensor is not None:
                    self.meter_sensor.update_meter(int(degree))
                text_id = self.config.get(CONF_TEXT_ENTITY)
                if text_id:
                    await self.hass.services.async_call(
                        "input_text", "set_value",
                        {"entity_id": text_id, "value": degree},
                        blocking=True
                    )

            self._update_status(f"正在上報網站 (度數: {degree})...")
            success = await self._submit_to_slgas(degree)
            if success:
                self._update_status(f"上報成功: {degree}")
            else:
                self._update_status(f"回報失敗 (度數: {degree})")
            self._add_to_history(degree, self.last_status)
            await self._send_notification(degree)
        except Exception as e:
            _LOGGER.error(f"[{cus_no}] 手動上報出錯: {e}")
            self._update_status(f"錯誤: {str(e)}")
            self._add_to_history("N/A", self.last_status)

    def _check_degree_anomaly(self, new_degree: int) -> str | None:
        """若度數與上次相差超過閾值，回傳警告訊息；否則回傳 None（允許寫入）。"""
        # 優先從 input_text 讀取上次度數，使用者可手動修改基準值
        last = None
        text_id = self.config.get(CONF_TEXT_ENTITY)
        if text_id:
            state = self.hass.states.get(text_id)
            if state and state.state not in ("unknown", "unavailable", ""):
                last = state.state
        # fallback: 從 meter_sensor 讀取
        if last is None and self.meter_sensor is not None:
            last = self.meter_sensor._attr_native_value
        if last is None:
            return None
        try:
            last_int = int(last)
        except (ValueError, TypeError):
            return None
        if last_int == 0:
            # 上次為 0，跳過異常檢查
            return None
        if new_degree < last_int:
            return (
                f"OCR 度數異常 (上次: {last_int}，本次: {new_degree})，"
                "新度數小於目前度數，不允許回退，跳過寫入"
            )
        threshold = int(self.config.get(CONF_DEGREE_DIFF_THRESHOLD, DEFAULT_DEGREE_DIFF_THRESHOLD))
        diff = new_degree - last_int
        if diff > threshold:
            return (
                f"OCR 度數異常 (上次: {last_int}，本次: {new_degree}，差距: {diff}，閾值: {threshold})，"
                "可能因光線不足誤判，跳過寫入"
            )
        return None

    async def execute_full_workflow(self, submit: bool = True):
        """Execute the entire workflow based on OCR source setting."""
        cus_no = self._entry_label
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

            # 異常偵測：與上次度數差距超過 10 則跳過寫入
            anomaly_msg = self._check_degree_anomaly(int(ocr_degree))
            if anomaly_msg:
                _LOGGER.warning(f"[{cus_no}] {anomaly_msg}")
                self._update_status(f"⚠ {anomaly_msg}")
                self._add_to_history(ocr_degree, self.last_status)
                return

            # 優先更新原生能源感測器
            if self.meter_sensor is not None:
                self.meter_sensor.update_meter(int(ocr_degree))
                _LOGGER.info(f"[{cus_no}] 已更新{self._meter_label}度數感測器為 {ocr_degree}")

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
            _LOGGER.error(f"[{cus_no}] {self._meter_label}回報流程出錯: {e}")
            self._update_status(f"錯誤: {str(e)}")
            self._add_to_history("N/A", self.last_status)

    async def _google_ai_ocr(self):
        """Google AI mode: snapshot + OCR."""
        cus_no = self._entry_label
        camera_id = self.config.get(CONF_CAMERA_ENTITY)
        if not camera_id:
            raise Exception("Google AI 模式需要設定攝影機實體")

        import os as _os

        # 1. 確認目標目錄存在
        img_dir = _os.path.dirname(self.image_path)
        if not _os.path.isdir(img_dir):
            raise Exception(
                f"截圖目錄不存在: {img_dir}，"
                "請確認 HA 的 /media 已掛載（HAOS 預設存在；Container 需手動掛載）"
            )

        # 2. 拍照前若照片不是今天的則刪除
        if _os.path.exists(self.image_path):
            mod_date = datetime.fromtimestamp(_os.path.getmtime(self.image_path)).date()
            if mod_date != datetime.now().date():
                try:
                    _os.remove(self.image_path)
                    _LOGGER.info(f"[{cus_no}] 已刪除舊照片 ({mod_date}): {self.image_path}")
                except Exception as del_err:
                    _LOGGER.warning(f"[{cus_no}] 刪除舊照片失敗: {del_err}")

        # 3. 拍照
        self._update_status("正在拍攝照片...")
        _LOGGER.info(f"[{cus_no}] 正在拍攝 {camera_id}，存至 {self.image_path} ...")
        try:
            await self.hass.services.async_call(
                "camera",
                "snapshot",
                {"entity_id": camera_id, "filename": self.image_path},
                blocking=True
            )
        except Exception as snap_err:
            raise Exception(f"camera.snapshot 失敗 ({camera_id}): {snap_err}") from snap_err

        # 等待檔案完全寫入磁碟
        await asyncio.sleep(2)

        # 4. 確認檔案確實存在（camera.snapshot 路徑不合法時靜默失敗）
        if not _os.path.exists(self.image_path):
            raise Exception(
                f"截圖未存檔：{self.image_path} 不存在。"
                "camera.snapshot 可能因路徑權限問題靜默失敗，"
                "請在 configuration.yaml 加入: homeassistant.allowlist_external_dirs: /media"
            )
        _LOGGER.info(f"[{cus_no}] 截圖已確認存檔: {self.image_path}")

        # 5. 影像預處理（反光去除 + 對比強化）
        self._update_status("正在進行影像預處理...")
        await self.hass.async_add_executor_job(
            preprocess_meter_image, self.image_path
        )

        # 6. AI OCR
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
            media_id = f"media-source://media_source/local/{filename}"
            service_data = {
                "task_name": "gas ai",
                "entity_id": "ai_task.google_ai_task",
                "attachments": {
                    "media_content_id": media_id,
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
            }
            _LOGGER.info(
                f"呼叫 ai_task.generate_data: media_id={media_id}, "
                f"content_type={content_type}, filename={filename}"
            )

            response = await self.hass.services.async_call(
                "ai_task",
                "generate_data",
                service_data,
                blocking=True,
                return_response=True
            )

            _LOGGER.info(f"ai_task 回應: {response}")

            # 解析回應 - 支援多種結構
            raw_result = None
            if isinstance(response, dict):
                # 嘗試頂層 text，再嘗試 data.text
                raw_result = response.get("text")
                if not raw_result:
                    data = response.get("data")
                    if isinstance(data, dict):
                        raw_result = data.get("text")
                    elif isinstance(data, str):
                        raw_result = data

            if not raw_result:
                _LOGGER.error(f"Google AI 服務未回傳有效文字, 完整回應: {response}")
                return None

            _LOGGER.info(f"AI 原始辨識結果: {raw_result}")

            # 尋找所有數字序列，選取最長的，並轉為整數以移除前導 0
            import re
            matches = re.findall(r"(\d+)", raw_result)
            if matches:
                ocr_result = str(int(max(matches, key=len)))
                _LOGGER.info(f"成功提取度數: {ocr_result}")
                return ocr_result
            else:
                _LOGGER.warning(f"辨識結果中找不到數字: {raw_result}")
                return None

        except Exception as e:
            _LOGGER.error(f"呼叫 Google AI 服務時發生錯誤: {e}", exc_info=True)
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
