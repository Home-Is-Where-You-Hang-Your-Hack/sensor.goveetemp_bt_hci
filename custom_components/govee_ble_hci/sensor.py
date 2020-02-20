"""Govee BLE monitor integration."""
from datetime import timedelta
import logging
import os
import statistics as sts
import struct
import subprocess
import sys
import tempfile
import voluptuous as vol

from homeassistant.const import (
    DEVICE_CLASS_TEMPERATURE,
    DEVICE_CLASS_HUMIDITY,
    TEMP_CELSIUS,
    ATTR_BATTERY_LEVEL,
)
from homeassistant.components.sensor import PLATFORM_SCHEMA
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import track_point_in_utc_time
import homeassistant.util.dt as dt_util

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
    CONF_TMIN,
    CONF_TMAX,
    CONF_HMIN,
    CONF_HMAX,
    CONF_GOVEE_DEVICES,
    CONF_DEVICE_MAC,
    CONF_DEVICE_NAME,
)

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
# Reverse MAC octet order
#
def reverse_mac(rmac):
    """Change LE order to BE."""
    if len(rmac) != 12:
        return None

    reversed_mac = rmac[10:12]
    reversed_mac += rmac[8:10]
    reversed_mac += rmac[6:8]
    reversed_mac += rmac[4:6]
    reversed_mac += rmac[2:4]
    reversed_mac += rmac[0:2]
    return reversed_mac


#
# Parse Govee H5074 message from hcitool
#
def parse_raw_message_gvh5074(data):
    """Parse the raw data."""
    # _LOGGER.debug(data)
    if data is None:
        return None

    if not data.startswith("043E170201040") or "88EC" not in data:
        return None

    # check if RSSI is valid
    (rssi,) = struct.unpack("<b", bytes.fromhex(data[-2:]))
    if not 0 >= rssi >= -127:
        return None

    # check for MAC presence in message and in service data
    device_mac_reversed = data[14:26]

    temp_lsb = str(data[40:42]) + str(data[38:40])
    hum_lsb = str(data[44:46]) + str(data[42:44])

    # parse Govee Encoded data
    govee_encoded_data = temp_lsb + hum_lsb

    hum_int = int(hum_lsb, 16)

    # Negative temperature stred in two's complement
    if str(data[40:42]) == "FF":
        temp_int = int(str(data[38:40]), 16) - 255
    else:
        temp_int = int(temp_lsb, 16)

    # parse battery percentage
    battery = int(data[46:48], 16)

    result = {
        "rssi": int(rssi),
        "mac": reverse_mac(device_mac_reversed),
        "temperature": float(temp_int / 100),
        "humidity": float(hum_int / 100),
        "battery": float(battery),
        "packet": govee_encoded_data,
    }

    return result


#
# Parse Govee H5075 message from hcitool
#
def parse_raw_message_gvh5075(data):
    """Parse the raw data."""
    # _LOGGER.debug(data)
    if data is None:
        return None

    # check for Govee H5075 name prefix "GVH5075_"
    GVH5075_index = data.find("475648353037355F", 32)
    if GVH5075_index == -1:
        return None

    # check LE General Discoverable Mode and BR/EDR Not Supported
    adv_index = data.find("020105", 64, 71)
    if adv_index == -1:
        return None

    # check if RSSI is valid
    (rssi,) = struct.unpack("<b", bytes.fromhex(data[-2:]))
    if not 0 >= rssi >= -127:
        return None

    # check for MAC presence in message and in service data
    device_mac_reversed = data[14:26]

    # parse Govee Encoded data
    govee_encoded_data = int(data[80:86], 16)

    # parse battery percentage
    battery = int(data[86:88], 16)

    result = {
        "rssi": int(rssi),
        "mac": reverse_mac(device_mac_reversed),
        "temperature": float(govee_encoded_data / 10000),
        "humidity": float((govee_encoded_data % 1000) / 10),
        "battery": float(battery),
        "packet": govee_encoded_data,
    }

    return result


