"""Constants for the Govee BLE HCI monitor sensor integration."""

DOMAIN = "govee_ble_hci"

# Configuration options
CONF_DECIMALS = "decimals"
CONF_DEVICE_MAC = "mac"
CONF_DEVICE_NAME = "name"
CONF_GOVEE_DEVICES = "govee_devices"
CONF_HCI_DEVICE = "hci_device"
CONF_LOG_SPIKES = "log_spikes"
CONF_PERIOD = "period"
CONF_ROUNDING = "rounding"
CONF_TEMP_RANGE_MAX_CELSIUS = "temp_range_max_celsius"
CONF_TEMP_RANGE_MIN_CELSIUS = "temp_range_min_celsius"
CONF_USE_MEDIAN = "use_median"


# Default values for configuration options
DEFAULT_DECIMALS = 2
DEFAULT_HCI_DEVICE = "hci0"
DEFAULT_LOG_SPIKES = False
DEFAULT_PERIOD = 60
DEFAULT_ROUNDING = True
DEFAULT_TEMP_RANGE_MAX = 60.0
DEFAULT_TEMP_RANGE_MIN = -20.0
DEFAULT_USE_MEDIAN = False

"""Fixed constants."""

# Sensor measurement limits to exclude erroneous spikes from the results
CONF_HMIN = 0.0
CONF_HMAX = 99.9
