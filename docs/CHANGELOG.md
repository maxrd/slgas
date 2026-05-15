# SLGAS 更新日誌 (CHANGELOG)

**最後更新**: 2026-05-15

---

## [v1.2.0] - 2026-05-15

### 🎯 主題
完整的多公司、多工種支援整合 - 從單一瓦斯公司升級為通用能源自動回報平台

### ✨ 新增功能

#### 核心架構重構
- **多公司模組化支援**: 實現 Reporter 設計模式，支援動態加載不同公司的回報邏輯
- **工廠模式實現**: ReporterFactory 類別統一管理所有 Reporter 的註冊和初始化
- **模組化檔案結構**: 新增 `reporters/` 目錄，包含：
  - `base.py` - BaseReporter 抽象基類
  - `factory.py` - ReporterFactory 工廠類
  - `slgas.py` - SLGAS (欣隆天然瓦斯) Reporter 實作
  - `water_taipei.py` - 台灣自來水 Reporter 實作

#### 新增水錶支援
- **水錶配置流程**: 完整的水錶用戶配置工作流程
- **台灣自來水整合**: 支援直接提交到 Taiwan Water 官方網站
- **水號驗證**: 自動驗證水號格式 (XXX-XXX)
- **電郵驗證**: 驗證申請人電子郵件格式
- **水量感測器**: 新增 WATER 設備類別支援，整合 HA 能源面板

#### 動態配置流程 (Phase 4)
- **6 步驟設定流程**:
  1. `async_step_user()` - 選擇計量類型 (瓦斯/水)
  2. `async_step_company()` - 選擇公司 (動態過濾)
  3. `async_step_basic_info()` - 輸入基本資訊 (動態欄位)
  4. `async_step_ocr_config()` - 設定 OCR 來源 (Google AI/外部實體)
  5. `async_step_advanced()` - 進階選項 (通知、排程、歷史)
  6. `async_step_finish()` - 建立配置條目

- **動態欄位選擇**: 根據用戶選擇自動顯示/隱藏相關欄位
- **智能驗證**: 根據公司類型執行不同的驗證邏輯
- **OptionsFlow 更新**: 支援修改現有配置

#### 通用感測器和按鈕
- **UniversalMeterSensor**: 支援瓦斯和水錶兩種裝置類別
  - 動態裝置類別: `SensorDeviceClass.GAS` 或 `SensorDeviceClass.WATER`
  - 動態名稱和圖示: 根據計量類型自動調整

- **動態按鈕名稱**: 
  - 瓦斯: "確認並立即上報瓦斯度數"
  - 水錶: "確認並立即上報水錶度數"

#### 多帳戶支援
- 在同一整合下管理多個瓦斯帳戶或水錶帳戶
- 每個帳戶獨立的感測器、按鈕和排程
- 避免檔案衝突: 改進的圖片命名規範

### 🔧 改進

#### const.py
- 新增計量類型常數: `METER_TYPE_GAS`, `METER_TYPE_WATER`
- 新增公司常數: `COMPANY_SLGAS`, `COMPANY_WATER_TAIPEI`
- 新增水錶配置欄位:
  - `CONF_WATER_NO` - 水號
  - `CONF_APPLICANT_NAME` - 申請人名稱
  - `CONF_EMAIL` - 電子郵件
  - `CONF_PHONE` - 聯繫電話

- 新增 OCR 來源常數:
  - `OCR_SOURCE_GOOGLE_AI`
  - `OCR_SOURCE_EXTERNAL`

- 新增預設提示詞:
  - `DEFAULT_PROMPT_GAS` - 瓦斯表識別提示
  - `DEFAULT_PROMPT_WATER` - 水錶識別提示

#### report_service.py
- 新增 `_init_reporter()` 方法: 根據公司類型動態初始化 Reporter
- 改進 `_submit_to_slgas()`: 委派給 Reporter 物件處理
- 更新 `image_path` 屬性: 動態生成適應各公司的圖片名稱
  - 瓦斯: `slgas_gas_{company}_{cus_no}.png`
  - 水錶: `slgas_water_{water_no_clean}.png`

#### sensor.py
- 重新命名: `SlgasMeterSensor` → `UniversalMeterSensor`
- 新增 `meter_type` 參數
- 動態設備類別:
  - 水錶: `SensorDeviceClass.WATER`
  - 瓦斯: `SensorDeviceClass.GAS`
- 動態名稱和圖示

#### button.py
- 動態按鈕名稱根據 `meter_type` 變更
- 動態圖示根據計量類型變更

#### config_flow.py
- **完整重寫**: 從簡單的單步流程升級為 6 步驟複雜流程
- 實現狀態機模式: 步驟間資料保留
- 動態表單生成: 根據用戶選擇生成欄位
- 完整的欄位驗證:
  - 水號格式驗證: `^\d{1,3}-\d{1,3}$`
  - 電郵格式驗證: `^[^@]+@[^@]+\.[^@]+$`
  - 必填欄位檢查 (攝影機/外部實體)

- 新增 SlgasOptionsFlowHandler 類別: 支援修改現有配置

#### strings.json
- 完整繁體中文本地化
- 新增 6 步驟所有標籤
- 新增錯誤訊息本地化
- 新增欄位說明和提示

#### __init__.py
- 新增 Reporter 註冊邏輯:
  ```python
  ReporterFactory.register(COMPANY_SLGAS, SlgasReporter)
  ReporterFactory.register(COMPANY_WATER_TAIPEI, WaterTaipeiReporter)
  ```

### 📚 文檔

