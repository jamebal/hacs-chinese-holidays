"""Constants for the holiday_status integration."""
from datetime import timedelta

DOMAIN = "holiday_status"

# Sensor specific constants
SENSOR_NAME = "今日状态"
ICON = "mdi:calendar-today"

# API related constants
# New API URL format: d={YYYYMM}
# HOLIDAY_API_URL = "http://tool.bitefu.net/jiari/?d={}"
HOLIDAY_API_URL = "https://cloud.jmal.top/api/share-file/68479e80c523cbaa3ca93b66/holiday.json"
API_TIMEOUT = 10  # seconds

# Possible states for the sensor
STATE_WEEKDAY = "工作日"
STATE_WEEKEND = "休息日"
STATE_HOLIDAY = "节假日"

# How often to update the sensor (e.g., every 12 hours)
# Considering the API returns monthly data, this is still reasonable.
SCAN_INTERVAL = timedelta(hours=12)