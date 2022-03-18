"""Govee BLE monitor integration."""
from datetime import timedelta
import logging
import voluptuous as vol
from typing import List, Optional, Dict, Set, Tuple

from bleson import get_provider  # type: ignore
from bleson.core.hci.constants import EVT_LE_ADVERTISING_REPORT  # type: ignore
from bleson.core.types import BDAddress  # type: ignore
from bleson.core.hci.type_converters import hex_string  # type: ignore

from homeassistant.exceptions import HomeAssistantError  # type: ignore
from homeassistant.components.sensor import PLATFORM_SCHEMA  # type: ignore
import homeassistant.helpers.config_validation as cv  # type: ignore
from homeassistant.helpers.entity import Entity  # type: ignore
from homeassistant.helpers.event import track_point_in_utc_time  # type: ignore
import homeassistant.util.dt as dt_util  # type: ignore

from homeassistant.const import (  # type: ignore
    DEVICE_CLASS_TEMPERATURE,
    DEVICE_CLASS_HUMIDITY,
    TEMP_CELSIUS,
    ATTR_BATTERY_LEVEL,
)

from .const import (
    CONF_DECIMALS,
    CONF_DEVICE_MAC,
    CONF_DEVICE_NAME,
    CONF_DEVICE_SENSOR_NUMBER,
    CONF_GOVEE_DEVICES,
    CONF_HCI_DEVICE,
    CONF_LOG_SPIKES,
    CONF_PERIOD,
    CONF_ROUNDING,
    CONF_TEMP_RANGE_MAX_CELSIUS,
    CONF_TEMP_RANGE_MIN_CELSIUS,
    CONF_USE_MEDIAN,
    DEFAULT_DECIMALS,
    DEFAULT_HCI_DEVICE,
    DEFAULT_LOG_SPIKES,
    DEFAULT_PERIOD,
    DEFAULT_ROUNDING,
    DEFAULT_TEMP_RANGE_MAX,
    DEFAULT_TEMP_RANGE_MIN,
    DEFAULT_USE_MEDIAN,
    DOMAIN,
)

from .govee_advertisement import GoveeAdvertisement
from .ble_ht import BLE_HT_data

###############################################################################

_LOGGER = logging.getLogger(__name__)

DEVICES_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_DEVICE_MAC): cv.string,
        vol.Optional(CONF_DEVICE_NAME): cv.string,
        vol.Optional(CONF_DEVICE_SENSOR_NUMBER): int,
    }
)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_ROUNDING, default=DEFAULT_ROUNDING): cv.boolean,
        vol.Optional(CONF_DECIMALS, default=DEFAULT_DECIMALS): cv.positive_int,
        vol.Optional(CONF_PERIOD, default=DEFAULT_PERIOD): cv.positive_int,
        vol.Optional(CONF_LOG_SPIKES, default=DEFAULT_LOG_SPIKES): cv.boolean,
        vol.Optional(CONF_USE_MEDIAN, default=DEFAULT_USE_MEDIAN): cv.boolean,
        vol.Optional(CONF_GOVEE_DEVICES): vol.All([DEVICES_SCHEMA]),
        vol.Optional(CONF_HCI_DEVICE, default=DEFAULT_HCI_DEVICE): cv.string,
        vol.Optional(
            CONF_TEMP_RANGE_MIN_CELSIUS, default=DEFAULT_TEMP_RANGE_MIN
        ): float,
        vol.Optional(
            CONF_TEMP_RANGE_MAX_CELSIUS, default=DEFAULT_TEMP_RANGE_MAX
        ): float,
    }
)

###############################################################################


