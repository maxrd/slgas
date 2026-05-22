[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub release](https://img.shields.io/github/release/maxrd/slgas.svg)](https://github.com/maxrd/slgas/releases/)
[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://github.com/maxrd/slgas/graphs/commit-activity)

# 通用能源自動回報整合 (Universal Utility Reporter)

### Home Assistant 自定義組件 — 支援瓦斯、水錶、電力自動申報

本插件提供**模組化架構**，可自動完成度數辨識與網站申報，目前已支援：

| 類型 | 公司 | OCR | 自動上報 | 狀態 |
|------|------|-----|---------|------|
| ⛽ 瓦斯 | 欣隆天然瓦斯 (SLGAS) | ✅ | ✅ | 穩定 |
| 💧 水錶 | 臺灣自來水公司 | ✅ | ✅ | 穩定 |
| ⚡ 電力 | 台灣電力公司 (Taipower) | ✅ | 開發中 | 預覽 |

---

## ✨ 主要功能

### 🤖 全自動申報（含圖形驗證碼）

台灣自來水申報流程完全自動化，無需人工介入：

1. 自動取得網站 Session 與 CSRF Token
2. 自動上傳水錶照片至台水伺服器
3. **自動用 Google AI 辨識圖形驗證碼**（存為 `/media/water_captcha.gif`）
4. 自動填寫所有欄位並送出申報

### 🎯 雙模式度數來源

- **Google AI OCR 模式**：攝影機拍照 → AI 自動辨識度數
- **外部實體模式**：直接讀取現有 `sensor` / `input_text` 實體

### 📊 能源面板原生整合

- 瓦斯：`device_class: gas`，單位 `m³`
- 水：`device_class: water`，單位 `m³`
- 電：`device_class: energy`，單位 `kWh`
- 三者均支援 HA 能源面板長期統計與圖表

### ⏰ 排程與手動控制

- 每日定時自動執行（僅辨識，不自動上報）
- 手動按鈕一鍵「拍照 → 辨識 → 上報 → 通知」完整流程
- 可分段執行「僅辨識」或「完整上報」

### 🔧 其他

- 同一整合支援多帳戶（瓦斯、水、電混搭）
- HA 重啟後自動恢復上次度數
- 最多保留 365 天歷史紀錄

---

## 預先準備 (Pre-requisites)

### 共用需求（所有類型）

- **Google Generative AI 整合**：HA 設定中已安裝並設定 `ai_task.google_ai_task`
- **input_text 實體**：用於存放辨識結果（手動確認用）

### 瓦斯（欣隆）額外需求

- 欣隆瓦斯客戶號、姓名、電話
- 對準表盤的攝影機（Google AI 模式）

### 水錶（台灣自來水）額外需求

- **水號（三段格式）**：`大區(2碼) - 用戶編號(8碼) - 檢查號(1碼)`，例如 `1B-12345678-9`
  > 可在水費通知單或台水官網帳號查詢
- 申請人姓名、電話、電郵
- 用水縣市、鄉鎮區、詳細地址
- 對準水錶的攝影機

---

## 安裝指南 (Installation)

### 方法一：HACS（推薦）

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=maxrd&repository=slgas&category=integration)

1. 開啟 **HACS → Integrations**
2. 右上角三點 → **Custom repositories**
3. 輸入 `https://github.com/maxrd/slgas`，類別選 **Integration**
4. 點擊 **Install**，重啟 Home Assistant

### 方法二：手動安裝

1. 下載本儲存庫原始碼
2. 將 `custom_components/slgas/` 複製到 HA 設定目錄的 `custom_components/` 中
3. 重啟 Home Assistant

---

## 配置流程 (Setup)

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=slgas)

### ⛽ 瓦斯配置（5 步驟）

```
步驟 1 → 選擇類型：⛽ 瓦斯
步驟 2 → 選擇公司：欣隆天然瓦斯
步驟 3 → 基本資訊：客戶號 / 姓名 / 電話
步驟 4 → OCR 設定：Google AI + 攝影機 + 提示詞
步驟 5 → 進階選項：input_text / 排程時間 / 通知腳本
```

**步驟 3 欄位說明（瓦斯）**

| 欄位 | 格式範例 | 說明 |
|------|----------|------|
| 客戶號 | `012345` | 欣隆瓦斯帳單上的客戶編號 |
| 客戶名稱 | `王小明` | 開單姓名 |
| 聯繫電話 | `0912345678` | 聯繫電話 |

---

### 💧 水錶配置（6 步驟）

