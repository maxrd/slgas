[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub release](https://img.shields.io/github/release/maxrd/slgas.svg)](https://github.com/maxrd/slgas/releases/)
[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://github.com/maxrd/slgas/graphs/commit-activity)

# 通用能源自動回報整合 (Universal Utility Reporter)

### Home Assistant 自定義組件 - 支援瓦斯與水錶自動申報

本插件提供**模組化架構**，支援多家公司的度數申報。目前已支援：
- ⛽ **欣隆天然瓦斯** (SLGAS)
- 💧 **台灣自來水** (Taiwan Water)
- ⚡ **台灣電力公司** (Taipower) *(上報功能開發中)*

能夠自動化每日的度數申報流程，並可直接整合 Home Assistant 能源面板追蹤消耗。

---

## ✨ 主要功能

### 🏭 模組化多公司支援
*   **工廠模式架構**：輕鬆新增其他公司支援（大台北瓦斯、台中水務等）。
*   **同一整合多條目**：在同一個整合下配置多個瓦斯/水錶帳戶。

### 📊 瓦斯與水錶皆支援
*   **瓦斯表** (`device_class: gas`, 單位 `m³`)
*   **水錶** (`device_class: water`, 單位 `m³`)
*   兩者均支援能源面板長期統計。

### 🎯 雙模式度數來源
*   **Google AI OCR 模式**：攝影機拍照 + AI 自動辨識度數。
*   **外部實體模式**：直接讀取現有的 `sensor` / `input_text` 實體。

### ⏰ 自動排程與手動控制
*   **每日定時執行**：自動拍照和辨識，但不自動上報（需手動確認）。
*   **手動快速按鈕**：一鍵執行「拍照 → 辨識 → 上報」完整流程。
*   **分段執行**：可分別執行「僅辨識」或「完整上報」。

### 📈 歷史紀錄與追蹤
*   **歷史保留**：預設保留 90 天回報記錄，可自訂（1～365 天）。
*   **重啟資料保留**：HA 重啟後自動恢復上次度數。

### 🔔 通知與整合
*   **自訂通知腳本**：回報完成後可發送推播、Telegram 等通知。
*   **能源面板整合**：度數感測器原生支援 HA 能源面板。

---

## 預先準備 (Pre-requisites)

在使用本插件前，請確保您的 Home Assistant 已具備以下條件：

### 瓦斯表配置

#### Google AI 模式
1.  **Google Generative AI 整合**：請先在 HA 中設定好官方的 Google Generative AI 整合。
2.  **瓦斯表攝影機**：已接入 Home Assistant 並可正常拍照。
3.  **input_text 實體**：用於存放辨識結果的文字實體。

#### 外部實體模式
1.  **度數來源實體**：已有一個 `input_text` 或 `sensor` 實體可提供瓦斯度數。
2.  **input_text 實體**：用於存放度數的文字實體。

### 水錶配置

#### 基本要求
1.  **水錶帳號**：台灣自來水公司的水號 (格式：`XXX-XXX`)
2.  **聯繫資訊**：申請人名稱、電話、電郵
3.  **Google AI 整合**：同上（用於拍照識別）
4.  **攝影機**：對準水錶的攝影機

> **提示**：水錶配置與瓦斯類似，支援同樣的 Google AI OCR 和外部實體兩種模式。

---

## 安裝指南 (Installation)

### 方法一：使用 HACS 安裝 (推薦)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=maxrd&repository=slgas&category=integration)

1.  打開 **HACS** -> **Integrations**。
2.  點擊右上角三個點，選擇 **Custom repositories**。
3.  輸入儲存庫網址 `https://github.com/maxrd/slgas` 並選擇類別為 **Integration**。
4.  點擊 **Install**。
5.  重啟 Home Assistant。

### 方法二：手動安裝

1.  下載本儲存庫的原始碼。
2.  將 `custom_components/slgas/` 目錄複製到您 HA 設定目錄下的 `custom_components/` 資料夾中。
3.  重啟 Home Assistant。

---

## 配置與使用 (Usage)

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=slgas)

設定流程為 **6 個步驟**，支援動態欄位選擇：

### 📋 配置流程

#### 步驟 1️⃣：選擇類型
選擇要配置的類型：
*   **⛽ 瓦斯** - 瓦斯表度數申報
*   **💧 水錶** - 自來水度數申報
*   **⚡ 電力** - 電力度數申報（台電，上報功能開發中）

#### 步驟 2️⃣：選擇公司
根據類型自動過濾可用公司：
*   瓦斯類型：欣隆天然瓦斯
*   水錶類型：台灣自來水
*   電力類型：台灣電力公司

#### 步驟 3️⃣：基本資訊
根據所選公司動態顯示欄位：

**瓦斯（欣隆）**
| 欄位 | 格式 | 說明 |
|---|---|---|
| 客戶號 | `012345` | 欣隆瓦斯的客戶編號 |
| 客戶名稱 | 自由文字 | 開單姓名 |
| 聯繫電話 | `0912345678` | 聯繫電話 |

**水錶（台灣自來水）**
| 欄位 | 格式 | 說明 |
|---|---|---|
| 申請人名稱 | 自由文字 | 申請人姓名 |
| 水號 | `123-456` | 水號（必須為 XXX-XXX 格式） |
| 聯繫電話 | `0912345678` | 聯繫電話 |
| 電子郵件 | `user@example.com` | 電郵地址 |

**電力（台灣電力公司）**
| 欄位 | 格式 | 說明 |
|---|---|---|
| 用戶編號 | `12345678` | 台電用戶編號 |

> **注意**：台電上報功能目前尚在開發中，按下「確認並立即上報」按鈕不會實際送出資料。

#### 步驟 4️⃣：OCR 設定
選擇度數辨識方式，根據選擇動態顯示欄位：

**Google AI 模式（推薦）**
| 欄位 | 必填 | 說明 |
|---|---|---|
| 攝影機 | ✅ | 選擇對準表盤的攝像頭 |
| AI 辨識提示詞 | ✅ | 系統已預設適當提示詞，可自訂 |

**外部實體模式**
| 欄位 | 必填 | 說明 |
|---|---|---|
| 度數實體 | ✅ | 提供度數的 input_text 或 sensor |

#### 步驟 5️⃣：進階選項
| 欄位 | 必填 | 說明 |
|---|---|---|
| 度數存放實體 | ✅ | 辨識結果寫入此 input_text，供確認與上報 |
| 排程時間 | ✅ | 每天自動執行時間（例如 `08:00`） |
| 通知腳本 | 選填 | 回報完成後執行此腳本（推播、Telegram 等） |
| 通知標題 | 選填 | 通知推送的標題，預設瓦斯為 `🔥 瓦斯度數回報`，水表為 `💧 水錶度數回報` |
| 歷史天數 | 選填 | 預設 `90` 天，範圍 1～365 天 |

### 📸 範例：瓦斯配置流程

```
1️⃣ 選擇類型 → ⛽ 瓦斯
2️⃣ 選擇公司 → 欣隆天然瓦斯
3️⃣ 基本資訊 → 輸入 CusNo / 名稱 / 電話
4️⃣ OCR設定 → Google AI + 攝影機
5️⃣ 進階選項 → input_text + 08:00 + 通知腳本
✅ 完成配置
```

### 💧 範例：水錶配置流程

```
1️⃣ 選擇類型 → 💧 水錶
2️⃣ 選擇公司 → 台灣自來水
3️⃣ 基本資訊 → 輸入名稱 / 水號 (123-456) / 電話 / 郵箱
4️⃣ OCR設定 → Google AI + 攝影機
5️⃣ 進階選項 → input_text + 20:00 + 通知腳本
✅ 完成配置
```

---

## 自動建立的實體 (Entities)

本插件會根據配置自動建立以下實體：

### 感測器 (Sensors)

#### 瓦斯表
| 實體 | 說明 |
|---|---|
| `sensor.gas_meter_[CusNo]` | 🔢 **瓦斯度數**：數值型感測器 |
| | `device_class: gas` - 瓦斯類別 |
| | `state_class: total_increasing` - 單調遞增 |
| | 單位：`m³` |
| | ✅ 支援能源面板 |
| `sensor.gas_report_status_[CusNo]` | 📋 **回報狀態**：最後一次回報成敗狀態 |
| | 屬性中包含最近 90 天的歷史紀錄 |

#### 水錶
| 實體 | 說明 |
|---|---|
| `sensor.water_meter_[WaterNo]` | 💧 **水錶度數**：數值型感測器 |
| | `device_class: water` - 水錶類別 |
| | `state_class: total_increasing` - 單調遞增 |
| | 單位：`m³` |
| | ✅ 支援能源面板 |
| `sensor.water_report_status_[WaterNo]` | 📋 **回報狀態**：最後一次回報成敗狀態 |
| | 屬性中包含最近 90 天的歷史紀錄 |

#### 電力
| 實體 | 說明 |
|---|---|
| `sensor.electricity_meter_[TaipowerId]` | ⚡ **電力度數**：數值型感測器 |
| | `device_class: energy` - 電力類別 |
| | `state_class: total_increasing` - 單調遞增 |
| | 單位：`kWh` |
| | ✅ 支援能源面板 |
| `sensor.electricity_report_status_[TaipowerId]` | 📋 **回報狀態**：最後一次回報成敗狀態 |
| | 屬性中包含最近 90 天的歷史紀錄 |

### 按鈕 (Buttons)

| 實體 | 說明 |
|---|---|
| **確認並立即上報瓦斯度數** | ⛽ 執行「拍照 → AI 辨識 → 上報網站 → 通知」完整流程 |
| **手動分析度數 (不提交)** | 📸 執行「拍照 → AI 辨識 → 更新感測器」（不上報網站） |
| **確認並立即上報水錶度數** | 💧 執行「拍照 → AI 辨識 → 上報網站 → 通知」完整流程 |
| **手動分析水錶度數 (不提交)** | 📸 執行「拍照 → AI 辨識 → 更新感測器」（不上報網站） |
| **確認並立即上報電力度數** | ⚡ 執行流程（上報功能開發中，按鈕不會實際送出） |
| **手動分析電力度數 (不提交)** | 📸 執行「拍照 → AI 辨識 → 更新感測器」（不上報網站） |

---

## ⚡ 能源面板整合 (Energy Dashboard)

本插件建立的度數感測器可直接用於 Home Assistant 能源面板進行長期統計。

### 瓦斯消耗追蹤

1.  前往 **設定** -> **儀表板** -> **能源**。
2.  在「**瓦斯消耗**」區塊點擊 **新增瓦斯來源**。
3.  選擇對應的感測器（例如 `sensor.gas_meter_12345`）。
4.  設定瓦斯單價（可選，用於計算金額）。

> **提示**：設定後 HA 會自動計算兩次讀數間的消耗差值，並以日/週/月圖表呈現。

### 水消耗追蹤

1.  前往 **設定** -> **儀表板** -> **能源**。
2.  在「**水消耗**」區塊點擊 **新增水來源**。
3.  選擇對應的感測器（例如 `sensor.water_meter_123-456`）。
4.  設定水價（可選）。

> **提示**：台灣自來水單位為 1 立方公尺 (`m³`) = 1000 公升。

---

### 📊 能源面板顯示

配置後，能源面板會自動顯示：
*   **今日消耗**：今天相比昨天的增量
*   **周期統計**：日、週、月的用量圖表
*   **成本估算**：根據費率計算的金額（若有設定）

---

### 📊 Lovelace 歷史紀錄卡片範例

在儀表板新增一個 `markdown` 卡片：

```yaml
type: markdown
title: 瓦斯回報歷史紀錄
content: |
  | 日期 | 度數 | 狀態 |
  |------|------|------|
  {% for r in state_attr('sensor.wa_si_hui_bao_zhuang_tai_你的用戶編號', 'history') %}
  | {{ r.date }} | {{ r.degree }} | {{ r.status }} |
  {% endfor %}
```

---

### 📢 通知腳本說明

若選擇了通知腳本，系統會傳入 `variables`：

| 變數 | 說明 |
|------|------|
| `title` | 通知標題（可在配置中自訂，或使用預設值） |
| `message` | 包含時間戳與度數的文字 |
| `data.file` | 截圖路徑（例如 `/media/slgas_gas_slgas_012345.png`） |

#### 腳本範例 - 瓦斯回報 (手機推播)

```yaml
script:
  slgas_notify_gas:
    alias: 瓦斯度數回報通知
    sequence:
      - service: notify.mobile_app_your_phone
        data:
          title: "{{ title }}"
          message: "{{ message }}"
          data:
            image: "{{ data.file }}"
```

#### 腳本範例 - 水錶回報 (手機推播)

```yaml
script:
  slgas_notify_water:
    alias: 水錶度數回報通知
    sequence:
      - service: notify.mobile_app_your_phone
        data:
          title: "{{ title }}"
          message: "{{ message }}"
          data:
            image: "{{ data.file }}"
```

> **提示**：兩個腳本結構相同，只是 alias 和通知內容不同。通知標題會從配置中自動傳入，無需硬編碼。

---

## 常見問題 (FAQ)

<details>
  <summary>🔍 為什麼我的 OCR 辨識結果不準確？</summary>

  OCR 的準確度取決於攝影機的清晰度、光線以及 Google AI 的模型判斷。建議：
  - 調整攝影機焦距，確保表盤清晰
  - 確保有足夠照明（日光或補光燈）
  - 調整提示詞（Prompt），針對特定表盤類型優化
  - 測試「手動分析度數」按鈕先確認辨識結果，再確認上報
</details>

<details>
  <summary>🌐 台灣自來水上報失敗怎麼辦？</summary>

  台灣自來水網站有額外的安全機制（如驗證碼）。若上報失敗：
  - 確認水號格式正確（`XXX-XXX`）
  - 確認申請人名稱與自來水公司紀錄一致
  - 檢查聯繫電話和電郵是否正確
  - 嘗試手動前往 [台灣自來水網站](https://www.water.gov.tw) 確認是否可正常申報
</details>

<details>
  <summary>⛽ 欣隆瓦斯上報失敗？</summary>

  - 確認客戶號、名稱與欣隆瓦斯紀錄一致
  - 檢查聯繫電話是否正確
  - 網站可能在維護，稍後再試
  - 查看回報狀態感測器的「歷史」屬性了解詳細錯誤訊息
</details>

<details>
  <summary>📋 歷史紀錄會消失嗎？</summary>

  - **回報狀態歷史**：存放在感測器屬性中，HA 重啟可能消失（未持久化）
  - **度數感測器**：使用 `RestoreEntity`，重啟後自動恢復上次數值
  - **建議**：如需永久保存，可在 HA 中設定「歷史統計」或連接外部資料庫
</details>

<details>
  <summary>♻️ 從舊版升級需要重新設定？</summary>

  是的。若您是從 v1.0 升級到 v1.2（新增水表支援）：
  - **建議做法**：刪除舊整合，重新新增整合
  - 原因：新版使用 6 步驟流程，欄位結構已變更
  - 不用擔心：新增時會創建新的唯一 ID，舊資料不會丟失
</details>

<details>
  <summary>🔄 Google AI 與外部實體模式有何差異？</summary>

  | 項目 | Google AI 模式 | 外部實體模式 |
  |------|---|---|
  | 流程 | 攝影機 → AI 辨識 | 直接讀取實體 |
  | 適用 | 有對準表盤的攝影機 | 已有其他 OCR 或手動輸入 |
  | 優點 | 全自動，無需人工 | 依賴其他可靠來源 |
  | 缺點 | 需要好攝影機和光線 | 需先有度數來源 |
</details>

<details>
  <summary>🔌 可以在一個整合下管理多個帳戶嗎？</summary>

  **是的！** 這是本整合的核心特色。您可以：
  - 在「設定」中重複新增整合
  - 每次新增時選擇不同的公司/帳號
  - 每個帳號都有獨立的配置、感測器和按鈕
  - 例如：同時管理「家裡瓦斯」、「租屋處瓦斯」、「家裡水錶」
</details>

---

## 聲明與支援 (Disclaimer & Support)

### ⚖️ 法律聲明

*   本插件為**非官方開發**，與以下機構無任何關聯：
    - 欣隆天然瓦斯股份有限公司
    - 台灣自來水公司
*   作者不保證回報流程的永久可用性
    - 網站可能隨時改版或改變 API
    - 請定期檢查回報狀態感測器
*   使用本插件自動申報服務須自行承擔風險

### 📢 支援與回饋

*   **問題回報**：[GitHub Issues](https://github.com/maxrd/slgas/issues)
*   **功能建議**：[GitHub Discussions](https://github.com/maxrd/slgas/discussions)
*   **技術文檔**：見本倉庫 `/docs` 資料夾
    - `IMPLEMENTATION.md` - 實裝詳解
    - `USER_GUIDE.md` - 完整使用指南
    - `CHANGELOG.md` - 版本變更記錄

### 🤝 貢獻與開發

本項目歡迎以下貢獻：
*   🐛 報告 Bug
*   ✨ 建議新功能
*   🏭 新增公司支援（大台北瓦斯、台中水務等）
*   📝 改進文檔
*   🌍 翻譯

---

**如果您覺得這個專案有幫助，請給它一個 ⭐ Star！**

**版本**: v1.3.0 (2026-05-20)
**狀態**: 主動維護中 🚀