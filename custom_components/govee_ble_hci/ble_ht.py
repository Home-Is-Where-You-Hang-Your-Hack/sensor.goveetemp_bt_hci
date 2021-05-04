"""Bluetooth LE Humidity/Temperature data classes."""
from typing import List, Optional, Union
import statistics as sts
import logging

from .const import (
    DEFAULT_TEMP_RANGE_MIN,
    DEFAULT_TEMP_RANGE_MAX,
    CONF_HMIN,
    CONF_HMAX,
)

_LOGGER = logging.getLogger(__name__)


class BLE_HT_packet:
    """Bluetooth LE Humidity/Temperature packet data."""

    temperature: float
    humidity: float
    packet: str


class BLE_HT_data:
    """Bluetooth LE Humidity/Temperature data."""

    _desc: Optional[str]
    _mac: str
    _rssi: List[int]
    _battery: Optional[int]
    _packet_data: List[BLE_HT_packet]
    _decimal_places: Optional[int]
    _log_spikes: bool
    _min_temp: float
    _max_temp: float

    def __init__(self, mac: str, description: Optional[str]) -> None:
        """Init."""
        self._mac = mac
        self._desc = description
        self._log_spikes = False
        self._min_temp = DEFAULT_TEMP_RANGE_MIN
        self._max_temp = DEFAULT_TEMP_RANGE_MAX
        self.reset()

    @property
    def data_size(self) -> int:
        """Packet data length."""
        return len(self._packet_data)

    @property
    def last_packet(self) -> Optional[str]:
        """Return MAC address."""
        if len(self._packet_data) == 0:
            return None
        return self._packet_data[-1].packet

    @property
    def mac(self) -> str:
        """Return MAC address."""
        return self._mac

    @property
    def battery(self) -> Optional[int]:
        """Return battery remaining value."""
        return self._battery

    @battery.setter
    def battery(self, value: Optional[int]) -> None:
        """Set battery remaining value."""
        if isinstance(value, int):
            self._battery = value

    @property
    def decimal_places(self) -> Optional[int]:
        """Set number of decimal places for rounding value."""
        return self._decimal_places

    @decimal_places.setter
    def decimal_places(self, value: int) -> None:
        """Set number of decimal places for rounding value."""
        if value >= 0:
            self._decimal_places = value

    @property
    def description(self) -> Optional[str]:
        """Return device description or MAC address."""
        return self._desc if hasattr(self, "_desc") else self._mac

    @description.setter
    def description(self, value: str) -> None:
        """Set device description."""
        if isinstance(value, str):
            self._desc = value

    @property
    def log_spikes(self) -> bool:
        """Set number of decimal places for rounding value."""
        return self._log_spikes

    @log_spikes.setter
    def log_spikes(self, value: bool) -> None:
        """Set number of decimal places for rounding value."""
        self._log_spikes = value

    @property
    def rssi(self) -> Optional[int]:
        """Return RSSI value."""
        try:
            return round(sts.mean(self._rssi))
        except (AssertionError, sts.StatisticsError):
            return None

    @rssi.setter
    def rssi(self, value: Optional[int]) -> None:
        """Set RSSI value."""
        if isinstance(value, int) and value < 0:
            self._rssi.append(value)

    @property
    def maximum_temperature(self) -> float:
        """Get upper bound of temperature."""
        return self._max_temp

    @maximum_temperature.setter
    def maximum_temperature(self, value: float) -> None:
        """Set upper bound of temperature."""
        self._max_temp = value

    @property
    def minimum_temperature(self) -> float:
        """Get lower bound of temperature."""
        return self._min_temp

    @minimum_temperature.setter
    def minimum_temperature(self, value: float) -> None:
        """Set lower bound of temperature."""
        self._min_temp = value

    @property
    def mean_temperature(self) -> Union[float, None]:
        """Mean temperature of values collected."""
        try:
            avg = sts.mean(self._map_packet_data_attrs("temperature"))
            if hasattr(self, "_decimal_places"):
                return round(avg, self._decimal_places)
            return avg
        except (AssertionError, sts.StatisticsError):
            return None

    @property
    def median_temperature(self) -> Union[float, None]:
        """Median temperature of values collected."""
        try:
            avg = sts.median(self._map_packet_data_attrs("temperature"))
            if hasattr(self, "_decimal_places"):
                return round(avg, self._decimal_places)
            return avg
        except (AssertionError, sts.StatisticsError):
            return None

    @property
    def mean_humidity(self) -> Union[float, None]:
        """Mean humidity of values collected."""
        try:
            avg = sts.mean(self._map_packet_data_attrs("humidity"))
            if hasattr(self, "_decimal_places"):
                return round(avg, self._decimal_places)
            return avg
        except (AssertionError, sts.StatisticsError):
            return None

    @property
    def median_humidity(self) -> Union[float, None]:
        """Median humidity of values collected."""
        try:
            avg = sts.median(self._map_packet_data_attrs("humidity"))
            if hasattr(self, "_decimal_places"):
                return round(avg, self._decimal_places)
            return avg
        except (AssertionError, sts.StatisticsError):
            return None

    def update(
        self,
        temperature: Optional[float],
        humidity: Optional[float],
        packet: Optional[Union[int, str]],
    ) -> None:
        """Update packet data."""
        new_packet = BLE_HT_packet()

        # Check if temperature within bounds
        if temperature is not None and self._max_temp >= temperature >= self._min_temp:
            new_packet.temperature = temperature
        elif self._log_spikes:
            err = "Temperature spike: {} ({})".format(temperature, self._mac)
            _LOGGER.error(err)

        # Check if humidity within bounds
        if humidity is not None and CONF_HMAX >= humidity >= CONF_HMIN:
            new_packet.humidity = humidity
        elif self._log_spikes:
            err = "Humidity spike: {} ({})".format(humidity, self._mac)
            _LOGGER.error(err)

        new_packet.packet = str(packet)
        self._packet_data.append(new_packet)

    def reset(self) -> None:
        """Reset default values."""
        self._battery = None
        self._rssi = []
        self._packet_data = []

    def _map_packet_data_attrs(self, attr: str) -> List[float]:
        """Map defined values from _packet.data."""
        mapped_vals = []
        for datum in self._packet_data:
            if hasattr(datum, attr):
                mapped_vals.append(float(getattr(datum, attr)))
        return mapped_vals
