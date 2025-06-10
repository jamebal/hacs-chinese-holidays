import asyncio
import logging
import sys
import os
from datetime import date, timedelta
import aiohttp # 确保这里导入了 aiohttp

# 配置日志，以便看到您的集成中的调试信息
logging.basicConfig(level=logging.DEBUG)
_LOGGER = logging.getLogger(__name__)

# 动态添加 custom_components 目录到 Python 模块搜索路径
current_dir = os.path.dirname(os.path.abspath(__file__))
custom_components_path = os.path.join(current_dir, 'custom_components')
sys.path.insert(0, custom_components_path)

# --- 模拟 Home Assistant 内部对象 ---
class MockHass:
    """模拟 HomeAssistant 对象，只包含您的传感器需要的部分"""
    def __init__(self):
        self.data = {}
        self._loop = asyncio.get_event_loop()
        _LOGGER.debug("MockHass initialized")

    def async_create_task(self, coro):
        """模拟 hass.async_create_task"""
        _LOGGER.debug("MockHass.async_create_task called for: %s", coro.__name__)
        return self._loop.create_task(coro)

    def setdefault(self, key, value):
        """模拟 dict.setdefault"""
        return self.data.setdefault(key, value)

    @property
    def loop(self):
        """模拟 hass.loop"""
        return self._loop

# --- 模块级别 Mocking Home Assistant 的 aiohttp_client ---
# 必须在导入 sensor.py 之前进行此操作

# 导入 Home Assistant 实际的 aiohttp_client 模块
import homeassistant.helpers.aiohttp_client as original_aiohttp_client_module

# 一个全局的 aiohttp.ClientSession 实例，供模拟函数使用
_mock_session_instance = None

# 注意：这个函数不再是 async def！它现在是同步的。
def _mock_get_clientsession_sync(hass_obj):
    """
    一个简单的模拟函数，替换 homeassistant.helpers.aiohttp_client.async_get_clientsession。
    它不依赖 hass_obj.bus，直接返回一个 aiohttp.ClientSession 实例。
    """
    global _mock_session_instance
    if _mock_session_instance is None:
        _LOGGER.debug("Mocking aiohttp_client.async_get_clientsession: Creating new aiohttp.ClientSession() synchronously")
        _mock_session_instance = aiohttp.ClientSession() # 这里直接创建同步的 ClientSession
    return _mock_session_instance

# 将原始函数替换为我们的同步模拟函数
original_aiohttp_client_module.async_get_clientsession = _mock_get_clientsession_sync
_LOGGER.debug("homeassistant.helpers.aiohttp_client.async_get_clientsession has been mocked (synchronously).")

# 现在可以从您的自定义集成中导入模块了
try:
    from holiday_status.const import (
        DOMAIN, SENSOR_NAME, ICON, HOLIDAY_API_URL, API_TIMEOUT,
        STATE_WEEKDAY, STATE_WEEKEND, STATE_HOLIDAY, SCAN_INTERVAL
    )
    from holiday_status.sensor import HolidayStatusSensor # 导入您的传感器类
except ImportError as e:
    _LOGGER.error(f"无法导入自定义集成模块。请确认文件路径和虚拟环境设置正确。错误: {e}")
    _LOGGER.error(f"当前 sys.path: {sys.path}")
    _LOGGER.error(f"尝试导入路径: {custom_components_path}")
    sys.exit(1)

# 模拟 async_add_entities 回调函数
added_entities = []
def mock_add_entities(entities_to_add, update_before_add=False):
    """模拟 async_add_entities，存储添加的实体"""
    _LOGGER.debug(f"mock_add_entities called with {len(entities_to_add)} entities. update_before_add: {update_before_add}")
    for entity in entities_to_add:
        added_entities.append(entity)
        if update_before_add:
            # 如果 Home Assistant 会在添加前更新实体，我们在这里模拟
            _LOGGER.debug(f"Simulating initial update for {entity.name}")
            asyncio.create_task(entity.async_update())

# --- 主调试逻辑 ---
async def main():
    _LOGGER.info("--- 启动本地 Home Assistant 传感器调试 ---")

    mock_hass = MockHass()

    _LOGGER.debug("Calling async_setup_platform for holiday_status sensor...")
    sensor_instance = HolidayStatusSensor(mock_hass) # 传入 mock_hass
    mock_add_entities([sensor_instance], True) # 模拟 Home Assistant 启动时添加并更新

    if not added_entities:
        _LOGGER.error("没有传感器实体被添加，调试终止。")
        if _mock_session_instance:
            await _mock_session_instance.close() # 关闭可能已创建的session
        return

    my_sensor = added_entities[0]
    _LOGGER.info(f"传感器实例已创建: {my_sensor.name}")
    _LOGGER.info(f"传感器初始状态 (可能为 None): {my_sensor.state}")

    # 手动调用传感器的 async_update 方法来获取最新状态
    _LOGGER.info("手动触发传感器更新...")
    await my_sensor.async_update()

    _LOGGER.info(f"传感器更新后的状态: {my_sensor.state}")
    _LOGGER.info(f"传感器名称: {my_sensor.name}")
    _LOGGER.info(f"传感器唯一ID: {my_sensor.unique_id}")
    _LOGGER.info(f"传感器图标: {my_sensor.icon}")

    # 调试结束时关闭模拟的 session
    if _mock_session_instance:
        await _mock_session_instance.close()

    _LOGGER.info("--- 本地 Home Assistant 传感器调试结束 ---")

if __name__ == "__main__":
    asyncio.run(main())