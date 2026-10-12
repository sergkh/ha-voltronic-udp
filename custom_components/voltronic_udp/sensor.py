"""Sensor platform for the Voltronic UDP integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import VoltronicCoordinator


MEASUREMENT = SensorStateClass.MEASUREMENT

SENSORS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(key="grid_voltage", name="Grid voltage", native_unit_of_measurement="V", device_class=SensorDeviceClass.VOLTAGE, state_class=MEASUREMENT),
    SensorEntityDescription(key="grid_frequency", name="Grid frequency", native_unit_of_measurement="Hz", device_class=SensorDeviceClass.FREQUENCY, state_class=MEASUREMENT),
    SensorEntityDescription(key="output_voltage", name="Output voltage", native_unit_of_measurement="V", device_class=SensorDeviceClass.VOLTAGE, state_class=MEASUREMENT),
    SensorEntityDescription(key="output_frequency", name="Output frequency", native_unit_of_measurement="Hz", device_class=SensorDeviceClass.FREQUENCY, state_class=MEASUREMENT),
    SensorEntityDescription(key="output_apparent_power", name="Output apparent power", native_unit_of_measurement="VA", device_class=SensorDeviceClass.APPARENT_POWER, state_class=MEASUREMENT),
    SensorEntityDescription(key="output_active_power", name="Output active power", native_unit_of_measurement="W", device_class=SensorDeviceClass.POWER, state_class=MEASUREMENT),
    SensorEntityDescription(key="load_percent", name="Load", native_unit_of_measurement="%", state_class=MEASUREMENT),
    SensorEntityDescription(key="bus_voltage", name="Bus voltage", native_unit_of_measurement="V", device_class=SensorDeviceClass.VOLTAGE, state_class=MEASUREMENT),
    SensorEntityDescription(key="battery_voltage", name="Battery voltage", native_unit_of_measurement="V", device_class=SensorDeviceClass.VOLTAGE, state_class=MEASUREMENT),
    SensorEntityDescription(key="battery_charge_current", name="Battery charge current", native_unit_of_measurement="A", device_class=SensorDeviceClass.CURRENT, state_class=MEASUREMENT),
    SensorEntityDescription(key="battery_capacity", name="Battery capacity", native_unit_of_measurement="%", device_class=SensorDeviceClass.BATTERY, state_class=MEASUREMENT),
    SensorEntityDescription(key="inverter_temperature", name="Inverter temperature", native_unit_of_measurement="°C", device_class=SensorDeviceClass.TEMPERATURE, state_class=MEASUREMENT),
    SensorEntityDescription(key="pv_input_current", name="PV input current", native_unit_of_measurement="A", device_class=SensorDeviceClass.CURRENT, state_class=MEASUREMENT),
    SensorEntityDescription(key="pv_input_voltage", name="PV input voltage", native_unit_of_measurement="V", device_class=SensorDeviceClass.VOLTAGE, state_class=MEASUREMENT),
    SensorEntityDescription(key="battery_voltage_scc", name="Battery voltage SCC", native_unit_of_measurement="V", device_class=SensorDeviceClass.VOLTAGE, state_class=MEASUREMENT),
    SensorEntityDescription(key="battery_discharge_current", name="Battery discharge current", native_unit_of_measurement="A", device_class=SensorDeviceClass.CURRENT, state_class=MEASUREMENT),
    SensorEntityDescription(key="model", name="Model", entity_category=EntityCategory.DIAGNOSTIC),
    SensorEntityDescription(
        key="operating_mode",
        name="Operating mode",
        device_class=SensorDeviceClass.ENUM,
        options=["P", "S", "L", "B", "F", "H"],
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[VoltronicCoordinator],
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Voltronic sensors for a config entry."""
    coordinator = entry.runtime_data
    async_add_entities(VoltronicSensor(coordinator, entry, description) for description in SENSORS)


class VoltronicSensor(CoordinatorEntity[VoltronicCoordinator], SensorEntity):
    """Represent one read-only inverter metric."""

    entity_description: SensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: VoltronicCoordinator,
        entry: ConfigEntry[VoltronicCoordinator],
        description: SensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._entry_id = entry.entry_id

    @property
    def device_info(self) -> DeviceInfo:
        """Return information for the single inverter device."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry_id)},
            name="Voltronic UDP Inverter",
            manufacturer="Voltronic-compatible",
            model=self.coordinator.data.get("model") or "PIP UDP bridge",
        )

    @property
    def native_value(self) -> Any:
        """Return the latest value supplied by the coordinator."""
        return self.coordinator.data.get(self.entity_description.key)
