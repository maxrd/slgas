# SLGAS 實裝說明書 (Implementation Guide)

**版本**: v1.2.0  
**最後更新**: 2026-05-15  
**目標讀者**: 開發者、維護人員

---

## 📋 目錄

1. [架構概覽](#架構概覽)
2. [模組化設計](#模組化設計)
3. [新增檔案](#新增檔案)
4. [修改的檔案](#修改的檔案)
5. [核心概念](#核心概念)
6. [擴展新公司](#擴展新公司)
7. [技術細節](#技術細節)

---

## 架構概覽

### 高層設計

```
┌─────────────────────────────────────────────┐
│         Home Assistant Integration          │
└──────────────────┬──────────────────────────┘
                   │
         ┌─────────┴─────────┐
         │                   │
    ┌────▼────┐        ┌────▼────┐
    │  Config │        │ Sensors │
    │  Flow   │        │ Buttons │
    └────┬────┘        └────┬────┘
         │                  │
         └──────────┬───────┘
                    │
        ┌───────────▼────────────┐
        │  Report Service        │
        │  (統一工作流程)         │
        └───────────┬────────────┘
                    │
        ┌───────────▼────────────┐
        │  Reporter Factory      │
        │  (動態加載)             │
        └───────────┬────────────┘
                    │
         ┌──────────┴──────────┐
         │                     │
    ┌────▼─────┐      ┌────────▼──┐
    │  SLGAS   │      │   Water   │
    │ Reporter │      │ Taipei    │
    │          │      │ Reporter  │
    └──────────┘      └───────────┘
         │                   │
    ┌────▼─────┐      ┌────────▼──┐
    │ SLGAS    │      │  Taiwan   │
    │ Website  │      │  Water    │
    │ API      │      │ Website   │
    └──────────┘      └───────────┘
```

---

## 模組化設計

### Reporter 模式

本整合使用 **Reporter 設計模式** 支援多公司：

```python
# 基礎接口
class BaseReporter(ABC):
    async def submit(self, degree: str, image_path: str) -> bool:
        """提交度數到遠端"""
        pass

# 具體實現
class SlgasReporter(BaseReporter):
    """欣隆瓦斯實裝"""
    
class WaterTaipeiReporter(BaseReporter):
    """台灣自來水實裝"""
```

### Factory 模式

工廠類動態加載對應的 Reporter：

```python
class ReporterFactory:
    @classmethod
    def get_reporter(cls, hass, company: str, config: dict) -> BaseReporter:
        reporter_class = cls._reporters.get(company)
        return reporter_class(hass, config)
```

---

## 新增檔案

### `reporters/` 目錄結構

```
reporters/
├── __init__.py              # 包初始化
├── base.py                  # BaseReporter 基礎類
├── factory.py               # ReporterFactory 工廠類
├── slgas.py                 # SLGAS 實作
└── water_taipei.py          # 台灣自來水實作
```

### 各檔案詳解

#### `base.py` - 基礎接口

定義所有 Reporter 必須實現的接口：

```python
class BaseReporter(ABC):
    """基礎 Reporter 類"""
    
    @abstractmethod
    async def submit(self, degree: str, image_path: str = None) -> bool:
        """上報度數到遠端伺服器"""
        pass
    
    def validate_config(self) -> bool:
        """驗證配置完整性"""
        pass
    
    def get_required_fields(self) -> list:
        """回傳此公司需要的欄位"""
        pass
```

#### `factory.py` - 工廠類

動態註冊和加載 Reporter：

```python
class ReporterFactory:
    _reporters = {}  # 已註冊的 Reporter
    
    @classmethod
    def register(cls, company: str, reporter_class):
        """註冊新 Reporter"""
        cls._reporters[company] = reporter_class
    
    @classmethod
    def get_reporter(cls, hass, company: str, config: dict):
        """根據公司名稱取得 Reporter 實例"""
        return cls._reporters[company](hass, config)
```

#### `slgas.py` - 欣隆實作

實現欣隆瓦斯的兩段階提交流程：

```python
class SlgasReporter(BaseReporter):
    async def submit(self, degree: str, image_path: str = None) -> bool:
        # Step 1: 驗證身份 (ChkField=Check)
        # Step 2: 寫入度數 (ChkField=Append)
        # 檢查成功訊息
```

#### `water_taipei.py` - 台灣自來水實作

實現台灣自來水的上報流程：

```python
class WaterTaipeiReporter(BaseReporter):
    async def submit(self, degree: str, image_path: str = None) -> bool:
        # 構建 multipart/form-data
        # 上傳圖片和資訊
        # 檢查成功訊息
```

---

## 修改的檔案

### `const.py` - 新增常數

```python
# Meter 類型
METER_TYPE_GAS = "gas"
METER_TYPE_WATER = "water"

# 公司
COMPANY_SLGAS = "slgas"
COMPANY_WATER_TAIPEI = "water_taipei"

# 水錶欄位
CONF_WATER_NO = "water_no"
CONF_APPLICANT_NAME = "applicant_name"
CONF_EMAIL = "email"

# Prompt 範本
DEFAULT_PROMPT_GAS = "..."
DEFAULT_PROMPT_WATER = "..."
```

### `__init__.py` - 註冊 Reporters

```python
from .reporters.factory import ReporterFactory
from .reporters.slgas import SlgasReporter
from .reporters.water_taipei import WaterTaipeiReporter

# 在模組載入時註冊
ReporterFactory.register(COMPANY_SLGAS, SlgasReporter)
ReporterFactory.register(COMPANY_WATER_TAIPEI, WaterTaipeiReporter)
```

### `report_service.py` - 整合 Factory

```python
class SlgasReportService:
    def __init__(self, hass, entry):
        self.meter_type = entry.data.get(CONF_METER_TYPE, METER_TYPE_GAS)
        self.company = entry.data.get(CONF_COMPANY, COMPANY_SLGAS)
        self.reporter = self._init_reporter()  # 動態初始化
    
    def _init_reporter(self):
        """根據公司初始化 Reporter"""
        return ReporterFactory.get_reporter(
            self.hass,
            self.company,
            self.config
        )
```

### `sensor.py` - 動態 Device Class

```python
class UniversalMeterSensor(SensorEntity):
    def __init__(self, report_service, entry, meter_type="gas"):
        if meter_type == METER_TYPE_WATER:
            self._attr_device_class = SensorDeviceClass.WATER
        else:
            self._attr_device_class = SensorDeviceClass.GAS
```

### `button.py` - 動態按鈕名稱

```python
class SlgasManualReportButton(ButtonEntity):
    def __init__(self, report_service, entry):
        meter_type = entry.data.get(CONF_METER_TYPE)
        if meter_type == METER_TYPE_WATER:
            self._attr_name = "確認並立即上報水錶度數"
        else:
            self._attr_name = "確認並立即上報瓦斯度數"
```

### `config_flow.py` - 6 步驟流程

完整重寫，實現：
1. `async_step_user()` - 選擇類型
2. `async_step_company()` - 選擇公司
3. `async_step_basic_info()` - 基本資訊
4. `async_step_ocr_config()` - OCR 設定
5. `async_step_advanced()` - 進階選項

---

## 核心概念

### 圖片命名規範

```python
# 瓦斯
slgas_gas_{company}_{cus_no}.png

# 水錶
slgas_water_{water_no_clean}.png
```

好處：
- 避免多條目檔案衝突
- 易於追蹤和識別

### 動態欄位選擇

Config Flow 根據用戶選擇動態顯示欄位：

```python
# 步驟 3: 根據 company 動態生成欄位
if company == COMPANY_WATER_TAIPEI:
    # 顯示水號、申請人等欄位
else:
    # 顯示客戶號、名稱等欄位
```

### Unique ID 策略

```python
# 瓦斯：使用客戶號
unique_id = config.get(CONF_CUS_NO)
title = f"⛽ 瓦斯 ({unique_id})"

# 水：使用水號
unique_id = config.get(CONF_WATER_NO)
title = f"💧 水錶 ({unique_id})"
```

---

## 擴展新公司

### 步驟 1: 建立新 Reporter

```python
# reporters/taipeigas.py
from .base import BaseReporter

class TaipeiGasReporter(BaseReporter):
    BASE_URL = "https://www.taipeigas.com.tw"
    
    async def submit(self, degree: str, image_path: str = None) -> bool:
        # 實現大台北瓦斯的上報邏輯
        pass
    
    def validate_config(self) -> bool:
        # 驗證必要欄位
        pass
    
    def get_required_fields(self) -> list:
        return ["cus_no", "cus_name", "cus_phone"]
```

### 步驟 2: 在 __init__.py 註冊

```python
from .reporters.taipeigas import TaipeiGasReporter

ReporterFactory.register("taipeigas", TaipeiGasReporter)
```

### 步驟 3: 在 const.py 新增常數

```python
COMPANY_TAIPEIGAS = "taipeigas"
```

### 步驟 4: 更新 config_flow.py

```python
async def async_step_company(self, user_input=None):
    if self.meter_type == METER_TYPE_GAS:
        companies = {
            COMPANY_SLGAS: "欣隆天然瓦斯",
            COMPANY_TAIPEIGAS: "大台北瓦斯",  # 新增
        }
```

### 步驟 5: 更新 strings.json

新增大台北瓦斯的欄位標籤。

---

## 技術細節

### Reporter 中的異常處理

```python
async def submit(self, degree: str, image_path: str = None) -> bool:
    try:
        # 嘗試上報
        return True
    except FileNotFoundError:
        self.last_status = "錯誤: 找不到圖片"
        return False
    except Exception as e:
        self.last_status = f"錯誤: {str(e)}"
        return False
```

### RestoreEntity 狀態恢復

```python
class UniversalMeterSensor(SensorEntity, RestoreEntity):
    async def async_added_to_hass(self):
        """啟動時恢復上次狀態"""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state:
            self._attr_native_value = int(last_state.state)
```

### 多步驟 Config Flow

```python
async def async_step_basic_info(self, user_input=None):
    if user_input is not None:
        # 儲存此步驟資料
        self._user_input.update(user_input)
        # 進入下一步驟
        return await self.async_step_ocr_config()
```

---

## 相關資源

- [Home Assistant 開發文檔](https://developers.home-assistant.io/)
- [Config Entries 文檔](https://developers.home-assistant.io/docs/config_entries_config_flow_handler)
- [Sensor 平台文檔](https://developers.home-assistant.io/docs/core/entity/sensor)

---

**報告生成**: 2026-05-15
