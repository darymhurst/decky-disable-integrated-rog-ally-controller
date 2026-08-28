# AGENTS.md

Decky Loader plugin that disables the ROG Ally (and similar) integrated controller so an external controller is the only pad games see. Runs as **root** (`plugin.json` `flags: ["root"]`).

## Commands

```sh
pnpm install          # lockfile is pnpm-lock.yaml
pnpm build            # rollup frontend → dist/index.js
pnpm watch            # rebuild on frontend changes
./package.sh          # build + zip plugin for Decky install
./package.sh -release # bump package.json patch version, then package
```

There is no test suite (`pnpm test` is a stub that exits 1). There is no lint script; TypeScript is type-checked as part of `pnpm build`.

The release zip is `decky-disable-integrated-rog-ally-controller.zip` at the repo root. Users install it by enabling Decky developer mode and uploading the zip. `package.sh -release` only increments the **patch** in `package.json` (does not commit or tag).

`package.sh` copies only `dist/index.js`, `main.py`, `plugin.json`, and `package.json` into the zip. It does not include `backend/`, `defaults/`, `LICENSE`, or `README.md`.

## Architecture

Frontend (`src/index.tsx`) is a Decky React plugin: one toggle, **Prefer external controller**. It talks to Python over `@decky/api` `callable()`:

| Frontend | Python (`Plugin` in `main.py`) |
|---|---|
| `isPreferExternal` | `is_prefer_external` |
| `setPreferExternal` | `set_prefer_external` |
| `isIntegratedControllerDisabled` | `is_integrated_controller_disabled` (actual bind state) |

Toggle **on** means: keep the built-in pad unless a real 3rd-party `js*` device is present, then disable it; re-enable when that pad is gone. Preference is stored in `DECKY_PLUGIN_SETTINGS_DIR/settings.json`. A 2s watch loop applies hotplug. `enable_integrated` / `disable_integrated` map to prefer-external off / on.

3rd-party detection skips Ally MCU IDs (`0b05:1abe`, `0b05:1b4c`), Valve virtual (`28de:11ff`), anything under `/sys/devices/virtual/input`, and on original Ally (`RC71L`) the emulated xpad `045e:028e`.

Python backend (`main.py`) is the real work. Current enable/disable path (`set_integrated_disabled`) is board-aware (`/sys/class/dmi/id/board_name`):

1. **mask `inputplumber`** — disable stops and `systemctl mask`s `inputplumber` *before* unbind so hidraw grabs are released; enable unmasks and starts it after re-bind.
2. **Original Ally (`RC71L`)** — xpad bind/unbind of the emulated Xbox 360 pad (`045e:028e`). Disable writes the interface to `/sys/bus/usb/drivers/xpad/unbind`; enable finds that USB device and binds `*:1.0`.
3. **Ally X family (`RC72LA`, `RC73XA` Xbox Ally X, `RC73YA` Xbox Ally)** — unbind/bind USB interfaces 2 and 5 of ASUS HID `0b05:1b4c` (`N-KEY Device`; joystick is typically `…/1-4:1.5/0003:0B05:1B4C.*`). Do not unbind xpad: the `045e:028e` `Microsoft X-Box 360 pad` on these boards is InputPlumber's virtual device (`/sys/devices/virtual/input`), and a real USB 360 pad may be an external controller.

If board name cannot be read, both paths run.

On plugin start (`_main`), `prefer_external` is loaded from settings. If it is missing but `inputplumber` is already masked (old always-disable installs), prefer-external is turned on. Then the watch loop keeps builtin state in sync with 3rd-party presence.

`run_cmd` strips `LD_LIBRARY_PATH` / `LD_PRELOAD` before calling `systemctl` or other subprocesses (Steam runtime pollution).

`main.py` also contains unused inputplumber-profile and `steamos-manager` helpers (`PROFILE_CONTENT`, `ensure_profile_exists`, `set_profile_disabled`, `mask_steamos_manager`, hiding `/usr/share/inputplumber/devices/50-rog_ally.yaml`). They are **not** on the current toggle path.

## Hardware / UX constraints

- Original Ally (`RC71L`) uses xpad `045e:028e` plus N-key `0b05:1abe`. Ally X (`RC72LA`), Xbox Ally X (`RC73XA`), and Xbox Ally (`RC73YA`) use ASUS HID `0b05:1b4c` interfaces 2 and 5 (`lsusb` shows `N-KEY Device`; `js` shows `ASUS ROG Ally X Gamepad` on interface 5).
- Tested on ROG Ally Extreme Z1 with an 8BitDo Ultimate 2C. Ally X family IDs confirmed from a live `lsusb` + `/sys/class/input` dump; toggle path not yet verified on that hardware.
- While the integrated controller is off, the Armoury Crate button does not work. Open Decky with **Power+A**, then re-enable in the plugin. Many external pads map their guide button to Armoury Crate.
- Masking `inputplumber` can affect extra-button / gyro plumbing. Current toggle does **not** mask `steamos-manager`, so battery charge limit and related SteamOS manager features should keep working. An unused `mask_steamos_manager` helper remains in `main.py`. Plugin is use-at-your-own-risk; it should not delete config, only bind/unbind and mask/unmask.

## Template leftovers

Scaffolded from [decky-plugin-template](https://github.com/SteamDeckHomebrew/decky-plugin-template). `package.json` name/repo metadata still say `decky-plugin-template`. `backend/` (Docker + `hello` C binary) and `defaults/` are unused by this plugin. `decky.pyi` is the Decky Python API stub.

Do not run as a non-root plugin; sysfs bind/unbind and `systemctl mask` need the `root` flag.
