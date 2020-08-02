"""Govee BLE monitor integration."""
from datetime import timedelta
import logging
import voluptuous as vol
from typing import List

from bleson import get_provider  # type: ignore
from bleson.core.hci.constants import EVT_LE_ADVERTISING_REPORT  # type: ignore
from bleson.core.types import BDAddress  # type: ignore
from bleson.core.hci.type_converters import hex_string  # type: ignore

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
    DEFAULT_ROUNDING,
    DEFAULT_DECIMALS,
    DEFAULT_PERIOD,
    DEFAULT_LOG_SPIKES,
    DEFAULT_USE_MEDIAN,
    DEFAULT_HCITOOL_ACTIVE,
    DEFAULT_HCI_DEVICE,
    CONF_ROUNDING,
    CONF_DECIMALS,
    CONF_PERIOD,
    CONF_LOG_SPIKES,
    CONF_USE_MEDIAN,
    CONF_HCITOOL_ACTIVE,
    CONF_HCI_DEVICE,
    CONF_GOVEE_DEVICES,
    CONF_DEVICE_MAC,
    CONF_DEVICE_NAME,
)

from .govee_advertisement import GoveeAdvertisement
from .ble_ht import BLE_HT_data

###############################################################################

_LOGGER = logging.getLogger(__name__)

DEVICES_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_DEVICE_MAC): cv.string,
        vol.Optional(CONF_DEVICE_NAME): cv.string,
    }
)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_ROUNDING, default=DEFAULT_ROUNDING): cv.boolean,
        vol.Optional(CONF_DECIMALS, default=DEFAULT_DECIMALS): cv.positive_int,
        vol.Optional(CONF_PERIOD, default=DEFAULT_PERIOD): cv.positive_int,
        vol.Optional(CONF_LOG_SPIKES, default=DEFAULT_LOG_SPIKES): cv.boolean,
        vol.Optional(CONF_USE_MEDIAN, default=DEFAULT_USE_MEDIAN): cv.boolean,
        vol.Optional(
            CONF_HCITOOL_ACTIVE, default=DEFAULT_HCITOOL_ACTIVE
        ): cv.boolean,  # noqa
        vol.Optional(CONF_GOVEE_DEVICES): vol.All([DEVICES_SCHEMA]),
        vol.Optional(CONF_HCI_DEVICE, default=DEFAULT_HCI_DEVICE): cv.string,
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
    sensors_by_mac = {}  # HomeAssistant sensors by MAC address

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
            mac = conf_dev["mac"]
            device = BLE_HT_data(mac, conf_dev.get("name", None))
            device.log_spikes = config[CONF_LOG_SPIKES]
            if config[CONF_ROUNDING]:
                device.decimal_places = config[CONF_DECIMALS]
            govee_devices.append(device)

            # Initialize HA sensors
            name = conf_dev.get("name", mac)
            temp_sensor = TemperatureSensor(mac, name)
            hum_sensor = HumiditySensor(mac, name)
            sensors = [temp_sensor, hum_sensor]
            sensors_by_mac[mac] = sensors
            add_entities(sensors)

    def update_ble_devices(config) -> None:
        """Discover Bluetooth LE devices."""
        # _LOGGER.debug("Discovering Bluetooth LE devices")
        use_median = config[CONF_USE_MEDIAN]

        ATTR = "_device_state_attributes"
        textattr = "last median of" if use_median else "last mean of"

        for device in govee_devices:
            sensors = sensors_by_mac[device.mac]

            _LOGGER.debug(
                "Last mfg data for {}: {}".format(
                    BDAddress(device.mac), device.last_packet
                )
            )

            if device.last_packet:
                humstate_med = float(device.median_humidity)
                humstate_mean = float(device.mean_humidity)
                tempstate_med = float(device.median_temperature)
                tempstate_mean = float(device.mean_temperature)

                getattr(sensors[0], ATTR)["median"] = tempstate_med
                getattr(sensors[0], ATTR)["mean"] = tempstate_mean
                if use_median:
                    setattr(sensors[0], "_state", tempstate_med)
                else:
                    setattr(sensors[0], "_state", tempstate_mean)

                getattr(sensors[1], ATTR)["median"] = humstate_med
                getattr(sensors[1], ATTR)["mean"] = humstate_mean

                if use_median:
                    setattr(sensors[1], "_state", humstate_med)
                else:
                    setattr(sensors[1], "_state", humstate_mean)

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
    adapter = get_provider().get_adapter(int(config[CONF_HCI_DEVICE][-1]))
    adapter._handle_meta_event = handle_meta_event
    hass.bus.listen("homeassistant_stop", adapter.stop_scanning)
    adapter.start_scanning()

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

    def __init__(self, mac: str, name: str):
        """Initialize the sensor."""
        self._state = None
        self._battery = None
        self._unique_id = "t_" + mac.replace(":", "")
        self._name = name
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
    def should_poll(self) -> bool:
        """No polling needed."""
        return False

    @property
    def device_state_attributes(self):
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

    def __init__(self, mac: str, name: str):
        """Initialize the sensor."""
        self._state = None
        self._battery = None
        self._name = name
        self._unique_id = "h_" + mac.replace(":", "")
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
    def should_poll(self) -> bool:
        """No polling needed."""
        return False

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return self._device_state_attributes

    @property
    def unique_id(self):
        """Return a unique ID."""
        return self._unique_id

    @property
    def force_update(self) -> bool:
        """Force update."""
        return True
