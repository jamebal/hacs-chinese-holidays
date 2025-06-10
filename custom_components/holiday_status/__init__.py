"""The holiday_status component."""
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)

DOMAIN = "holiday_status"

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the holiday_status component."""
    _LOGGER.debug("Setting up holiday_status component")
    # No custom setup logic needed here as the sensor platform handles everything.
    # The sensor platform will be automatically discovered and set up.
    return True