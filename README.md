# Govee Temperature/Humidity BLE Home Assistant Component

A custom component for [Home Assistant](https://www.home-assistant.io) that listens for the advertisement message broadcast by Govee Bluetooth Thermometer/Hygrometers.

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg?style=plastic)](https://github.com/custom-components/hacs)
![hassfest_badge](https://github.com/Home-Is-Where-You-Hang-Your-Hack/sensor.goveetemp_bt_hci/actions/workflows/hassfest.yaml/badge.svg)

## Supported Devices
* Govee H5051 (BLE only)
* Govee H5072
* [Govee H5074](https://www.amazon.com/Govee-Thermometer-Hygrometer-Bluetooth-Temperature/dp/B07R586J37)
* [Govee H5075](https://www.amazon.com/Govee-Temperature-Humidity-Notification-Monitor/dp/B07Y36FWTT/)
* Govee H5101
* [Govee H5102](https://www.amazon.com/gp/product/B087313N8F/)
* [Govee H5177](https://www.amazon.com/gp/product/B08C9VYMHY)
* [Govee H5179](https://www.amazon.com/gp/product/B0872ZWV8X) (BLE only)

## Installation


**1. Install the custom component:**

- The easiest way is to install it with [HACS](https://hacs.xyz/). First install [HACS](https://hacs.xyz/) if you don't have it yet. After installation, the custom component can be found in the HACS store under integrations.

- Alternatively, you can install it manually. Just copy paste the content of the `sensor.goveetemp_bt_hci/custom_components` folder in your `config/custom_components` directory.
     As example, you will get the `sensor.py` file in the following path: `/config/custom_components/govee_ble_hci/sensor.py`.

*NOTE:* the following instructions about setting device permissions are an edge case for a very specific set up.  (If you do not understand it, do not worry about).

- If running Home Assistant without root access the [Bleson](https://github.com/TheCellule/python-bleson) Python library used for accessing bluetooth requires the following permissions applied to the Python 3 binary. If using a virtual environment for HA, this binary will be in the virtual environment path.

     *NOTE*: Replace "path" with the path to the Python3 binary (example: /srv/homeassistant/bin/python3)
     ```
     sudo setcap cap_net_raw,cap_net_admin+eip $(eval readlink -f path)
     ```
**2. Stop and start Home Assistant:**

- Stop and start Home Assistant. Make sure you first stop Home Assistant and then start Home Assistant again.  Do this before step 5, as Home Assistant will otherwise complain that your configuration is not valid (as it still uses the build in `govee_ble_hci` integration), and won't restart when hitting restart in the server management menu.

**3. Add the platform to your configuration.yaml file (see [below](#configuration))**

**4. Restart Home Assistant:**

- A second restart may be required to load the configuration. Within a few minutes, the sensors should be added to your home-assistant automatically (at least two [period](#period) may be required.  If the [period](#period) is set to a time greater than two minutes, at least four [period](#period) may be required).

**5. If the entities are still not displaying data, a restart of the host device may be required.**

### Troubleshooting and help

Any questions or support should be asked on [this component's Home Assistant community post](https://community.home-assistant.io/t/govee-ble-thermometer-hygrometer-sensor/166696).

### Configuration Variables

Specify the sensor platform `govee_ble_hci` and a list of devices with unique MAC address.

*NOTE*: device name is optional.  If not provided, devices will be labeled using the MAC address
```
sensor:
  - platform: govee_ble_hci
    govee_devices:
      - mac: "A4:C1:38:A1:A2:A3"
        name: Bedroom
      - mac: "A4:C1:38:B1:B2:B3"
      - mac: "A4:C1:38:C1:C2:C3"
        name: Kitchen
```



##### Additional component configuration options

| Option | Type |Default Value | Description |  
| -- | -- | -- | -- |
| `rounding`| Boolean | `True` | Enable/disable rounding of the average of all measurements taken within the number seconds specified with 'period'. |  
| `decimals` | positive integer | `2`| Number of decimal places to round if rounding is enabled. NOTE: the raw Celsius is rounded and setting `decimals: 0` will still result in decimal values returned for Fahrenheit as well as temperatures being off by up to 1 degree `F`.|
| `period` | positive integer | `60` | The period in seconds during which the sensor readings are collected and transmitted to Home Assistant after averaging. The Govee devices broadcast roughly once per second so this limits amount of mostly duplicate data stored in  Home Assistant's database. |
| `log_spikes` |  Boolean | `False` | Puts information about each erroneous spike in the Home Assistant log. |
| `use_median` | Boolean  | `False` | Use median as sensor output instead of mean (helps with "spiky" sensors). Please note that both the median and the mean values in any case are present as the sensor state attributes. |
| `hci_device`| string | `hci0` | HCI device name used for scanning. |

Example with all defaults:
```
sensor:
  - platform: govee_ble_hci
    rounding: True
    decimals: 2
    period: 60
    log_spikes: False
    hci_device: hci0
    govee_devices:
      - mac: "A4:C1:38:A1:A2:A3"
        name: Bedroom
      - mac: "A4:C1:38:B1:B2:B3"
      - mac: "A4:C1:38:C1:C2:C3"
        name: Kitchen
```

## Credits
  This was originally based on/shamelessly copied from [custom-components/sensor.mitemp_bt](https://github.com/custom-components/sensor.mitemp_bt).  I want to thank [@tsymbaliuk](https://community.home-assistant.io/u/tsymbaliuk) and [@Magalex](https://community.home-assistant.io/u/Magalex) for providing a blueprint for developing my Home Assistant component.
