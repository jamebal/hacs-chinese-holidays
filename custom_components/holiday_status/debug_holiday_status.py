import asyncio
import logging
import sys
import os
from datetime import date, timedelta
# import aiohttp # 不再需要在这里直接导入 aiohttp，因为 sensor.py 自己管理 session

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

# --- 移除所有 homeassistant.helpers.aiohttp_client 的 Mocking ---
# 因为 sensor.py 不再依赖它进行本地调试

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
        return

    my_sensor = added_entities[0]
    _LOGGER.info(f"传感器实例已创建: {my_sensor.name}")
    _LOGGER.info(f"传感器初始状态 (可能为 None): {my_sensor.state}")

    # 移除手动触发的第二次更新
    # _LOGGER.info("手动触发传感器更新...")
    # await my_sensor.async_update()

    _LOGGER.info(f"传感器更新后的状态: {my_sensor.state}")
    _LOGGER.info(f"传感器名称: {my_sensor.name}")
    _LOGGER.info(f"传感器唯一ID: {my_sensor.unique_id}")
    _LOGGER.info(f"传感器图标: {my_sensor.icon}")

    _LOGGER.info("--- 本地 Home Assistant 传感器调试结束 ---")

if __name__ == "__main__":
    # 强烈建议直接在命令行运行，以避免 PyCharm 调试器的干扰
    # python debug_holiday_status.py
    asyncio.run(main())