```
步驟 1 → 選擇類型：💧 水錶
步驟 2 → 選擇公司：臺灣自來水
步驟 3 → 基本資訊：姓名 / 水號三段 / 電話 / 電郵 / 縣市
步驟 3b → 用水地址：鄉鎮區（動態下拉）/ 詳細地址
步驟 4 → OCR 設定：Google AI + 攝影機 + 提示詞
步驟 5 → 進階選項：input_text / 排程時間 / 通知腳本
```

**步驟 3 欄位說明（台水）**

| 欄位 | 格式範例 | 說明 |
|------|----------|------|
| 申請人姓名 | `王小明` | 台水帳戶登記姓名 |
| 水號大區 | `1B` | 2 碼英數字（水費通知單右上角） |
| 水號用戶編號 | `12345678` | 8 碼數字 |
| 水號檢查號 | `9` | 1 碼 |
| 聯繫電話 | `02-1234-5678` 或 `0912-345678` | 市話或手機均可 |
| 電子郵件 | `user@gmail.com` | 接收申報通知的信箱 |
| 縣(市) | 下拉選單 | 選擇用水地點縣市 |

**步驟 3b 欄位說明（用水地址）**

| 欄位 | 說明 |
|------|------|
| 鄉鎮(區) | 依縣市自動從台水 API 載入，下拉選擇 |
| 詳細地址 | 街道門號（例：中正路 100 號） |

> **水號格式說明**：台水水號分三段，以 `-` 分隔。水費通知單範例：`1B-12345678-9`

---

### ⚡ 電力配置（5 步驟）

```
步驟 1 → 選擇類型：⚡ 電力
步驟 2 → 選擇公司：台灣電力公司
步驟 3 → 基本資訊：台電用戶編號
步驟 4 → OCR 設定：Google AI + 攝影機
步驟 5 → 進階選項：input_text / 排程時間
```

> **注意**：台電自動上報功能目前尚在開發中，OCR 辨識度數正常運作，但上報網站功能尚未完成。

---

## 自動建立的實體 (Entities)

### 感測器 (Sensors)

| 實體 ID | 說明 | 能源面板 |
|---------|------|---------|
| `sensor.gas_meter_[CusNo]` | 瓦斯度數，`m³`，`device_class: gas` | ✅ 瓦斯消耗 |
| `sensor.gas_report_status_[CusNo]` | 瓦斯回報狀態與歷史 | — |
| `sensor.water_meter_[WaterNum]` | 水錶度數，`L`（公升），`device_class: water` | ✅ 水消耗 |
| `sensor.water_report_status_[WaterNum]` | 水錶回報狀態與歷史 | — |
| `sensor.electricity_meter_[TaipowerId]` | 電力度數，`kWh`，`device_class: energy` | ✅ 電力消耗 |
| `sensor.electricity_report_status_[TaipowerId]` | 電力回報狀態與歷史 | — |

### 按鈕 (Buttons)

| 按鈕 | 動作 |
|------|------|
| 確認並立即上報（瓦斯/水/電） | 拍照 → AI 辨識 → 上報網站 → 通知 |
| 手動分析度數（不提交） | 拍照 → AI 辨識 → 更新感測器（不上報） |

---

## 能源面板整合

1. 前往 **設定 → 儀表板 → 能源**
2. 新增對應感測器：
   - 瓦斯消耗 → `sensor.gas_meter_...`
   - 水消耗 → `sensor.water_meter_...`（單位：公升 L）
   - 電力消耗 → `sensor.electricity_meter_...`
3. 可設定費率，HA 自動計算兩次讀數間的差值與費用

---

## 通知腳本

回報完成後，系統會呼叫您設定的腳本，並傳入以下變數：

| 變數 | 說明 |
|------|------|
| `title` | 通知標題（可在進階設定中自訂） |
| `message` | 含時間戳與度數的文字 |
| `data.file` | 截圖路徑（例：`/media/slgas_water_1B123456789.png`） |

**範例腳本**（適用瓦斯、水錶、電力）：

```yaml
script:
  slgas_notify:
    alias: 能源度數回報通知
    sequence:
      - service: notify.mobile_app_your_phone
        data:
          title: "{{ title }}"
          message: "{{ message }}"
          data:
            image: "{{ data.file }}"
```

---

## 歷史紀錄卡片

在 Lovelace 新增 `markdown` 卡片顯示回報歷史：

