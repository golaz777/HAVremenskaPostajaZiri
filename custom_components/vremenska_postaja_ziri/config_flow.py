"""Config flow for Vremenska postaja Žiri integration."""
from __future__ import annotations

from typing import Any
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    CONF_GROUPS,
    CONF_RIVER_WARNING_LEVEL,
    CONF_SCAN_INTERVAL,
    DEFAULT_RIVER_WARNING_LEVEL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    GROUPS,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Vremenska postaja Žiri."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            return self.async_create_entry(title="Vremenska postaja Žiri", data={})

        return self.async_show_form(step_id="user")

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> OptionsFlowHandler:
        """Return the options flow."""
        return OptionsFlowHandler()


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Choose data groups, polling interval and the river warning level."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            user_input[CONF_SCAN_INTERVAL] = int(user_input[CONF_SCAN_INTERVAL])
            user_input[CONF_RIVER_WARNING_LEVEL] = int(user_input[CONF_RIVER_WARNING_LEVEL])
            return self.async_create_entry(data=user_input)

        options = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_GROUPS, default=options.get(CONF_GROUPS, GROUPS)
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=GROUPS,
                        multiple=True,
                        mode=SelectSelectorMode.LIST,
                        translation_key="groups",
                    )
                ),
                vol.Required(
                    CONF_SCAN_INTERVAL,
                    default=options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=MIN_SCAN_INTERVAL,
                        max=MAX_SCAN_INTERVAL,
                        step=1,
                        mode=NumberSelectorMode.BOX,
                        unit_of_measurement="min",
                    )
                ),
                vol.Required(
                    CONF_RIVER_WARNING_LEVEL,
                    default=options.get(CONF_RIVER_WARNING_LEVEL, DEFAULT_RIVER_WARNING_LEVEL),
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=1,
                        max=1000,
                        step=1,
                        mode=NumberSelectorMode.BOX,
                        unit_of_measurement="cm",
                    )
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
