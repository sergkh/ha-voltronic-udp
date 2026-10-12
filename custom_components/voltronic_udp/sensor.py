"""Sensor platform for the Voltronic UDP integration."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import DOMAIN
from .coordinator import VoltronicCoordinator


MEASUREMENT = SensorStateClass.MEASUREMENT
TOTAL_INCREASING = SensorStateClass.TOTAL_INCREASING

# QMOD is a one-character Voltronic PIP protocol value.  Expose clear states
# in Home Assistant, but retain the exact raw value as an entity attribute.
OPERATING_MODES = {
    "P": "Power on",
    "S": "Standby",
    "L": "Line mode",
    "B": "Battery mode",
    "F": "Fault",
    "H": "Power saving",
}

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
    SensorEntityDescription(key="pv_input_power", name="PV input power", native_unit_of_measurement="W", device_class=SensorDeviceClass.POWER, state_class=MEASUREMENT),
    SensorEntityDescription(key="battery_voltage_scc", name="Battery voltage SCC", native_unit_of_measurement="V", device_class=SensorDeviceClass.VOLTAGE, state_class=MEASUREMENT),
    SensorEntityDescription(key="battery_discharge_current", name="Battery discharge current", native_unit_of_measurement="A", device_class=SensorDeviceClass.CURRENT, state_class=MEASUREMENT),
    SensorEntityDescription(key="model", name="Model", entity_category=EntityCategory.DIAGNOSTIC),
    SensorEntityDescription(
        key="operating_mode",
        name="Operating mode",
        device_class=SensorDeviceClass.ENUM,
        options=list(OPERATING_MODES.values()),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[VoltronicCoordinator],
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Voltronic sensors for a config entry."""
    coordinator = entry.runtime_data
    entities = [VoltronicSensor(coordinator, entry, description) for description in SENSORS]
    entities.append(VoltronicPvEnergySensor(coordinator, entry))
    async_add_entities(entities)


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
        value = self.coordinator.data.get(self.entity_description.key)
        if self.entity_description.key == "operating_mode":
            return OPERATING_MODES.get(value)
        return value

    @property
    def extra_state_attributes(self) -> dict[str, str] | None:
        """Keep the raw PIP mode code available for diagnostics."""
        if self.entity_description.key != "operating_mode":
            return None
        if (raw_mode := self.coordinator.data.get("operating_mode")) is None:
            return None
        return {"protocol_mode": raw_mode}


class VoltronicPvEnergySensor(CoordinatorEntity[VoltronicCoordinator], RestoreSensor):
    """Integrate PV input power into a persistent energy-production counter."""

    _attr_has_entity_name = True
    _attr_name = "PV input energy"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = "kWh"
    _attr_state_class = TOTAL_INCREASING
    _attr_suggested_display_precision = 3

    def __init__(
        self,
        coordinator: VoltronicCoordinator,
        entry: ConfigEntry[VoltronicCoordinator],
    ) -> None:
        """Initialize the energy counter at zero or its restored value."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_pv_input_energy"
        self._entry_id = entry.entry_id
        self._energy = 0.0
        self._last_power: float | None = None
        self._last_sample: datetime | None = None

    @property
    def device_info(self) -> DeviceInfo:
        """Associate this counter with the inverter device."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry_id)},
            name="Voltronic UDP Inverter",
            manufacturer="Voltronic-compatible",
            model=self.coordinator.data.get("model") or "PIP UDP bridge",
        )

    @property
    def native_value(self) -> float:
        """Return the monotonic, accumulated energy in kWh."""
        return round(self._energy, 3)

    async def async_added_to_hass(self) -> None:
        """Restore the accumulated energy without estimating a downtime gap."""
        await super().async_added_to_hass()
        if (last_data := await self.async_get_last_sensor_data()) is not None:
            try:
                self._energy = float(last_data.native_value)
            except (TypeError, ValueError):
                pass
        self._last_power = self._current_power()
        self._last_sample = dt_util.utcnow()

    def _current_power(self) -> float | None:
        power = self.coordinator.data.get("pv_input_power")
        return float(power) if isinstance(power, (int, float)) and power >= 0 else None

    @callback
    def _handle_coordinator_update(self) -> None:
        """Integrate two consecutive PV-power samples using the trapezoid rule."""
        now = dt_util.utcnow()
        power = self._current_power()
        if power is not None and self._last_power is not None and self._last_sample is not None:
            elapsed_seconds = (now - self._last_sample).total_seconds()
            max_gap = max(self.coordinator.update_interval.total_seconds() * 3, 120)
            if 0 < elapsed_seconds <= max_gap:
                self._energy += (self._last_power + power) * elapsed_seconds / 7_200_000

        self._last_power = power
        self._last_sample = now
        super()._handle_coordinator_update()