```yaml
type: markdown
title: 水錶回報歷史
content: |
  | 日期 | 度數 | 狀態 |
  |------|------|------|
  {% for r in state_attr('sensor.water_report_status_1B123456789', 'history') %}
  | {{ r.date }} | {{ r.degree }} | {{ r.status }} |
  {% endfor %}
```

---

## 常見問題 (FAQ)

<details>
<summary>💧 台灣自來水上報全自動流程如何運作？</summary>

上報流程完全在 HA 背景執行，無需任何人工介入：

1. **取得 Session**：自動訪問台水申辦頁面，取得 ASP.NET Session Cookie 與 CSRF Token
2. **上傳照片**：將水錶照片上傳至台水伺服器，取得檔案 ID
3. **解決驗證碼**：向台水取得圖形驗證碼（GIF），存至 `/media/water_captcha.gif`，再呼叫 `ai_task.google_ai_task` 辨識 5 位數字
4. **送出申報**：填寫所有正確欄位（姓名、三段水號、地址、度數、照片 ID、驗證碼）並 POST 送出

整個流程約 10–30 秒完成。
</details>

<details>
<summary>🔢 台水水號格式是什麼？</summary>

台水水號由三段組成，以 `-` 分隔，例如 `1B-12345678-9`：

| 段落 | 長度 | 說明 | 範例 |
|------|------|------|------|
| 大區 | 2 碼 | 英數字混合 | `1B`、`2C` |
| 用戶編號 | 8 碼 | 純數字 | `12345678` |
| 檢查號 | 1 碼 | 數字或字母 | `9` |

水號可在水費通知單右上角或台水官網「水費查詢」中查到。
</details>

<details>
<summary>🤖 AI 驗證碼辨識準確嗎？</summary>

台水驗證碼為純數字、無扭曲的簡單圖形，Google AI 辨識率相當高。若偶爾辨識失敗，重試即可（每次取得的驗證碼不同）。

驗證碼圖片會存至 `/media/water_captcha.gif`，可在 HA 媒體瀏覽器中查看最後一次的驗證碼。
</details>

<details>
<summary>🔍 OCR 度數辨識不準確怎麼辦？</summary>

- 調整攝影機焦距，確保表盤清晰
- 確保有足夠照明
- 修改「AI 提示詞」，針對特定表盤優化
- 先按「手動分析度數（不提交）」確認辨識結果後，再執行完整上報
</details>

<details>
<summary>⛽ 欣隆瓦斯上報失敗怎麼辦？</summary>

- 確認客戶號、名稱與欣隆瓦斯紀錄一致
- 確認聯繫電話格式正確
- 網站可能暫時維護，稍後再試
- 查看回報狀態感測器的「history」屬性了解詳細錯誤
</details>

<details>
<summary>🔄 Google AI 模式 vs 外部實體模式？</summary>

| 項目 | Google AI 模式 | 外部實體模式 |
|------|---------------|-------------|
| 流程 | 攝影機 → AI 辨識 | 直接讀取實體值 |
| 適用 | 有對準表盤的攝影機 | 已有其他 OCR 或手動輸入 |
| 優點 | 全自動，無需人工 | 不依賴攝影機 |
| 缺點 | 需要清晰影像和光線 | 需另有度數來源 |
</details>

<details>
<summary>🔌 可以同時管理多個帳戶嗎？</summary>

**可以。** 在「設定 → 整合」中重複新增本整合，每次選擇不同帳戶。例如：
- 家裡瓦斯（欣隆）
- 家裡水錶（台水）
- 租屋處水錶（台水）

每個帳戶有獨立的感測器、按鈕和配置。
</details>

<details>
<summary>♻️ 從舊版升級需要重新設定嗎？</summary>

若您是從 v1.x 升級，且原本的水錶水號使用舊格式（`XXX-XXX`），建議重新設定：
- 刪除舊的水錶整合條目
- 重新新增，填入新的三段水號格式

舊的瓦斯設定不受影響，無需重新設定。
</details>

---

## 聲明 (Disclaimer)

本插件為**非官方開發**，與欣隆天然瓦斯、台灣自來水公司、台灣電力公司無任何關聯。作者不保證申報流程的永久可用性，網站改版可能導致失效。使用本插件自動申報服務須自行承擔風險，請定期確認回報狀態感測器。

---

## 支援與回饋

- **問題回報**：[GitHub Issues](https://github.com/maxrd/slgas/issues)
- **功能建議**：[GitHub Discussions](https://github.com/maxrd/slgas/discussions)

如果這個專案對您有幫助，請給它一個 ⭐ Star！

---

**版本**：2026.5.27 | **狀態**：主動維護中 🚀
