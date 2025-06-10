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
from homeassistant.helpers.event import async_track_time_change # 导入时间事件追踪器

_LOGGER = logging.getLogger(__name__)

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

    # 关键改变: 告诉 Home Assistant 这个实体不应该被定期轮询
    # 因为我们自己会管理更新时间
    _attr_should_poll = False

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the sensor."""
        self.hass = hass
        self._state = None
        self._attributes = {}
        self._unsub_listener = None # 用于存储取消定时任务的句柄
        _LOGGER.debug("HolidayStatusSensor initialized")

    @property
    def state(self) -> str | None:
        """Return the state of the sensor."""
        return self._state

    @property
    def extra_state_attributes(self) -> dict | None:
        """Return the state attributes."""
        return self._attributes

    async def async_added_to_hass(self) -> None:
        """Run when this entity has been added to Home Assistant."""
        _LOGGER.debug(f"HolidayStatusSensor {self.entity_id} added to Home Assistant.")
        # 首次加载时立即更新一次状态
        await self._async_update_data()

        # 注册一个每天凌晨 00:00:01 更新的回调
        # async_track_time_change 会返回一个取消函数，我们需要在实体移除时调用它
        self._unsub_listener = async_track_time_change(
            self.hass,
            self._schedule_update,
            hour=17,
            minute=20,
            second=1
        )
        _LOGGER.debug(f"Scheduled daily update for {self.entity_id} at 00:01:00.")

    async def async_will_remove_from_hass(self) -> None:
        """Run when this entity will be removed from Home Assistant."""
        _LOGGER.debug(f"HolidayStatusSensor {self.entity_id} will be removed from Home Assistant.")
        # 在实体移除时取消定时任务，防止内存泄漏
        if self._unsub_listener:
            self._unsub_listener()
            self._unsub_listener = None
            _LOGGER.debug(f"Cancelled daily update schedule for {self.entity_id}.")

    async def _schedule_update(self, now: datetime | None = None) -> None:
        """Callback for the scheduled time update."""
        _LOGGER.debug(f"Scheduled update triggered for {self.entity_id} at {now}.")
        await self._async_update_data()

    async def _async_update_data(self) -> None:
        """Fetch new state data for the sensor and update HA state."""
        _LOGGER.debug(f"Starting data fetch for {self.entity_id}")
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
                        _LOGGER.info(f"Holiday status for {self.entity_id} updated to: {self._state} ({holiday_typename})")
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
            _LOGGER.error(f"Failed to fetch holiday status for {self.entity_id}: API request timed out for {url}")
        except Exception as e:
            self._state = "错误"
            self._attributes = {"error": f"API请求失败: {e}"}
            _LOGGER.error(f"Failed to fetch holiday status for {self.entity_id}: {e}", exc_info=True)
        finally:
            # 无论成功或失败，都通知 Home Assistant 状态可能已更改
            self.async_write_ha_state()

    # 仍然保留 async_update 方法，以防用户手动从开发者工具调用 homeassistant.update_entity 服务
    async def async_update(self) -> None:
        """Manual update hook for Home Assistant."""
        _LOGGER.debug(f"Manual update triggered for {self.entity_id}.")
        await self._async_update_data()