# SLGAS 水表模組化實作進度報告
## Phase 1-3 完成總結

**更新日期**: 2026-05-15  
**完成狀態**: ✅ Phase 1-3 完成 (基礎設施 + Sensor + Button 動態化)  
**下一階段**: Phase 4 - Config Flow 多步驟流程設計

---

## 📋 已完成的工作

### Phase 1️⃣: 基礎設施 ✅

#### 1.1 常數定義 (const.py)
```python
# 新增常數
METER_TYPE_GAS = "gas"
METER_TYPE_WATER = "water"
COMPANY_SLGAS = "slgas"
COMPANY_WATER_TAIPEI = "water_taipei"

# 水錶相關欄位
CONF_WATER_NO = "water_no"
CONF_APPLICANT_NAME = "applicant_name"
CONF_EMAIL = "email"
CONF_PHONE = "phone"
```

#### 1.2 Reporter 架構
- ✅ `reporters/base.py` - BaseReporter 標準接口
- ✅ `reporters/factory.py` - ReporterFactory 工廠模式
- ✅ `reporters/slgas.py` - 欣隆瓦斯模組 (重構完成)
- ✅ `reporters/water_taipei.py` - 台灣自來水模組框架
- ✅ `reporters/__init__.py` - 包初始化

#### 1.3 整合點
- ✅ `__init__.py` - 註冊所有 Reporters
- ✅ `report_service.py` - 使用工廠模式加載 Reporter

---

### Phase 2️⃣: Sensor 動態化 ✅

#### 2.1 UniversalMeterSensor 
```python
class UniversalMeterSensor(SensorEntity, RestoreEntity):
    """支援瓦斯和水錶的通用感應器"""
    
    # 根據 meter_type 動態設定：
    # - device_class (SensorDeviceClass.GAS / .WATER)
    # - name (瓦斯度數 / 水錶度數)
    # - icon (mdi:counter / mdi:water)
```

**關鍵實現**:
- ✅ 支援 `device_class = WATER` (能源面板支援)
- ✅ `state_class = TOTAL_INCREASING` (單調遞增)
- ✅ 單位: `m³`
- ✅ RestoreEntity 狀態恢復

#### 2.2 SlgasReportSensor
- ✅ 動態狀態名稱（根據 meter_type）
- ✅ 動態圖示

#### 2.3 向後相容性
```python
# 別名支援現有程式碼
SlgasMeterSensor = UniversalMeterSensor
```

---

### Phase 3️⃣: Button 動態化 ✅

#### 3.1 SlgasManualReportButton
```python
# 根據 meter_type 動態設定：
# - 瓦斯: "確認並立即上報瓦斯度數" (icon: mdi:send-check)
# - 水: "確認並立即上報水錶度數" (icon: mdi:water)
```

#### 3.2 SlgasOcrOnlyButton
- ✅ 動態名稱和圖示

---

## 📁 檔案結構更新

```
custom_components/slgas/
├── reporters/                           [新增目錄]
│   ├── __init__.py
│   ├── base.py                         [基礎類]
│   ├── factory.py                      [工廠模式]
│   ├── slgas.py                        [欣隆重構]
│   └── water_taipei.py                 [台水框架]
├── __init__.py                         [✏️ 改: 註冊reporters]
├── button.py                           [✏️ 改: 動態按鈕]
├── config_flow.py                      [待實作: Phase 4]
├── const.py                            [✏️ 改: 新增常數]
├── report_service.py                   [✏️ 改: 整合工廠模式]
├── sensor.py                           [✏️ 改: 動態device_class]
└── manifest.json                       [無變更]
```

---

## 🔍 核心改動摘要

### report_service.py
```python
# 新增初始化邏輯
def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
    self.meter_type = entry.data.get(CONF_METER_TYPE, METER_TYPE_GAS)
    self.company = entry.data.get(CONF_COMPANY, COMPANY_SLGAS)
    self.reporter = self._init_reporter()  # 動態加載

def _init_reporter(self):
    """根據公司初始化 Reporter"""
    return ReporterFactory.get_reporter(self.hass, self.company, config)

# 簡化的上報方法
async def _submit_to_slgas(self, degree):
    """使用 Reporter 上報（支援多公司）"""
    success = await self.reporter.submit(degree, self.image_path)
    self.last_status = self.reporter.last_status
    return success
```

