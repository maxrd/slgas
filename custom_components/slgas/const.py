"""Constants for the slgas integration."""

DOMAIN = "slgas"

# Configuration keys
CONF_CUS_NO = "cus_no"
CONF_CUS_NAME = "cus_name"
CONF_CUS_PHONE = "cus_phone"
CONF_CAMERA_ENTITY = "camera_entity"
CONF_TEXT_ENTITY = "text_entity"
CONF_SCHEDULE_TIME = "schedule_time"
CONF_NOTIFY_SCRIPT = "notify_script"
CONF_HISTORY_DAYS = "history_days"
CONF_PROMPT = "prompt"
CONF_OCR_SOURCE = "ocr_source"
CONF_DEGREE_ENTITY = "degree_entity"

# OCR source options
OCR_SOURCE_GOOGLE_AI = "google_ai"
OCR_SOURCE_EXTERNAL = "external"

# Defaults
DEFAULT_HISTORY_DAYS = 90
DEFAULT_PROMPT = "這是一張瓦斯表的照片,左邊為4個黑底白色數字整數度數字框,只回傳這4位 ,有一個m2這個忽略,右邊為3個黑底紅色數字框忽略，不要有其他文字。"

# Services
SERVICE_EXECUTE_REPORT = "execute_report"

# File paths
DEFAULT_IMAGE_PATH = "/config/www/slgas.jpg"