#### 新增文件
- **IMPLEMENTATION.md** (200+ 行)
  - 完整的技術實作指南
  - 架構圖和設計模式解釋
  - 檔案結構說明
  - 新增公司的步驟教程
  - 技術細節和最佳實踐

- **USER_GUIDE.md** (300+ 行)
  - 分步驟配置指南 (瓦斯和水錶)
  - 日常使用說明
  - 完整的故障排除指南
  - 進階配置教程
  - 常見問答

- **CHANGELOG.md** (本文件)
  - 版本更新歷史

#### 更新文件
- **README.md**
  - 更新標題為 "通用能源自動回報整合"
  - 擴展功能說明以支援水錶
  - 更新先決條件
  - 重寫配置部分說明 6 步驟流程
  - 新增能源面板水消耗配置
  - 擴展 FAQ

### 🐛 修復

#### 清理未使用的導入
- `report_service.py`: 移除 aiohttp, BeautifulSoup, 未使用的常數導入
- `sensor.py`: 優化導入，明確使用 METER_TYPE_GAS
- `button.py`: 確保所有導入都被使用

#### 驗證改進
- 修正電郵驗證: 從 `cv.is_email()` 改為正則表達式
- 改進水號驗證: 強制執行 XXX-XXX 格式
- 新增 OCR 來源必填欄位檢查

### 🏗️ 架構改進

#### 模組化設計
```
BaseReporter (抽象類)
├── SlgasReporter (SLGAS 實作)
└── WaterTaipeiReporter (台灣自來水實作)

ReporterFactory (工廠類)
├── register() - 註冊新 Reporter
└── get_reporter() - 取得 Reporter 實例
```

#### 擴展性
- 新增公司只需:
  1. 建立新 Reporter 類別 (繼承 BaseReporter)
  2. 在 __init__.py 註冊
  3. 在 config_flow.py 新增公司選項
  4. 在 strings.json 新增標籤

### 📋 技術細節

#### 向後相容性
- SlgasMeterSensor 保留為 UniversalMeterSensor 的別名
- 現有配置仍可使用，會自動升級

#### 狀態恢復
- RestoreEntity 實作保留最後度數狀態
- 支援 HA 重啟後的狀態恢復

#### 多步驟流程
- 使用字典存儲步驟間資料
- 動態表單生成基於累積的用戶選擇
- 完整的欄位驗證和錯誤處理

---

## [v1.1.0] - 2026-05-10

### ✨ 新增功能

#### 動態感測器和按鈕 (Phase 2-3)
- **SlgasOcrOnlyButton**: 新增手動 OCR 按鈕
- **動態實體名稱**: 根據公司和客戶號動態生成
- **狀態持久化**: RestoreEntity 支援狀態恢復

### 🔧 改進

#### report_service.py
- 新增 `last_error` 屬性: 追蹤最後錯誤
- 新增 `last_status` 屬性: 追蹤最後狀態
- 改進錯誤處理和日誌記錄

#### sensor.py
- 新增 `last_error` 屬性感測器
- 改進圖片路徑生成邏輯

### 📚 文檔
- 新增 Phase 3 完成報告

---

## [v1.0.0] - 2026-05-01

### 🎯 初始版本
支援欣隆天然瓦斯的自動度數辨識和上報

### ✨ 功能
- **Google Generative AI 整合**: 使用 AI 辨識瓦斯表度數
- **自動化排程**: 每日定時拍照和辨識
- **手動上報**: 確認度數後手動上報到欣隆網站
- **本地度數存儲**: 使用 input_text 存儲辨識結果
- **歷史追蹤**: 保留配置的天數內的上報紀錄
- **Home Assistant 整合**: 
  - 度數感測器
  - 上報狀態感測器
  - 確認並上報按鈕
  - 報表服務

### 🔧 技術特性
- **Config Flow**: 簡單的設定流程
- **SLGAS Reporter**: 基礎的欣隆瓦斯上報實作
- **OCR 整合**: Google Generative AI API 呼叫
- **錯誤處理**: 完整的異常捕捉和日誌

### 📦 檔案結構
```
custom_components/slgas/
├── __init__.py
├── const.py
├── config_flow.py
├── report_service.py
├── sensor.py
├── button.py
├── manifest.json
├── strings.json
└── reporters/
    ├── __init__.py
    └── slgas.py
```

---

## 版本對比

| 功能 | v1.0.0 | v1.1.0 | v1.2.0 |
|------|--------|--------|--------|
| 瓦斯支援 | ✅ | ✅ | ✅ |
| 水錶支援 | ❌ | ❌ | ✅ |
| 多公司支援 | ❌ (單公司) | ❌ | ✅ |
| Reporter 工廠模式 | ❌ | ❌ | ✅ |
| 6 步驟設定流程 | ❌ | ❌ | ✅ |
| 動態欄位驗證 | ❌ | ❌ | ✅ |
| 能源面板水消耗 | ❌ | ❌ | ✅ |
| 多帳戶支援 | ✅ | ✅ | ✅ |
| OCR 按鈕 | ❌ | ✅ | ✅ |
| 狀態恢復 | ❌ | ✅ | ✅ |

---

## 路線圖

### Phase 5: 實地測試 (進行中)
- [ ] 瓦斯配置流程測試
- [ ] 水錶配置流程測試
- [ ] 欄位驗證測試
- [ ] OptionsFlow 測試
- [ ] 台灣自來水 API 驗證

### 未來版本 (v1.3.0+)
- [ ] 大台北瓦斯公司支援
- [ ] 台中自來水公司支援
- [ ] 驗證碼交互優化
- [ ] 性能監控和優化
- [ ] 更多公司支援

---

**報告生成**: 2026-05-15
