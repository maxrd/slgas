"""Constants for the slgas integration."""

DOMAIN = "slgas"

# Meter types
METER_TYPE_GAS = "gas"
METER_TYPE_WATER = "water"
METER_TYPE_ELECTRICITY = "electricity"

# Companies
COMPANY_SLGAS = "slgas"
COMPANY_SHINHAI = "shinhai"
COMPANY_WATER_TAIPEI = "water_taipei"
COMPANY_TAIPOWER = "taipower"

# Configuration keys - Common
CONF_METER_TYPE = "meter_type"
CONF_COMPANY = "company"
CONF_CAMERA_ENTITY = "camera_entity"
CONF_TEXT_ENTITY = "text_entity"
CONF_SCHEDULE_TIME = "schedule_time"
CONF_NOTIFY_SCRIPT = "notify_script"
CONF_NOTIFY_TITLE = "notify_title"
CONF_HISTORY_DAYS = "history_days"
CONF_PROMPT = "prompt"
CONF_OCR_SOURCE = "ocr_source"
CONF_DEGREE_ENTITY = "degree_entity"

# Configuration keys - Gas (SLGAS 欣隆)
CONF_CUS_NO = "cus_no"
CONF_CUS_NAME = "cus_name"
CONF_CUS_PHONE = "cus_phone"

# Configuration keys - Gas (新海瓦斯)
CONF_SHINHAI_NO1      = "shinhai_no1"       # 用戶號碼第1段 (3碼)
CONF_SHINHAI_NO2      = "shinhai_no2"       # 用戶號碼第2段 (5碼)
CONF_SHINHAI_NO3      = "shinhai_no3"       # 用戶號碼第3段 (1碼)
CONF_SHINHAI_TEL_AREA = "shinhai_tel_area"  # 市話區碼 (最多4碼，與 shinhai_tel 配對)
CONF_SHINHAI_TEL      = "shinhai_tel"       # 市話號碼 (最多8碼)
CONF_SHINHAI_MOBILE   = "shinhai_mobile"    # 手機 (10碼，與市話擇一)

# Configuration keys - Water (Taiwan Water)
CONF_WATER_NO = "water_no"          # legacy, kept for backward compat
CONF_WATER_NUM1 = "water_num1"      # 大區 2碼, e.g. "1B"
CONF_WATER_NUM2 = "water_num2"      # 用戶編號 8碼, e.g. "12345678"
CONF_WATER_NUM3 = "water_num3"      # 檢查號 1碼, e.g. "9"
CONF_WATER_ADDR_CITY = "water_addr_city"   # 縣市代碼, e.g. "C"
CONF_WATER_ADDR_DIST = "water_addr_dist"   # 鄉鎮區代碼, e.g. "207"
CONF_WATER_ADDR = "water_addr"      # 詳細地址
CONF_APPLICANT_NAME = "applicant_name"
CONF_EMAIL = "email"
CONF_PHONE = "phone"
CONF_CAPTCHA_CODE = "captcha_code"

# Configuration keys - Electricity (Taipower)
CONF_TAIPOWER_ID = "taipower_id"

# OCR source options
OCR_SOURCE_GOOGLE_AI = "google_ai"
OCR_SOURCE_EXTERNAL = "external"

# Configuration keys - Anomaly detection
CONF_DEGREE_DIFF_THRESHOLD = "degree_diff_threshold"

# Defaults
DEFAULT_HISTORY_DAYS = 90
DEFAULT_DEGREE_DIFF_THRESHOLD = 10
DEFAULT_NOTIFY_TITLE_GAS = "🔥 瓦斯度數回報"
DEFAULT_NOTIFY_TITLE_WATER = "💧 水錶度數回報"
DEFAULT_NOTIFY_TITLE_ELECTRICITY = "⚡ 電力度數回報"
DEFAULT_PROMPT_GAS = "這是一張瓦斯表的照片,請提取左邊黑底白色數字框中的整數度數,忽略右邊紅色數字框(通常為3位),只回傳數字本身,不要有其他文字。"
DEFAULT_PROMPT_WATER = "這是一張水錶的照片,請提取黑色數字部分的整數度數,忽略紅色小數部分。只回傳數字本身,不要有其他文字。"
DEFAULT_PROMPT_ELECTRICITY = "這是一張電錶的照片,請提取黑色數字部分的整數度數,忽略小數部分。只回傳數字本身,不要有其他文字。"
DEFAULT_PROMPT = DEFAULT_PROMPT_GAS  # backward compatibility

# Services
SERVICE_EXECUTE_REPORT = "execute_report"

# File paths
DEFAULT_IMAGE_DIR = "/media"
DEFAULT_IMAGE_PATH = "/media/slgas.png"  # fallback for single-entry compatibility
DEFAULT_CAPTCHA_IMAGE_PATH = "/media/water_captcha.gif"

# Taiwan Water city codes (value, label)
WATER_TAIPEI_CITIES = [
    ("B", "基隆市"), ("C", "新北市"), ("D", "宜蘭縣"), ("E", "桃園市"),
    ("F", "新竹市"), ("G", "新竹縣"), ("H", "苗栗縣"), ("I", "台中市"),
    ("J", "彰化縣"), ("K", "南投縣"), ("L", "雲林縣"), ("M", "嘉義市"),
    ("N", "嘉義縣"), ("O", "台南市"), ("P", "高雄市"), ("Q", "屏東縣"),
    ("R", "台東縣"), ("S", "花蓮縣"), ("T", "澎湖縣"), ("U", "金門縣"),
]