### 圖片命名規範
```python
# 瓦斯: slgas_gas_<company>_<cus_no>.png
# 水: slgas_water_<water_no_clean>.png
```

---

## ✅ 驗證檢查清單

- ✅ `const.py` 包含所有新增常數
- ✅ Reporter 類別都繼承 BaseReporter
- ✅ Factory 模式正確註冊
- ✅ report_service 正確初始化 reporter
- ✅ sensor.py 動態設定 device_class
- ✅ button.py 動態設定名稱
- ✅ 無循環導入問題
- ✅ 向後相容性保留

---

## 🚨 尚未完成的項目

### Phase 4️⃣: Config Flow 多步驟流程 (待實作)
- [ ] 步驟 1: 選擇 meter_type (gas/water)
- [ ] 步驟 2: 選擇公司 (動態過濾)
- [ ] 步驟 3: 基本資訊 (動態欄位)
- [ ] 步驟 4: OCR 設定
- [ ] 步驟 5: 驗證碼 (僅水錶，可選)
- [ ] 步驟 6: 進階選項

### Phase 4 的關鍵任務
```
config_flow.py 需要實現：
1. async_step_meter_type() - 選擇類型
2. async_step_company() - 選擇公司（根據類型過濾）
3. async_step_basic_info() - 基本資訊（動態欄位）
4. async_step_ocr_config() - OCR 設定
5. async_step_captcha() - 驗證碼（水錶專用）
6. async_step_advanced() - 進階選項
```

---

## 🧪 建議的測試步驟 (Phase 4 前)

1. **導入測試**
   ```bash
   python3 -c "from custom_components.slgas.reporters.factory import ReporterFactory; print(ReporterFactory.list_reporters())"
   ```
   預期輸出: `{'slgas': 'SlgasReporter', 'water_taipei': 'WaterTaipeiReporter'}`

2. **實例化測試**
   ```python
   from custom_components.slgas.reporters.factory import ReporterFactory
   reporter = ReporterFactory.get_reporter(hass, "slgas", config)
   assert reporter.validate_config()
   ```

3. **現有功能回歸測試**
   - 確保欣隆瓦斯上報仍然正常
   - 測試現有度數感測器恢復狀態功能

---

## 📝 接下來的優先順序

### 立即進行 (高優先)
1. **實現 Config Flow** (Phase 4)
   - 這是連接 UI 和新功能的關鍵
   - 預計 2-3 天完成

2. **測試現有瓦斯功能**
   - 確保向後相容性
   - 預計 0.5 天

### 後續 (中優先)
3. **實地驗證 Taiwan Water API**
   - 確認表單欄位名稱
   - 確認 POST 端點和成功訊息
   - 預計 1-2 天

4. **驗證碼處理方案**
   - 實現 UI 交互（手動輸入）
   - 預計 1 天

5. **完整端到端測試** (Phase 4)
   - 新建瓦斯條目
   - 新建水錶條目
   - 測試上報流程
   - 預計 2-3 天

---

## 🎯 當前里程碑

```
[████████░░░░░░░░░░] 40% 完成

✅ Phase 1: 基礎設施
✅ Phase 2: Sensor 動態化  
✅ Phase 3: Button 動態化
⏳ Phase 4: Config Flow (進行中)
⏳ Phase 5: 實地測試 (待開始)
```

---

## 💡 技術亮點

1. **Factory 模式** - 輕鬆添加新公司支援
2. **動態 Device Class** - 正確的能源面板支援
3. **圖片命名規範** - 避免多條目衝突
4. **向後相容性** - 現有瓦斯配置無縫升級

---

## 📞 下一步確認項目

在進行 Phase 4 (Config Flow) 之前，需要確認：

- [ ] 台灣自來水的表單字段名稱（申請人、水號等）
- [ ] POST 端點是否為 `/ch/ECounter/Apply`
- [ ] 驗證碼圖片如何取得（直接 URL 或需截圖）
- [ ] 成功訊息的確切文本
- [ ] HA Config Flow 是否支援在步驟中顯示圖片

---

**報告生成時間**: 2026-05-15  
**下一個更新**: Phase 4 Config Flow 實現完成後
