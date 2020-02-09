
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)

# Govee Temperature/Humidity BLE Home Assistant Component

A custom component for [Home Assistant](https://www.home-assistant.io) that listens for the advertisement message broadcast by Govee Bluetooth Thermometer/Hygrometers.  This version uses [deprecated bluez hcitool/hcidump](https://git.kernel.org/pub/scm/bluetooth/bluez.git/commit/?id=b1eb2c4cd057624312e0412f6c4be000f7fc3617) to scan.  This approach has its issues however [HASS](https://www.home-assistant.io/hassio) will required support to open the appropriate socket (AF_Bluetooth sockets on Alpine Linux using Python 3) before a better solution can be developed.

## Supported Devices
* [Govee H5074](https://www.amazon.com/Govee-Thermometer-Hygrometer-Bluetooth-Temperature/dp/B07R586J37)
* [Govee H5075](https://www.amazon.com/Govee-Temperature-Humidity-Notification-Monitor/dp/B07Y36FWTT/)

## Installation


**1. Install bluez-hcidump (not needed on HASSio):**

- The package `bluez-hcidump` needs to be installed first. `bluez-hcidump` reads raw the data coming from and going to your Bluetooth device. You can install it with the following command

     ```shell
     sudo apt-get install bluez-hcidump
     ```

**2. Allow hcitool and hcidump to run without root access (not needed on HASSio):**

- This custom component uses hcitool and hcidump commands to receive the data. Run the following commands to allow hcitool and hcidump to run without root access:

     ```shell
     sudo setcap 'cap_net_raw+ep' `readlink -f \`which hcidump\``
     sudo setcap 'cap_net_raw+ep' `readlink -f \`which hcitool\``
     ```

**3. Install the custom component:**

- The easiest way is to install it with [HACS](https://hacs.xyz/). First install [HACS](https://hacs.xyz/) if you don't have it yet. After installation, the custom component can be found in the HACS store under integrations.

- Alternatively, you can install it manually. Just copy paste the content of the `sensor.goveetemp_bt_hci/custom_components` folder in your `config/custom_components` directory.
     As example, you will get the `sensor.py` file in the following path: `/config/custom_components/govee_ble_hci/sensor.py`.

**4. Stop and start Home Assistant:**

- Stop and start Home Assistant. Make sure you first stop Home Assistant and then start Home Assistant again.  Do this before step 5, as Home Assistant will otherwise complain that your configuration is not ok (as it still uses the build in `govee_ble_hci` integration), and won't restart when hitting restart in the server management menu.

**5. Add the platform to your configuration.yaml file (see [below](#configuration))**

**6. Restart Home Assistant:**

- A second restart is required to load the configuration. After a few minutes, the sensors should be added to your home-assistant automatically (at least one [period](#period) required).


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
| `hcitool_active`| Boolean | `False`| In active mode hcitool sends scan requests, which is most often not required, but slightly increases the sensor battery consumption. 'Passive mode' means that you are not sending any request to the sensor but you are just reciving the advertisements sent by the BLE devices. This parameter is a subject for experiment. See the hcitool docs, --passive switch|
| `hci_device`| string | `hci0` | HCI device name used for scanning. |

## Credits
  This was heavily based on/shamelessly copied from [custom-components/sensor.mitemp_bt](https://github.com/custom-components/sensor.mitemp_bt).  I want to thank [@tsymbaliuk](https://community.home-assistant.io/u/tsymbaliuk) and [@Magalex](https://community.home-assistant.io/u/Magalex) for providing a blueprint for developing my Home Assistant component.
