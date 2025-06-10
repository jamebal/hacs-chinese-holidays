"""Platform for holiday_status sensor."""
from __future__ import annotations

from datetime import datetime, timedelta
import logging

import async_timeout

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)

# 定义传感器更新频率（例如，每1小时更新一次）
SCAN_INTERVAL = timedelta(hours=1)

# API 地址
API_BASE_URL = "http://tool.bitefu.net/jiari/?d={date}&info=1"

# 节假日类型映射
# type=0为工作日, type=1为休息日, type=2为节假日
STATUS_MAP = {
    0: "工作日",
    1: "休息日",
    2: "节假日",
}

async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the Holiday Status sensor platform."""
    _LOGGER.debug("Setting up HolidayStatusSensor")
    async_add_entities([HolidayStatusSensor(hass)], True)

class HolidayStatusSensor(SensorEntity):
    """Representation of a Holiday Status sensor."""

    _attr_name = "Holiday Status"
    _attr_unique_id = "holiday_today_status_sensor"
    _attr_icon = "mdi:calendar" # 为传感器设置一个日历图标

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the sensor."""
        self.hass = hass
        self._state = None
        self._attributes = {}
        _LOGGER.debug("HolidayStatusSensor initialized")

    @property
    def state(self) -> str | None:
        """Return the state of the sensor."""
        return self._state

    @property
    def extra_state_attributes(self) -> dict | None:
        """Return the state attributes."""
        return self._attributes

    async def async_update(self) -> None:
        """Fetch new state data for the sensor.
        This is the only method that should fetch new data for Home Assistant.
        """
        _LOGGER.debug("Starting HolidayStatusSensor update")
        session = async_get_clientsession(self.hass)
        today = datetime.now()

        # API需要YYYYMM格式的日期
        api_date_month = today.strftime("%Y%m")
        # API响应中的键是MMDD格式
        api_date_day = today.strftime("%m%d")

        url = API_BASE_URL.format(date=api_date_month)
        _LOGGER.debug(f"Fetching data from API: {url}")

        try:
            async with async_timeout.timeout(10): # 设置10秒超时
                response = await session.get(url)
                response.raise_for_status() # 如果请求失败，抛出异常
                data = await response.json()
                _LOGGER.debug(f"API response: {data}")

                # 检查响应数据结构
                if api_date_month in data and api_date_day in data[api_date_month]:
                    today_info = data[api_date_month][api_date_day]
                    holiday_type = today_info.get("type")
                    holiday_typename = today_info.get("typename")

                    if holiday_type is not None and holiday_type in STATUS_MAP:
                        self._state = STATUS_MAP[holiday_type]
                        self._attributes = {
                            "api_raw_type": holiday_type,
                            "api_typename": holiday_typename,
                            "date": today.strftime("%Y-%m-%d"),
                            "last_updated": datetime.now().isoformat()
                        }
                        _LOGGER.info(f"Holiday status updated to: {self._state} ({holiday_typename})")
                    else:
                        self._state = "未知"
                        self._attributes = {
                            "error": "API返回的类型值无效或缺失",
                            "api_raw_response_for_today": today_info
                        }
                        _LOGGER.warning(f"Invalid or missing type in API response for {today.strftime('%Y%m%d')}: {today_info}")
                else:
                    self._state = "未知"
                    self._attributes = {
                        "error": "API未返回今日数据",
                        "api_response_month_data": data.get(api_date_month)
                    }
                    _LOGGER.warning(f"No data for today ({api_date_day}) in API response for month {api_date_month}.")

        except async_timeout.TimeoutError:
            self._state = "错误"
            self._attributes = {"error": "API请求超时"}
            _LOGGER.error(f"Failed to fetch holiday status: API request timed out for {url}")
        except Exception as e:
            self._state = "错误"
            self._attributes = {"error": f"API请求失败: {e}"}
            _LOGGER.error(f"Failed to fetch holiday status: {e}", exc_info=True)