#
# Configure for Home Assistant
#
def setup_platform(hass, config, add_entities, discovery_info=None) -> None:
    """Set up the sensor platform."""
    _LOGGER.debug("Starting Govee HCI Sensor")

    govee_devices: List[BLE_HT_data] = []  # Data objects of configured devices
    sensors_by_device = {}  # HomeAssistant sensors by their BLE_HT_data device
    adapter = None

    def handle_meta_event(hci_packet) -> None:
        """Handle recieved BLE data."""
        # If recieved BLE packet is of type ADVERTISING_REPORT
        if hci_packet.subevent_code == EVT_LE_ADVERTISING_REPORT:
            packet_mac = hci_packet.data[3:9]

            for device in govee_devices:
                # If recieved device data matches a configured govee device
                if BDAddress(device.mac) == BDAddress(packet_mac):
                    _LOGGER.debug(
                        "Received packet data for {}: {}".format(
                            BDAddress(device.mac), hex_string(hci_packet.data)
                        )
                    )
                    # parse packet data
                    ga = GoveeAdvertisement(hci_packet.data)

                    #  Check to make sure sensor numbers match
                    if ga.sensor_number != device.sensor_number:
                        continue

                    # If mfg data information is defined, update values
                    if ga.packet is not None:
                        device.update(ga.temperature, ga.humidity, ga.packet)

                    # Update RSSI and battery level
                    device.rssi = ga.rssi
                    device.battery = ga.battery

    def init_configureed_devices() -> None:
        """Initialize configured Govee devices."""
        for conf_dev in config[CONF_GOVEE_DEVICES]:
            # Initialize BLE HT data objects
            mac: str = conf_dev["mac"]
            given_name = conf_dev.get("name", None)
            sensor_number = conf_dev.get("sensor_number", 0)

            device = BLE_HT_data(mac, given_name, sensor_number)
            device.log_spikes = config[CONF_LOG_SPIKES]
            device.maximum_temperature = config[CONF_TEMP_RANGE_MAX_CELSIUS]
            device.minimum_temperature = config[CONF_TEMP_RANGE_MIN_CELSIUS]

            if config[CONF_ROUNDING]:
                device.decimal_places = config[CONF_DECIMALS]
            govee_devices.append(device)

            # Initialize HA sensors
            name = conf_dev.get("name", mac)
            temp_sensor = TemperatureSensor(mac, name, sensor_number)
            hum_sensor = HumiditySensor(mac, name, sensor_number)
            sensors = [temp_sensor, hum_sensor]
            sensors_by_device[device] = sensors
            add_entities(sensors)

    def update_ble_devices(config) -> None:
        """Discover Bluetooth LE devices."""
        # _LOGGER.debug("Discovering Bluetooth LE devices")
        use_median = config[CONF_USE_MEDIAN]

        ATTR = "_device_state_attributes"
        textattr = "last median of" if use_median else "last mean of"

        for device in govee_devices:
            sensors = sensors_by_device[device]

            _LOGGER.debug(
                "Last mfg data for {}: {}".format(
                    BDAddress(device.mac), device.last_packet
                )
            )

            if device.last_packet:
                if device.median_humidity is not None:
                    humstate_med = float(device.median_humidity)
                    getattr(sensors[1], ATTR)["median"] = humstate_med
                    if use_median:
                        setattr(sensors[1], "_state", humstate_med)

                if device.mean_humidity is not None:
                    humstate_mean = float(device.mean_humidity)
                    getattr(sensors[1], ATTR)["mean"] = humstate_mean
                    if not use_median:
                        setattr(sensors[1], "_state", humstate_mean)

                if device.median_temperature is not None:
                    tempstate_med = float(device.median_temperature)
                    getattr(sensors[0], ATTR)["median"] = tempstate_med
                    if use_median:
                        setattr(sensors[0], "_state", tempstate_med)

                if device.mean_temperature is not None:
                    tempstate_mean = float(device.mean_temperature)
                    getattr(sensors[0], ATTR)["mean"] = tempstate_mean
                    if not use_median:
                        setattr(sensors[0], "_state", tempstate_mean)

                for sensor in sensors:
                    last_packet = device.last_packet
                    getattr(sensor, ATTR)["last packet id"] = last_packet
                    getattr(sensor, ATTR)["rssi"] = device.rssi
                    getattr(sensor, ATTR)[ATTR_BATTERY_LEVEL] = device.battery
                    getattr(sensor, ATTR)[textattr] = device.data_size
                    sensor.async_schedule_update_ha_state()

                device.reset()

    def update_ble_loop(now) -> None:
        """Lookup Bluetooth LE devices and update status."""
        _LOGGER.debug("update_ble_loop called")
        adapter.start_scanning()

        try:
            # Time to make the dounuts
            update_ble_devices(config)
        except RuntimeError as error:
            _LOGGER.error("Error during Bluetooth LE scan: %s", error)

        time_offset = dt_util.utcnow() + timedelta(seconds=config[CONF_PERIOD])
        # update_ble_loop() will be called again after time_offset
        track_point_in_utc_time(hass, update_ble_loop, time_offset)

    ###########################################################################

    # Initalize bluetooth adapter and begin scanning
    # XXX: will not work if there are more than 10 HCI devices
    try:
        adapter = get_provider().get_adapter(int(config[CONF_HCI_DEVICE][-1]))
        adapter._handle_meta_event = handle_meta_event
        hass.bus.listen("homeassistant_stop", adapter.stop_scanning)
        adapter.start_scanning()
    except (RuntimeError, OSError, PermissionError) as error:
        error_msg = "Error connecting to Bluetooth adapter: {}\n\n".format(error)
        error_msg += "Bluetooth adapter troubleshooting:\n"
        error_msg += "  -If running HASS, ensure the correct HCI device is being"
        error_msg += " used. Check by logging into HA command line and execute:\n"
        error_msg += "          gdbus introspect --system --dest org.bluez --object-path /org/bluez | fgrep -i hci\n"
        error_msg += "  -If running Home Assistant in Docker, "
        error_msg += "make sure it run with the --privileged flag.\n"
        # _LOGGER.error(error_msg)
        raise HomeAssistantError(error_msg) from error

    # Initialize configured Govee devices
    init_configureed_devices()
    # Begin sensor update loop
    update_ble_loop(dt_util.utcnow())


