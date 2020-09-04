{% if installed or pending_update %}

## 0.7
**Feature:**
  - **Added support for the Govee H5051** (Thank you[billprozac](https://github.com/billprozac))

**Fix:**
  - **Restart scanning each period to prevent device sleeping** (Thank you[billprozac](https://github.com/billprozac))

**Docs:**
  - **Added non-root user note** (Thank you[spinningmonkey](https://github.com/spinningmonkey))

**NOTE** FOR THOSE WHO ARE UPGRADING FROM V0.5 - a restart of the host device is suggested after upgrading this component.  The previous implementation may still have processes running or sockets open which.could cause unforeseeable issues.  I apologize for the inconvenience and future updates should go much smoother.  

{% endif %}


[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)

# Govee Temperature/Humidity BLE Home Assistant Component

A custom component for [Home Assistant](https://www.home-assistant.io) that listens for the advertisement message broadcast by Govee Bluetooth Thermometer/Hygrometers.

## Supported Devices
* Govee H5072
* [Govee H5074](https://www.amazon.com/Govee-Thermometer-Hygrometer-Bluetooth-Temperature/dp/B07R586J37)
* [Govee H5075](https://www.amazon.com/Govee-Temperature-Humidity-Notification-Monitor/dp/B07Y36FWTT/)

## Installation


**1. Install the custom component:**

- The easiest way is to install it with [HACS](https://hacs.xyz/). First install [HACS](https://hacs.xyz/) if you don't have it yet. After installation, the custom component can be found in the HACS store under integrations.

- Alternatively, you can install it manually. Just copy paste the content of the `sensor.goveetemp_bt_hci/custom_components` folder in your `config/custom_components` directory.
     As example, you will get the `sensor.py` file in the following path: `/config/custom_components/govee_ble_hci/sensor.py`.

**2. Stop and start Home Assistant:**

- Stop and start Home Assistant. Make sure you first stop Home Assistant and then start Home Assistant again.  Do this before step 5, as Home Assistant will otherwise complain that your configuration is not ok (as it still uses the build in `govee_ble_hci` integration), and won't restart when hitting restart in the server management menu.

**3. Add the platform to your configuration.yaml file (see [below](#configuration))**

**4. Restart Home Assistant:**

- A second restart may be required to load the configuration. Within a few minutes, the sensors should be added to your home-assistant automatically (at least one [period](#period) required).


### Configuration Variables

Specify the sensor platform `govee_ble_hci` and a list of devices with unique MAC address.

*NOTE*: device name is optional.  If not provided, deivces will be labeled using the MAC address
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



##### Additional configuration options
| Option | Type |Default Value | Description |  
| -- | -- | -- | -- |
| `rounding`| Boolean | `True` | Enable/disable rounding of the average of all measurements taken within the number seconds specified with 'period'. |  
| `decimals` | positive integer | `2`| Number of decimal places to round if rounding is enabled. |
| `period` | positive integer | `60` | The period in seconds during which the sensor readings are collected and transmitted to Home Assistant after averaging. The Govee devices broadcast roughly once per second so this limits amount of mostly duplicate data stored in  Home Assistant's database. |
| `log_spikes` |  Boolean | `False` | Puts information about each erroneous spike in the Home Assistant log. |
| `use_median` | Boolean  | `False` | Use median as sensor output instead of mean (helps with "spiky" sensors). Please note that both the median and the mean values in any case are present as the sensor state attributes. |
| `hci_device`| string | `hci0` | HCI device name used for scanning. |

## Credits
  This was originally based on/shamelessly copied from [custom-components/sensor.mitemp_bt](https://github.com/custom-components/sensor.mitemp_bt).  I want to thank [@tsymbaliuk](https://community.home-assistant.io/u/tsymbaliuk) and [@Magalex](https://community.home-assistant.io/u/Magalex) for providing a blueprint for developing my Home Assistant component.
