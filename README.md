# Decky Disable Integrated ROG Ally Controller

A **Decky Loader plugin** for ROG Ally handhelds that allows disabling the integrated controller.  
This is useful when an external controller conflicts with the built-in controls or is not detected correctly in certain games.

---

## Features

- Prefer an external / 3rd-party controller: built-in pad stays on until a real extra controller is connected, then the built-in pad is disabled
- Re-enables the built-in pad when the extra controller is disconnected
- Prevents input conflicts with USB and Bluetooth controllers
- Lightweight plugin with minimal dependencies
- Works seamlessly with Decky Loader

---

## Installation

1. In Desktop mode download the latest release zip from [here](https://github.com/darymhurst/decky-disable-integrated-rog-ally-controller/raw/refs/heads/main/decky-disable-integrated-rog-ally-controller.zip).
2. Manually upload the zip file from within Decky after enabling developer mode.

## Notes

Turn **Prefer external controller** on. With no extra pad connected, the built-in controller stays enabled. Plug in a USB or Bluetooth controller and the built-in pad is disabled; unplug it and the built-in pad comes back.

Steam / InputPlumber virtual devices (for example `Microsoft X-Box 360 pad` under `/sys/devices/virtual/input`, or Valve `28de:11ff`) are not treated as 3rd-party controllers.

When the integrated controller is disabled the Armoury Crate button will be disabled which means you will need to use the alternative Power+A combination to access the Decky sidebar and then turn the plugin off (or unplug the extra pad).
Most external controllers e.g. Xbox usually have their middle Xbox button mapped to mimic the Armoury Crate hardware button. On Xbox Ally / Xbox Ally X, Armoury Crate is the top-left face button (a dedicated Xbox/guide button is separate).

When a 3rd-party controller is present and prefer-external is on, the plugin currently:

* Masks the `inputplumber` service
* Unbinds the built-in gamepad (xpad `045e:028e` on original Ally, ASUS HID `0b05:1b4c` on Ally X / Xbox Ally / Xbox Ally X)

It does **not** stop `steamos-manager`. Battery charge limit, TDP, BIOS/dock updates, WiFi, and similar SteamOS manager features stay available.

Older versions of this plugin *did* mask `steamos-manager`. That leftover helper is still in [main.py](main.py) but is unused. Masking `inputplumber` can still affect extra-button / gyro plumbing; use at your own risk. The plugin does not delete config files.

## Disclaimer

Tested on ROG Ally Extreme Z1 (RC71L) with an external 8BitDo Ultimate 2C. Ally X / Xbox Ally / Xbox Ally X expose the built-in pad as USB HID `0b05:1b4c` (`N-KEY Device`; joystick is typically interface 5, `ASUS ROG Ally X Gamepad`). The `Microsoft X-Box 360 pad` (`045e:028e`) on those machines is InputPlumber's virtual device under `/sys/devices/virtual/input`, not a real USB xpad device. The plugin is not hard-coded to a specific external controller.

## Appearance

![Within Decky](plugin1.jpg)

![Disable/enable](plugin2.jpg)
