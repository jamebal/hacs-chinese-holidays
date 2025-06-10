"""Platform for sensor integration."""
from __future__ import annotations

import logging
from datetime import date, timedelta
import asyncio

import aiohttp # 确保这里导入了 aiohttp

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
# 这里不再直接导入 async_get_clientsession，因为它会在 async_update 中动态获取或创建 session
# from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN,
    SENSOR_NAME,
    ICON,
    HOLIDAY_API_URL,
    API_TIMEOUT,
    STATE_WEEKDAY,
    STATE_WEEKEND,
    STATE_HOLIDAY,
    SCAN_INTERVAL
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the holiday_status sensor platform."""
    _LOGGER.debug("Setting up holiday_status sensor")
    async_add_entities([HolidayStatusSensor(hass)], True)


class HolidayStatusSensor(SensorEntity):
    """Representation of a Holiday Status Sensor."""

    _attr_name = SENSOR_NAME
    _attr_icon = ICON
    _attr_unique_id = f"{DOMAIN}_today_status_sensor"
    _attr_state = None  # Initial state
    _attr_should_poll = True
    _attr_force_update = False
    _attr_scan_interval = SCAN_INTERVAL

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the sensor."""
        self._hass = hass
        # 不再在 __init__ 中创建 session
        # self._session = async_get_clientsession(hass)
        self._cached_month_data = None
        self._cached_month_year_str = None

    async def async_update(self) -> None:
        """Fetch new state data for the sensor."""
        today = date.today()
        today_year_month_str = today.strftime("%Y%m")
        today_day_str_for_api_key = today.strftime("%m%d")

        # Home Assistant 推荐的方式是在 async_update 中获取 session
        # 或者在更高级的 setup_entry 中获取并传递
        # 为了本地调试方便，我们这里直接创建一个临时的session，并使用 async with
        # 在实际的 Home Assistant 中，您会使用 hass.helpers.aiohttp_client.async_get_clientsession(self._hass)
        # 但为了本地调试，我们将修改 debug_holiday_status.py 来模拟它
        session = None
        try:
            # 获取或创建客户端会话
            # 在实际的HA中，这里是 hass.helpers.aiohttp_client.async_get_clientsession(self._hass)
            # 在本地调试中，这个会被 debug_holiday_status.py 模拟的函数替换
            from homeassistant.helpers.aiohttp_client import async_get_clientsession
            session = async_get_clientsession(self._hass) # 确保这里是同步的ClientSession，由mock提供

            # Check if we need to fetch new monthly data or use cache
            if self._cached_month_year_str != today_year_month_str:
                _LOGGER.debug("Fetching new month data for %s from API", today_year_month_str)
                api_url = HOLIDAY_API_URL.format(today_year_month_str)

                # 使用 async with 来确保 session 和 response 正确关闭
                async with session.get(api_url, timeout=API_TIMEOUT) as response:
                    response.raise_for_status()
                    full_month_data = await response.json()

                    if not full_month_data or today_year_month_str not in full_month_data:
                        _LOGGER.error("API response for %s is malformed or missing expected month key: %s", today_year_month_str, full_month_data)
                        self._attr_state = None
                        return

                    self._cached_month_data = full_month_data[today_year_month_str]
                    self._cached_month_year_str = today_year_month_str
                    _LOGGER.debug("Successfully fetched and cached data for month %s", today_year_month_str)
            else:
                _LOGGER.debug("Using cached month data for %s", today_year_month_str)

            # Now, get the specific day's data from the cached month data
            day_data = self._cached_month_data.get(today_day_str_for_api_key)

            if not day_data:
                _LOGGER.warning("No data found for date %s in cached month data. Defaulting to workday.", today_day_str_for_api_key)
                self._attr_state = STATE_WEEKDAY
                return

            api_type = day_data.get("type")

            if api_type == 0:
                self._attr_state = STATE_WEEKDAY
                _LOGGER.debug("API reports %s (type 0) as: %s", today.strftime("%Y-%m-%d"), STATE_WEEKDAY)
            elif api_type == 1:
                if today.weekday() >= 5: # Saturday (5) or Sunday (6)
                    self._attr_state = STATE_WEEKEND
                    _LOGGER.debug("API reports %s (type 1) on a weekend day, setting to: %s", today.strftime("%Y-%m-%d"), STATE_WEEKEND)
                else:
                    self._attr_state = STATE_HOLIDAY
                    _LOGGER.debug("API reports %s (type 1) on a weekday, setting to: %s", today.strftime("%Y-%m-%d"), STATE_HOLIDAY)
            else:
                _LOGGER.warning("Unknown API type %s for date %s. Defaulting to workday.", api_type, today.strftime("%Y-%m-%d"))
                self._attr_state = STATE_WEEKDAY

        except aiohttp.ClientError as e:
            _LOGGER.error("Error connecting to holiday API for %s: %s", today.strftime("%Y-%m-%d"), e)
            self._attr_state = None
        except asyncio.TimeoutError:
            _LOGGER.error("Timeout occurred while connecting to holiday API for %s", today.strftime("%Y-%m-%d"))
            self._attr_state = None
        except Exception as e:
            _LOGGER.error("An unexpected error occurred while updating holiday status for %s: %s", today.strftime("%Y-%m-%d"), e)
            self._attr_state = None
        finally:
            # 这里的 finally 不应该关闭 session，因为它是由外部管理的
            # if session and not session.closed:
            #     await session.close() # 这一行在 HA 环境中不应该有，因为 session 是共享的
            pass

        _LOGGER.info("Current holiday status for %s: %s", today.strftime("%Y-%m-%d"), self._attr_state)