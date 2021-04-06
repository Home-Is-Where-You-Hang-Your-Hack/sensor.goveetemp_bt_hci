"""Constants for the Govee BLE HCI monitor sensor integration."""

# Configuration options
CONF_ROUNDING = "rounding"
CONF_DECIMALS = "decimals"
CONF_PERIOD = "period"
CONF_LOG_SPIKES = "log_spikes"
CONF_USE_MEDIAN = "use_median"
CONF_HCITOOL_ACTIVE = "hcitool_active"
CONF_HCI_DEVICE = "hci_device"
CONF_GOVEE_DEVICES = "govee_devices"
CONF_DEVICE_MAC = "mac"
CONF_DEVICE_NAME = "name"


# Default values for configuration options
DEFAULT_ROUNDING = True
DEFAULT_DECIMALS = 2
DEFAULT_PERIOD = 60
DEFAULT_LOG_SPIKES = False
DEFAULT_USE_MEDIAN = False
DEFAULT_HCITOOL_ACTIVE = False
DEFAULT_HCI_DEVICE = "hci0"

"""Fixed constants."""

# Sensor measurement limits to exclude erroneous spikes from the results
CONF_TMIN = -30.0
CONF_TMAX = 60.0
CONF_HMIN = 0.0
CONF_HMAX = 99.9