###############################################################################

#
# HomeAssistant Temperature Sensor Class
#
class TemperatureSensor(Entity):
    """Representation of a sensor."""

    def __init__(self, mac: str, name: str, sensor_number: int):
        """Initialize the sensor."""
        self._state = None
        self._battery = None
        self._unique_id = "t_{}_{}".format(mac.replace(":", ""), sensor_number)
        self._name = name
        self._mac = mac.replace(":", "")
        self._device_state_attributes = {}

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return "{} temp".format(self._name)

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return TEMP_CELSIUS

    @property
    def device_class(self):
        """Return the unit of measurement."""
        return DEVICE_CLASS_TEMPERATURE

    @property
    def device_info(self) -> Optional[Dict[str, Set[Tuple[str, str]]]]:
        """Temperature Device Info."""
        return {
            "identifiers": {(DOMAIN, self._mac)},
            "name": self._name,
            "manufacturer": "Govee",
        }

    @property
    def should_poll(self) -> bool:
        """No polling needed."""
        return False

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self._device_state_attributes

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return self._unique_id

    @property
    def force_update(self) -> bool:
        """Force update."""
        return True


#
# HomeAssistant Humidity Sensor Class
#
class HumiditySensor(Entity):
    """Representation of a Sensor."""

    def __init__(self, mac: str, name: str, sensor_number: int):
        """Initialize the sensor."""
        self._state = None
        self._battery = None
        self._name = name
        self._unique_id = "h_{}_{}".format(mac.replace(":", ""), sensor_number)
        self._mac = mac.replace(":", "")
        self._device_state_attributes = {}

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return "{} humidity".format(self._name)

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return "%"

    @property
    def device_class(self):
        """Return the unit of measurement."""
        return DEVICE_CLASS_HUMIDITY

    @property
    def device_info(self) -> Optional[Dict[str, Set[Tuple[str, str]]]]:
        """Humidity Device Info."""
        return {
            "identifiers": {(DOMAIN, self._mac)},
            "name": self._name,
            "manufacturer": "Govee",
        }

    @property
    def should_poll(self) -> bool:
        """No polling needed."""
        return False

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return self._device_state_attributes

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return self._unique_id

    @property
    def force_update(self) -> bool:
        """Force update."""
        return True
