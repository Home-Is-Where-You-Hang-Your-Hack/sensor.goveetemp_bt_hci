"""Govee thermometer/hygrometer BLE advertisement parser."""
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


#
# Reverse MAC octet order, return as a string
#
def reverse_mac(rmac: bytes) -> Optional[str]:
    """Change LE order to BE."""
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
            self.name = None
            self.packet = None
            self.temperature = None
            self.humidity = None
            self.battery = None

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
                    self.name = str(payload)
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
                self.temperature = float(self.packet / 10000)
                self.humidity = float((self.packet % 1000) / 10)
                self.battery = int(self.mfg_data[6])
            elif self.check_is_gvh5074():
                mfg_data_5074 = hex_string(self.mfg_data[3:7]).replace(" ", "")
                temp_lsb = mfg_data_5074[2:4] + mfg_data_5074[0:2]
                hum_lsb = mfg_data_5074[6:8] + mfg_data_5074[4:6]
                self.packet = temp_lsb + hum_lsb
                self.humidity = float(int(hum_lsb, 16) / 100)
                # Negative temperature stored an two's complement
                temp_lsb_int = int(temp_lsb, 16)
                self.temperature = float(twos_complement(temp_lsb_int) / 100)
                self.battery = int(self.mfg_data[7])
        except (ValueError, IndexError):
            pass

    def check_is_gvh5074(self) -> bool:
        """Check if mfg data is that of Govee H5074."""
        return self._mfg_data_check(9, 6)

    def check_is_gvh5075_gvh5072(self) -> bool:
        """Check if mfg data is that of Govee H5075 or H5072."""
        return self._mfg_data_check(8, 5)

    def _mfg_data_check(self, data_length: int, flags: int) -> bool:
        """Check if mfg data is of a certain length with the correct flag."""
        return (
            hasattr(self, "mfg_data")
            and len(self.mfg_data) == data_length
            and self.flags == flags
        )
