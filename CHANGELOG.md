# Changelog
All notable changes to this project will be documented in this file.

## 0.10.0
**Feat:**
  - **Minimum and maximum temperature configurable.**  Base on [SteveOnorato/moat_temp_hum_ble](https://github.com/SteveOnorato/moat_temp_hum_ble/).  Thank you @SteveOnorato
  - **Devices now related.** Thank you @natekspencer
**Fix:**
  - **Catch Bluetooth adapter error and provide useful information.**
**Chore:**
  - **Removed "CONF_HCITOOL_ACTIVE"**

**BREAKING CHANGE** - With the removal of `CONF_HCITOOL_ACTIVE` if `hcitool_active` is still in your config, Home Assistant will not start.  Please remove this deprecated flag.

## 0.9.2
**Fix:**
  - **Update bleson package to version 0.18, fixes non BLE spec device name errors**

## 0.9.1
**Fix:**
  - **Add version to manifest.json**

## 0.9.0
**Feature:**
  - **Added support for the Govee H5179** (Thank you [skilau](https://github.com/skilau))

## 0.8.0
**Fix:**
  - **Decode negative temperature for Govee H5072, Govee H5075, Govee H5051 and Govee H5052**
  - **Catch remaining StatisticsError instances in sensor**

## 0.7.1
**Fix:**
  - **Update bleson package, fixes constant RSSI value**

## 0.7
**Feature:**
  - **Added support for the Govee H5051** (Thank you [billprozac](https://github.com/billprozac))
  - **Added support for the Govee H5102** (Thank you [billprozac](https://github.com/billprozac))

**Fix:**
  - **Restart scanning each period to prevent device sleeping** (Thank you [billprozac](https://github.com/billprozac))

**Docs:**
  - **Added non-root user note** (Thank you [spinningmonkey](https://github.com/spinningmonkey))

## 0.6
**Fix:**
  - **Removed hcitool dependencies.**
  - **Restructure component for easier maintenance.**
  - **Deprecated `hcitool_active` configuration option.**

## 0.5
**Feature:**
  - **Added support for the Govee H5072**

## 0.4
**Fixed:**

 - **Correct two's complement conversion**
 - **Initialize m_temp and m_hum to prevent UnboundLocalError error**

## 0.3
**Fixed:**

 - **Prevent crashing on reading of corrupt broadcast**

## 0.2

**Fixed:**

 - **Fix limit updates to period interval** (Thank you [sfjes](github.com/sfjes))

## 0.1
  - **Initial Release**
