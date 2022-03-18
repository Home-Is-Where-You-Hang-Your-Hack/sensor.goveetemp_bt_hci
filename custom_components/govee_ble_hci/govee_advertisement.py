"""Govee thermometer/hygrometer BLE advertisement parser."""
from struct import unpack_from
from typing import Optional
import logging

from bleson.core.hci.constants import (  # type: ignore
    GAP_FLAGS,
    GAP_NAME_COMPLETE,
    GAP_MFG_DATA,
)
from bleson.core.hci.type_converters import (  # type: ignore
    rssi_from_byte,
    hex_string,
)

###############################################################################

_LOGGER = logging.getLogger(__name__)


def twos_complement(n: int, w: int = 16) -> int:
    """Two's complement integer conversion."""
    # Adapted from: https://stackoverflow.com/a/33716541.
    if n & (1 << (w - 1)):
        n = n - (1 << w)
    return n


def decode_temps(packet_value: int) -> float:
    """Decode potential negative temperatures."""
    # https://github.com/Thrilleratplay/GoveeWatcher/issues/2

    if packet_value & 0x800000:
        return float((packet_value ^ 0x800000) / -10000)
    return float(packet_value / 10000)


#
# Reverse MAC octet order, return as a string
#
def reverse_mac(rmac: bytes) -> Optional[str]:
    """Change Little Endian order to Big Endian."""
    if len(rmac) != 6:
        return None
    macarr = [format(c, "02x") for c in list(reversed(rmac))]
    return (":".join(macarr)).upper()


class GoveeAdvertisement:
    """Govee thermometer/hygrometer BLE sensor advertisement parser class."""

    name: Optional[str]
    mfg_data: bytes
    temperature: Optional[float]
    humidity: Optional[float]
    battery: Optional[int]
    mac: Optional[str]
    rssi: Optional[int]
    _address: bytes

    def __init__(self, data: bytes):
        """Init."""
        try:
            self._address = data[3:9]
            self.mac = reverse_mac(self._address)
            self.rssi = rssi_from_byte(data[-1])
            self.raw_data = data[10:-1]
            self.flags = 6
            self.sensor_number = 0
            self.name = None
            self.packet = None
            self.temperature = None
            self.humidity = None
            self.battery = None
            self.model = None

            pos = 10
            while pos < len(data) - 1:
                _LOGGER.debug("POS={}".format(pos))
                length = data[pos]
                payload_offset = pos + 2
                gap_type = data[pos + 1]
                payload_end = payload_offset + length - 1
                payload = data[payload_offset:payload_end]
                _LOGGER.debug(
                    "Pos={} Type=0x{:02x} Len={} Payload={}".format(
                        pos, gap_type, length, hex_string(payload)
                    )
                )
                if GAP_FLAGS == gap_type:
                    self.flags = payload[0]
                    _LOGGER.debug("Flags={:02x}".format(self.flags))
                elif GAP_NAME_COMPLETE == gap_type:
                    self.name = payload.decode("ascii")
                    _LOGGER.debug("Complete Name={}".format(self.name))
                elif GAP_MFG_DATA == gap_type:
                    # unit8
                    self.mfg_data = payload
                    msg = "Manufacturer Data={}"
                    _LOGGER.debug(msg.format(str(self.mfg_data)))
                pos += length + 1

            if self.check_is_gvh5075_gvh5072():
                mfg_data_5075 = hex_string(self.mfg_data[3:6]).replace(" ", "")
                self.packet = int(mfg_data_5075, 16)
                self.temperature = decode_temps(self.packet)
                self.humidity = float((self.packet % 1000) / 10)
                self.battery = int(self.mfg_data[6])
                self.model = "Govee H5072/H5075"
            elif self.check_is_gvh5102():
                mfg_data_5075 = hex_string(self.mfg_data[4:7]).replace(" ", "")
                self.packet = int(mfg_data_5075, 16)
                self.temperature = decode_temps(self.packet)
                self.humidity = float((self.packet % 1000) / 10)
                self.battery = int(self.mfg_data[7])
                self.model = "Govee H5101/H5102"
            elif self.check_is_gvh5178():
                mfg_data_5075 = hex_string(self.mfg_data[5:8]).replace(" ", "")
                self.packet = int(mfg_data_5075, 16)
                self.temperature = decode_temps(self.packet)
                self.humidity = float((self.packet % 1000) / 10)
                self.battery = int(self.mfg_data[8])
                self.sensor_number = int(self.mfg_data[4])
                self.model = "Govee H5178"
            elif self.check_is_gvh5179():
                temp, hum, batt = unpack_from("<HHB", self.mfg_data, 6)
                self.packet = hex(temp)[2:] + hex(hum)[2:]
                # Negative temperature stored an two's complement
                self.temperature = float(twos_complement(temp) / 100.0)
                self.humidity = float(hum / 100.0)
                self.battery = int(batt)
                self.model = "Govee H5179"
            elif self.check_is_gvh5074() or self.check_is_gvh5051():
                temp, hum, batt = unpack_from("<HHB", self.mfg_data, 3)
                self.packet = hex(temp)[2:] + hex(hum)[2:]
                # Negative temperature stored an two's complement
                self.temperature = float(twos_complement(temp) / 100.0)
                self.humidity = float(hum / 100.0)
                self.battery = int(batt)
                self.model = "Govee H5074/H5051"
        except (ValueError, IndexError):
            pass

    def check_is_gvh5074(self) -> bool:
        """Check if mfg data is that of Govee H5074."""
        return self._mfg_data_check(9, 6)

    def check_is_gvh5102(self) -> bool:
        """Check if mfg data is that of Govee H5102."""
        return self._mfg_data_check(8, 5) and self._mfg_data_id_check("0100")

    def check_is_gvh5075_gvh5072(self) -> bool:
        """Check if mfg data is that of Govee H5075 or H5072."""
        return self._mfg_data_check(8, 5) and self._mfg_data_id_check("88ec")

    def check_is_gvh5051(self) -> bool:
        """Check if mfg data is that of Govee H5051."""
        return self._mfg_data_check(11, 6)

    def check_is_gvh5178(self) -> bool:
        """Check if mfg data is that of Govee H5178."""
        return self._mfg_data_check(11, 5)

    def check_is_gvh5179(self) -> bool:
        """Check if mfg data is that of Govee H5179."""
        return self._mfg_data_check(11, 6) and self._mfg_data_id_check("0188")

    def _mfg_data_check(self, data_length: int, flags: int) -> bool:
        """Check if mfg data is of a certain length with the correct flag."""
        return (
            hasattr(self, "mfg_data")
            and len(self.mfg_data) == data_length
            and self.flags == flags
        )

    def _mfg_data_id_check(self, id: str) -> bool:
        """Check if mfg data id is of a certain value."""
        return (
            hasattr(self, "mfg_data")
            and len(self.mfg_data) > 2
            and hex_string(self.mfg_data[0:2]).replace(" ", "") == id
        )
