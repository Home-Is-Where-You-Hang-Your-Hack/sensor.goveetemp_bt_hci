# Changelog
All notable changes to this project will be documented in this file.

## 0.7
**Feature:**
  - **Added support for the Govee H5051** (Thank you[billprozac](https://github.com/billprozac))

**Fix:**
  - **Restart scanning each period to prevent device sleeping** (Thank you[billprozac](https://github.com/billprozac))

**Docs:**
  - **Added non-root user note** (Thank you[spinningmonkey](https://github.com/spinningmonkey))

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
