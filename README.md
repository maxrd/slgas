[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![GitHub release](https://img.shields.io/github/release/maxrd/slgas.svg)](https://github.com/maxrd/slgas/releases/)
[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://github.com/maxrd/slgas/graphs/commit-activity)

# 基隆欣隆瓦斯自動回報 (SLGAS Auto Report)
### Home Assistant 自定義組件 - 用於自動回報欣林天然瓦斯度數

本插件專為欣林天然瓦斯用戶設計，能夠自動化每日的瓦斯度數申報流程。透過整合攝影機拍照與 Google AI OCR 技術，實現「免人工、自動報表」的智能體驗。

⭐ **主要功能：**
*   **自動排程辨識**：每日定時執行拍照與辨識，更新度數但不自動上報。
*   **兩段階段上報**：精準模擬網站的驗證 (`Check`) 與寫入 (`Append`) 流程。
*   **AI OCR 辨識**：結合 Google AI 自動讀取瓦斯表數字。
*   **歷史紀錄**：預設保留 90 天回報歷史，可自訂天數（1～365 天）。
*   **手動確認上報**：點擊按鈕執行完整流程（含自動辨識與正式上報）。

---

## 預先準備 (Pre-requisites)
在使用本插件前，請確保您的 Home Assistant 已具備以下條件：
1.  **Google Generative AI 整合**：插件依賴 Google AI 進行 OCR 辨識，請先在 HA 中設定好官方的 Google Generative AI 整合。
2.  **瓦斯表攝影機**：已接入 Home Assistant 並可正常拍照。
3.  **度數存放實體**：請預先建立一個 `input_text` (輔助元件)，用來存放辨識後的度數。

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

1.  前往 **設定** -> **裝置與服務** -> **新增整合**。
2.  搜尋 `欣林瓦斯自動回報` (或 `slgas`)。
3.  在設定頁面填入以下資訊：
    *   **用戶編號 (CusNo)**：例如 `012345`。
    *   **用戶名稱 (CusName)**：您的開單姓名。
    *   **用戶手機 (Cuscallno)**：預留的聯絡電話。
    *   **瓦斯表攝影機**：選擇對準瓦斯表的攝像頭。
    *   **度數存放實體**：選擇預先建立的 `input_text`。
    *   **排程時間**：設定每天自動執行的時間（例如 `08:00`）。
    *   **通知腳本 (選填)**：選擇一個 HA 腳本，在每次回報完成後自動呼叫，用於傳送推播通知。留空則不通知。
    *   **歷史紀錄保留天數**：預設 `90` 天，可自訂 1～365 天。

---

## 自動化流程說明 (Quick Start)
本插件會自動建立以下實體：

*   **感測器 (Sensor)**：`sensor.slgas_last_report`
    *   顯示最後一次回報的成敗狀態。
    *   在屬性 (Attributes) 中紀錄歷史數據（日期、辨識度數、狀態），保留天數依設定而定。
    *   💡 可透過 Lovelace `markdown` 卡片呈現歷史表格（見下方範例）。
*   **按鈕 (Button)**：`button.slgas_manual_report`
    *   **立即確認並上報**：點擊此按鈕會執行「拍照 -> OCR -> 寫入實體 -> **正式上報網站** -> 通知」的完整動作。建議在排程辨識後，人工確認 `input_text` 數值正確再按下此按鈕。

### 📊 Lovelace 歷史紀錄卡片範例
在儀表板新增一個 `markdown` 卡片，填入以下內容即可顯示表格：
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
> ⚠️ 請將 `sensor.wa_si_hui_bao_zhuang_tai_你的用戶編號` 替換為您實際的感測器 entity_id。

### 📢 通知腳本說明

若在設定中選擇了通知腳本，系統會在每次回報流程完成後，透過 `script.turn_on` 呼叫該腳本，並傳入 `variables` 變數。

#### 傳入參數格式

| 變數 | 型別 | 說明 | 範例值 |
|------|------|------|--------|
| `message` | `string` | 換行 + 時間戳 + 目前度數 | `\n2026-05-03 08:00:01  目前瓦期使用度數為:1234` |
| `data.file` | `string` | 攝影機截圖的本機檔案路徑 | `/config/www/slgas.jpg` |

#### 實際呼叫格式（內部邏輯）
```python
await hass.services.async_call(
    "script",
    "turn_on",
    {
        "entity_id": "script.slgas_notify",   # 您選擇的腳本
        "variables": {
            "message": "\n2026-05-03 08:00:01  目前瓦期使用度數為:1234",
            "data": {
                "file": "/config/www/slgas.jpg"
            }
        }
    }
)
```

#### `message` 格式詳解
```
\n{YYYY-MM-DD HH:MM:SS}  目前瓦期使用度數為:{input_text 的值}
```
*   開頭有一個換行符 `\n`
*   時間為回報完成當下的本機時間
*   度數讀取自您設定的 `input_text` 實體的當前狀態值

#### 腳本範例

**範例一：手機 APP 推播通知（含圖片）**
```yaml
script:
  slgas_notify:
    alias: 瓦斯回報通知
    sequence:
      - service: notify.mobile_app_your_phone
        data:
          title: "🔥 瓦斯度數回報"
          message: "{{ message }}"
          data:
            image: "{{ data.file }}"
```

**範例二：LINE Notify**
```yaml
script:
  slgas_notify:
    alias: 瓦斯回報 LINE 通知
    sequence:
      - service: notify.line_notify
        data:
          message: "{{ message }}"
          data:
            file: "{{ data.file }}"
```

**範例三：Telegram（含照片）**
```yaml
script:
  slgas_notify:
    alias: 瓦斯回報 Telegram 通知
    sequence:
      - service: telegram_bot.send_photo
        data:
          file: "{{ data.file }}"
          caption: "{{ message }}"
```

**範例四：純文字通知（不傳圖片）**
```yaml
script:
  slgas_notify:
    alias: 瓦斯回報純文字通知
    sequence:
      - service: notify.mobile_app_your_phone
        data:
          message: "{{ message }}"
```

> 💡 **提示**：若不需要通知功能，設定時將「通知腳本」欄位留空即可。

---

## 常見問題 (FAQ)

<details>
  <summary>為什麼我的 OCR 辨識結果不準確？</summary>
  OCR 的準確度取決於攝影機的清晰度、光線以及 Google AI 的模型判斷。建議調整攝影機焦距，並確保夜間有足夠的紅外補光或照明。
</details>

<details>
  <summary>網站上報失敗，錯誤訊息顯示「回報失敗」？</summary>
  這通常是因為用戶資料 (CusNo/CusName) 與瓦斯公司紀錄不符，或是網站在維護中。請確認手動前往網站填寫是否正常。
</details>

<details>
  <summary>歷史紀錄會消失嗎？</summary>
  歷史紀錄存放在感測器的狀態屬性中，若 Home Assistant 資料庫重置或插件被刪除重新安裝，舊紀錄將會消失。保留天數可在設定中自訂（預設 90 天，最大 365 天）。
</details>

---

## 聲明與支援 (Disclaimer)
*   本插件為非官方開發，與「欣林天然瓦斯股份有限公司」無任何關聯。
*   作者不保證回報流程的永久可用性，請用戶定期檢查回報狀態。
*   如有任何問題或建議，請至 [GitHub Issues](https://github.com/maxrd/slgas/issues) 提交。

---
**如果您覺得這個專案有幫助，請給它一個 ⭐ Star！**
#   s l g a s 
 
 