#
# BLEScanner class
#
class BLEScanner:
    """BLE scanner."""

    hcitool = None
    hcidump = None
    tempf = tempfile.TemporaryFile(mode="w+b")
    devnull = (
        subprocess.DEVNULL
        if sys.version_info > (3, 0)
        else open(os.devnull, "wb")  # noqa
    )

    #
    # Start scanning with hcitool and hcidump
    #
    def start(self, config):
        """Start receiving broadcasts."""
        _LOGGER.debug("Start receiving broadcasts")

        _LOGGER.debug(config[CONF_GOVEE_DEVICES])

        hci_device = config[CONF_HCI_DEVICE]

        # is hcitool in active or passive mode
        hcitool_active = config[CONF_HCITOOL_ACTIVE]

        hcitoolcmd = ["hcitool", "-i", hci_device, "lescan", "--duplicates"]

        if not hcitool_active:
            hcitoolcmd.append("--passive")

        # hcitool subprecess
        self.hcitool = subprocess.Popen(
            hcitoolcmd, stdout=self.devnull, stderr=self.devnull
        )

        # hcidump subprecess
        self.hcidump = subprocess.Popen(
            ["hcidump", "-i", hci_device, "--raw", "hci"],
            stdout=self.tempf,
            stderr=self.devnull,
        )

    #
    # Stop scanning
    #
    def stop(self):
        """Stop receiving broadcasts."""
        _LOGGER.debug("Stop receiving broadcasts")
        self.hcidump.terminate()
        self.hcidump.communicate()
        self.hcitool.terminate()
        self.hcitool.communicate()

    #
    # Prcocess clean up
    #
    def shutdown_handler(self, event):
        """Run homeassistant_stop event handler."""
        _LOGGER.debug("Running homeassistant_stop event handler: %s", event)
        self.hcidump.kill()
        self.hcidump.communicate()
        self.hcitool.kill()
        self.hcitool.communicate()
        self.tempf.close()

    #
    # Process message
    #
    def messages(self):
        """Get data from hcidump."""
        data = ""
        try:
            _LOGGER.debug("reading hcidump...")
            self.tempf.flush()
            self.tempf.seek(0)

            # read lines from STDOUT
            for line in self.tempf:
                try:
                    sline = line.decode()
                except AttributeError:
                    _LOGGER.debug("Error decoding line: %s", line)
                if sline.startswith("> "):
                    yield data
                    data = sline[2:].strip().replace(" ", "")
                elif sline.startswith("< "):
                    yield data
                    data = ""
                else:
                    data += sline.strip().replace(" ", "")
        except RuntimeError as error:
            _LOGGER.error("Error during reading of hcidump: %s", error)
            data = ""

        # reset STDOUT
        self.tempf.seek(0)
        self.tempf.truncate(0)
        yield data


