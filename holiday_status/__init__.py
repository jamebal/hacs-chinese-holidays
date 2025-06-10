"""The holiday_status integration."""
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# List of platforms that this integration supports.
PLATFORMS = ["sensor"]


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the holiday_status component."""
    _LOGGER.debug("Setting up holiday_status component")
    hass.data.setdefault(DOMAIN, {})

    # If you had configuration in configuration.yaml, you'd process it here.
    # For a simple sensor, we directly load the platform.
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(ConfigEntry("", {}, DOMAIN, ""), platform)
        for platform in PLATFORMS
    )

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data.pop(DOMAIN)
    return unload_ok