#
# Configure for Home Assistant
#
def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the sensor platform."""
    _LOGGER.debug("Starting")
    scanner = BLEScanner()
    hass.bus.listen("homeassistant_stop", scanner.shutdown_handler)
    scanner.start(config)

    sensors_by_mac = {}

    ATTR = "_device_state_attributes"
    div_zero_hum_msg = "Division by zero while humidity averaging!"

    #
    # Discover Bluetooth LE devices.
    #
    def discover_ble_devices(config):
        """Discover Bluetooth LE devices."""
        _LOGGER.debug("Discovering Bluetooth LE devices")
        rounding = config[CONF_ROUNDING]
        decimals = config[CONF_DECIMALS]
        log_spikes = config[CONF_LOG_SPIKES]
        use_median = config[CONF_USE_MEDIAN]

        _LOGGER.debug("Stopping")
        scanner.stop()

        _LOGGER.debug("Analyzing")
        hum_m_data = {}
        temp_m_data = {}
        batt = {}  # battery
        lpacket = {}  # last packet number
        rssi = {}
        macs_names = {}  # map of macs to names given
        updated_sensors = {}

        for conf_dev in config[CONF_GOVEE_DEVICES]:
            conf_dev = dict(conf_dev)
            mac = conf_dev["mac"].translate({ord(i): None for i in ":"})
            macs_names[mac] = conf_dev.get("name", mac)

        _LOGGER.debug(macs_names)
        for msg in scanner.messages():
            data = parse_raw_message_gvh5075(msg)

            if not data:
                data = parse_raw_message_gvh5074(msg)

            # check for mac and temperature
            # assume humidity, batter and rssi are included
            if data and "mac" in data and data["mac"] in macs_names.keys():
                # Device MAC address
                mac = data["mac"]
                # Given name
                name = macs_names[mac]
                # Temperature in Celsius
                temp = data["temperature"]
                # humidity %
                humidity = data["humidity"]

                # ignore duplicated message
                packet = data["packet"]

                if mac in lpacket:
                    prev_packet = lpacket[mac]
                else:
                    prev_packet = None
                if prev_packet == packet:
                    _LOGGER.debug("DUPLICATE: %s, IGNORING!", data)
                else:
                    _LOGGER.debug("NEW DATA: %s", data)
                    lpacket[mac] = packet

                # Check if temperature within bounds
                if CONF_TMAX >= temp >= CONF_TMIN:
                    if mac not in temp_m_data:
                        temp_m_data[mac] = []
                    temp_m_data[mac].append(temp)
                    m_temp = temp_m_data[mac]
                elif log_spikes:
                    _LOGGER.error("Temperature spike: %s (%s)", temp, mac)

                # Check if humidity within bounds
                if CONF_HMAX >= humidity >= CONF_HMIN:
                    if mac not in hum_m_data:
                        hum_m_data[mac] = []
                    hum_m_data[mac].append(humidity)
                    m_hum = hum_m_data[mac]
                elif log_spikes:
                    _LOGGER.error("Humidity spike: %s (%s)", humidity, mac)

                # Battery percentage
                batt[mac] = int(data["battery"])

                # RSSI
                if mac not in rssi:
                    rssi[mac] = []
                rssi[mac].append(data["rssi"])

                # update home assistat
                if mac in sensors_by_mac:
                    sensors = sensors_by_mac[mac]
                else:
                    temp_sensor = TemperatureSensor(mac, name)
                    hum_sensor = HumiditySensor(mac, name)
                    sensors = [temp_sensor, hum_sensor]
                    sensors_by_mac[mac] = sensors
                    add_entities(sensors)

                for sensor in sensors:
                    getattr(sensor, ATTR)["last packet id"] = packet
                    getattr(sensor, ATTR)["rssi"] = round(sts.mean(rssi[mac]))
                    getattr(sensor, ATTR)[ATTR_BATTERY_LEVEL] = batt[mac]

                # averaging and states updating
                tempstate_mean = None
                humstate_mean = None
                tempstate_med = None
                humstate_med = None
                if use_median:
                    textattr = "last median of"
                else:
                    textattr = "last mean of"

                if m_temp:
                    try:
                        if rounding:
                            tempstate_med = round(sts.median(m_temp), decimals)  # noqa
                            tempstate_mean = round(sts.mean(m_temp), decimals)  # noqa
                        else:
                            tempstate_med = sts.median(m_temp)
                            tempstate_mean = sts.mean(m_temp)

                        if use_median:
                            setattr(sensors[0], "_state", tempstate_med)
                        else:
                            setattr(sensors[0], "_state", tempstate_mean)

                        getattr(sensors[0], ATTR)[textattr] = len(m_temp)
                        getattr(sensors[0], ATTR)["median"] = tempstate_med
                        getattr(sensors[0], ATTR)["mean"] = tempstate_mean
                        updated_sensors[mac + "_temp"] = sensors[0]
                    except AttributeError:
                        _LOGGER.info("Sensor %s not yet ready for update", mac)
                    except ZeroDivisionError:
                        _LOGGER.error(
                            "Division by zero while temperature averaging!"
                        )  # noqa
                        continue
                    except IndexError as error:
                        _LOGGER.error("%s. Index is 0!", error)
                        _LOGGER.error("sensors list size: %i", len(sensors))

                if m_hum:
                    try:
                        if rounding:
                            humstate_med = round(sts.median(m_hum), decimals)
                            humstate_mean = round(sts.mean(m_hum), decimals)
                        else:
                            humstate_med = sts.median(m_hum)
                            humstate_mean = sts.mean(m_hum)

                        if use_median:
                            setattr(sensors[1], "_state", humstate_med)
                        else:
                            setattr(sensors[1], "_state", humstate_mean)

                        getattr(sensors[1], ATTR)[textattr] = len(m_hum)
                        getattr(sensors[1], ATTR)["median"] = humstate_med
                        getattr(sensors[1], ATTR)["mean"] = humstate_mean
                        updated_sensors[mac + "_temp"] = sensors[1]
                    except AttributeError:
                        _LOGGER.info("Sensor %s not yet ready for update", mac)
                    except ZeroDivisionError:
                        _LOGGER.error(div_zero_hum_msg)
                        continue
                    except IndexError as error:
                        _LOGGER.error("%s. Index is 1!", error)
                        _LOGGER.error("sensors list size: %i", len(sensors))
        if len(updated_sensors) > 0:
            for k, sens in updated_sensors.items():
                _LOGGER.debug("updating sensor %s", k)
                sens.async_schedule_update_ha_state()
        scanner.start(config)
        return []

    #
    # Update BLE
    #
    def update_ble(now):
        """Lookup Bluetooth LE devices and update status."""
        period = config[CONF_PERIOD]
        _LOGGER.debug("update_ble called")

        try:
            discover_ble_devices(config)
        except RuntimeError as error:
            _LOGGER.error("Error during Bluetooth LE scan: %s", error)

        track_point_in_utc_time(
            hass, update_ble, dt_util.utcnow() + timedelta(seconds=period)
        )

    update_ble(dt_util.utcnow())


#
# HomeAssistant Temperature Sensor Class
#
class TemperatureSensor(Entity):
    """Representation of a sensor."""

    def __init__(self, mac, name):
        """Initialize the sensor."""
        self._state = None
        self._battery = None
        self._unique_id = "t_" + mac
        self._name = name
        self._device_state_attributes = {}

    @property
    def name(self):
        """Return the name of the sensor."""
        return "{} temp".format(self._name)

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return TEMP_CELSIUS

    @property
    def device_class(self):
        """Return the unit of measurement."""
        return DEVICE_CLASS_TEMPERATURE

    @property
    def should_poll(self):
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
    def force_update(self):
        """Force update."""
        return True


#
# HomeAssistant Humidity Sensor Class
#
class HumiditySensor(Entity):
    """Representation of a Sensor."""

    def __init__(self, mac, name):
        """Initialize the sensor."""
        self._state = None
        self._battery = None
        self._name = name
        self._unique_id = "h_" + mac
        self._device_state_attributes = {}

    @property
    def name(self):
        """Return the name of the sensor."""
        return "{} humidity".format(self._name)

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return "%"

    @property
    def device_class(self):
        """Return the unit of measurement."""
        return DEVICE_CLASS_HUMIDITY

    @property
    def should_poll(self):
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
    def force_update(self):
        """Force update."""
        return True
