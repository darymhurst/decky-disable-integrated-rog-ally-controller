import asyncio
import json
import subprocess
import os
import shutil
import glob
import decky

PROFILE_PATH = "/etc/inputplumber/devices.d/49-rog_ally_no_gamepad.yaml"
PROFILE_HIDDEN_PATH = "/etc/inputplumber/devices.d/49-rog_ally_no_gamepad.yaml.disabled"
SYSTEM_PROFILE_PATH = "/usr/share/inputplumber/devices/50-rog_ally.yaml"
SYSTEM_PROFILE_HIDDEN_PATH = "/usr/share/inputplumber/devices/50-rog_ally.yaml.disabled"
XPAD_PATH = "/sys/bus/usb/drivers/xpad"

STEAMOS_MANAGER_SERVICE_NAME = "steamos-manager"
INPUTPLUMBER_SERVICE_NAME = "inputplumber"

ASUS_VENDOR_ID="b05"
ASUS_N_KEY_PRODUCT_ID="1abe"
# Ally X (RC72LA), Xbox Ally (RC73YA), and Xbox Ally X (RC73XA).
# Confirmed on Ally X family: lsusb "0b05:1b4c ASUSTek ... N-KEY Device".
# Native joystick is HID on USB interface 5, e.g.:
#   Name: ASUS ROG Ally X Gamepad  Vendor: 0b05  Product: 1b4c  Bus: 0003
#   Sysfs: .../usb1/1-4/1-4:1.5/0003:0B05:1B4C.0006/input/input23
# Do not hard-code the usb1/1-4 path; topology changes across boots/docks.
ASUS_ALLY_X_PRODUCT_ID="1b4c"
ALLY_X_GAMEPAD_INTERFACES = {2, 5}
MICROSOFT_VENDOR_ID = "45e"
XBOX_PRODUCT_ID = "28e"

# Original Ally / Z1 Extreme uses an emulated Xbox 360 pad on xpad.
ORIGINAL_ALLY_BOARDS = {"RC71L"}
# Ally X family physical pad is ASUS HID 0b05:1b4c. The Microsoft X-Box 360
# pad (045e:028e) that also shows up is InputPlumber's *virtual* device
# (sysfs under /sys/devices/virtual/input), not USB xpad.
ALLY_X_FAMILY_BOARDS = {"RC72LA", "RC73XA", "RC73YA"}

# Physical Ally MCU IDs. Ignore these when looking for a 3rd-party pad.
BUILTIN_USB_IDS = {
    ("0b05", "1abe"),
    ("0b05", "1b4c"),
}
XBOX_360_ID = ("045e", "028e")
VALVE_VIRTUAL_ID = ("28de", "11ff")
VIRTUAL_INPUT_PREFIX = "/sys/devices/virtual/input/"
SETTINGS_FILE = "settings.json"
WATCH_INTERVAL_SEC = 2

PLUGIN_NAME = "decky-disable-integrated-rog-ally-controller"

PROFILE_CONTENT = f"""version: 1
kind: CompositeDevice
name: ASUS ROG Ally (No Gamepad)
single_source: false
matches:
  - dmi_data:
      board_name: RC71L
      sys_vendor: ASUSTeK COMPUTER INC.
  - dmi_data:
      board_name: RC72LA
      sys_vendor: ASUSTeK COMPUTER INC.
  - dmi_data:
      board_name: RC73XA
      sys_vendor: ASUSTeK COMPUTER INC.
  - dmi_data:
      board_name: RC73YA
      sys_vendor: ASUSTeK COMPUTER INC.
source_devices:
  - group: gamepad
    hidraw:
      vendor_id: 0x{ASUS_VENDOR_ID:0>4s}
      product_id: 0x{ASUS_N_KEY_PRODUCT_ID:0>4s}
      interface_num: 2
  - group: gamepad
    hidraw:
      vendor_id: 0x{ASUS_VENDOR_ID:0>4s}
      product_id: 0x{ASUS_ALLY_X_PRODUCT_ID:0>4s}
      interface_num: 2
  - group: gamepad
    hidraw:
      vendor_id: 0x{ASUS_VENDOR_ID:0>4s}
      product_id: 0x{ASUS_ALLY_X_PRODUCT_ID:0>4s}
      interface_num: 5
  - group: gamepad
    evdev:
      name: Microsoft X-Box 360 pad
      vendor_id: 0x{MICROSOFT_VENDOR_ID:0>4s}
      product_id: 0x{XBOX_PRODUCT_ID:0>4s}
      handler: event*
  - group: gamepad
    unique: false
    evdev:
      vendor_id: 0x{ASUS_VENDOR_ID:0>4s}
      product_id: 0x{ASUS_ALLY_X_PRODUCT_ID:0>4s}
      handler: event*
  - group: keyboard
    evdev:
      name: ASUS ROG Ally Config
      vendor_id: 0x{ASUS_VENDOR_ID:0>4s}
      product_id: 0x{ASUS_N_KEY_PRODUCT_ID:0>4s}
      handler: event*
  - group: keyboard
    unique: false
    evdev:
      name: Asus Keyboard
      vendor_id: 0x{ASUS_VENDOR_ID:0>4s}
      product_id: 0x{ASUS_N_KEY_PRODUCT_ID:0>4s}
      handler: event*
  - group: keyboard
    unique: false
    evdev:
      name: ROG Ally Keyboard
      vendor_id: 0x{ASUS_VENDOR_ID:0>4s}
      product_id: 0x{ASUS_N_KEY_PRODUCT_ID:0>4s}
      handler: event*
  - group: imu
    iio:
      name: bmi323-imu
      mount_matrix:
        x: [1, 0, 0]
        y: [0, -1, 0]
        z: [0, 0, -1]
  - group: led
    udev:
      sys_name: ally:rgb:joystick_rings
      subsystem: leds
options:
  auto_manage: true
  persist: true
target_devices:
  - keyboard
capability_map_id: aly1
"""

def log_info(s):
    decky.logger.info(f"{PLUGIN_NAME}: {s}")

def log_error(s):
    decky.logger.error(f"{PLUGIN_NAME}: {s}")

def run_cmd(args, timeout=10):
    env = os.environ.copy()
    env.pop("LD_LIBRARY_PATH", None)
    env.pop("LD_PRELOAD", None)
    return subprocess.run(args, capture_output=True, text=True, env=env, timeout=timeout)

def ensure_profile_exists(disabled):
    os.makedirs("/etc/inputplumber/devices.d", exist_ok=True)
    if not os.path.exists(PROFILE_HIDDEN_PATH) and not os.path.exists(PROFILE_PATH):
        with open(PROFILE_PATH if disabled else PROFILE_HIDDEN_PATH, "w") as f:
            f.write(PROFILE_CONTENT)
        log_info("created inputplumber profile")

def get_xpad_interface():
    for uevent in glob.glob(f"{XPAD_PATH}/*/uevent"):
        try:
            with open(uevent) as f:
                content = f.read()
            if f"PRODUCT={MICROSOFT_VENDOR_ID}/{XBOX_PRODUCT_ID}" in content or f"{MICROSOFT_VENDOR_ID:0>4s}" in content.lower():
                interface = uevent.replace("/uevent", "").split("/")[-1]
                log_info(f"get_xpad_interface={interface}")
                return interface
        except:
            log_error(f"Couldn't read {uevent}")
    return None

def _sys_read(path):
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        return None

def _sys_write(path, value):
    with open(path, "w") as f:
        f.write(value)

def _pad_id(value):
    return f"{value:0>4s}".lower()

def settings_path():
    return os.path.join(decky.DECKY_PLUGIN_SETTINGS_DIR, SETTINGS_FILE)

def load_prefer_external():
    path = settings_path()
    try:
        with open(path) as f:
            data = json.load(f)
        return bool(data.get("prefer_external", False))
    except FileNotFoundError:
        return False
    except Exception as e:
        log_error(f"failed to load settings: {e}")
        return False

def save_prefer_external(enabled: bool):
    os.makedirs(decky.DECKY_PLUGIN_SETTINGS_DIR, exist_ok=True)
    path = settings_path()
    try:
        with open(path, "w") as f:
            json.dump({"prefer_external": bool(enabled)}, f)
        log_info(f"saved prefer_external={enabled}")
    except Exception as e:
        log_error(f"failed to save settings: {e}")

def joystick_input_dir(js_dir):
    device = os.path.join(js_dir, "device")
    if os.path.isdir(device):
        return device
    try:
        return os.path.dirname(os.path.realpath(js_dir))
    except OSError:
        return js_dir

def joystick_ids(input_dir):
    vendor = _sys_read(os.path.join(input_dir, "id", "vendor"))
    product = _sys_read(os.path.join(input_dir, "id", "product"))
    if vendor is None or product is None:
        return None
    return (_pad_id(vendor), _pad_id(product))

def is_virtual_sysfs(path):
    try:
        return os.path.realpath(path).startswith(VIRTUAL_INPUT_PREFIX)
    except OSError:
        return False

def list_external_controllers():
    """Real 3rd-party gamepads, excluding Ally MCU and InputPlumber virtual pads."""
    board = get_board_name()
    original_ally = board in ORIGINAL_ALLY_BOARDS
    found = []
    original_ally_360 = []
    for js_dir in glob.glob("/sys/class/input/js*"):
        input_dir = joystick_input_dir(js_dir)
        ids = joystick_ids(input_dir)
        if not ids:
            continue
        name = _sys_read(os.path.join(input_dir, "name")) or os.path.basename(js_dir)
        virtual = is_virtual_sysfs(input_dir)
        if virtual or ids == VALVE_VIRTUAL_ID:
            continue
        if ids in BUILTIN_USB_IDS:
            continue
        entry = {
            "js": os.path.basename(js_dir),
            "name": name,
            "id": f"{ids[0]}:{ids[1]}",
            "virtual": virtual,
        }
        if ids == XBOX_360_ID and original_ally:
            original_ally_360.append(entry)
            continue
        found.append(entry)
    # Original Ally builtin is itself a 045e:028e xpad device. Extra copies
    # (8BitDo XInput, a real 360 pad, etc.) count as 3rd-party.
    if len(original_ally_360) > 1:
        found.extend(original_ally_360[1:])
    return found

def has_external_controller():
    return bool(list_external_controllers())

def iter_usb_device_dirs(vendor_id, product_id):
    vendor = _pad_id(vendor_id)
    product = _pad_id(product_id)
    for vendor_path in glob.glob("/sys/bus/usb/devices/*/idVendor"):
        if (_sys_read(vendor_path) or "").lower() != vendor:
            continue
        product_path = vendor_path.replace("idVendor", "idProduct")
        if (_sys_read(product_path) or "").lower() != product:
            continue
        yield os.path.dirname(vendor_path)

def usb_interface_dirs(device_dir, interface_nums):
    wanted = {int(n) for n in interface_nums}
    for iface_dir in glob.glob(f"{device_dir}/*:*"):
        raw = _sys_read(os.path.join(iface_dir, "bInterfaceNumber"))
        if raw is None:
            continue
        try:
            number = int(raw, 16)
        except ValueError:
            continue
        if number in wanted:
            yield iface_dir

def bound_usb_driver(iface_dir):
    link = os.path.join(iface_dir, "driver")
    if not os.path.islink(link):
        return None
    return os.path.basename(os.path.realpath(link))

def unbind_usb_interface(iface_dir):
    iface = os.path.basename(iface_dir)
    driver = bound_usb_driver(iface_dir)
    if not driver:
        log_info(f"{iface} already unbound")
        return
    try:
        _sys_write(f"/sys/bus/usb/drivers/{driver}/unbind", iface)
        log_info(f"unbound {iface} from {driver}")
    except Exception as e:
        log_error(f"failed to unbind {iface} from {driver}: {e}")

def bind_usb_interface(iface_dir, driver="usbhid"):
    iface = os.path.basename(iface_dir)
    current = bound_usb_driver(iface_dir)
    if current:
        log_info(f"{iface} already bound to {current}")
        return
    try:
        _sys_write(f"/sys/bus/usb/drivers/{driver}/bind", iface)
        log_info(f"bound {iface} to {driver}")
    except Exception as e:
        log_error(f"failed to bind {iface} to {driver}: {e}")

def get_board_name():
    return (_sys_read("/sys/class/dmi/id/board_name") or "").strip().upper()

def uses_xpad_gamepad(board):
    return not board or board in ORIGINAL_ALLY_BOARDS

def uses_ally_x_hid_gamepad(board):
    return not board or board in ALLY_X_FAMILY_BOARDS

def unbind_hid_under_usb_interface(iface_dir):
    for hid_dir in glob.glob(f"{iface_dir}/0003:*"):
        driver_link = os.path.join(hid_dir, "driver")
        if not os.path.islink(driver_link):
            continue
        driver_path = os.path.realpath(driver_link)
        hid_id = os.path.basename(hid_dir)
        try:
            _sys_write(os.path.join(driver_path, "unbind"), hid_id)
            log_info(f"unbound HID {hid_id} from {os.path.basename(driver_path)}")
        except Exception as e:
            log_error(f"failed to unbind HID {hid_id}: {e}")

def set_ally_x_hid_gamepad_bound(bound: bool):
    found = False
    for device_dir in iter_usb_device_dirs(ASUS_VENDOR_ID, ASUS_ALLY_X_PRODUCT_ID):
        found = True
        log_info(f"found Ally X / Xbox Ally HID {os.path.basename(device_dir)} (0b05:{ASUS_ALLY_X_PRODUCT_ID})")
        for iface_dir in usb_interface_dirs(device_dir, ALLY_X_GAMEPAD_INTERFACES):
            if bound:
                bind_usb_interface(iface_dir, "usbhid")
            else:
                unbind_hid_under_usb_interface(iface_dir)
                unbind_usb_interface(iface_dir)
    if not found:
        log_info("no Ally X / Xbox Ally HID gamepad (0b05:1b4c) found")

def is_service_masked(service_name, log=True):
    masked = run_cmd(["systemctl", "is-enabled", service_name]).stdout.strip() == "masked"
    if log:
        log_info(f"is_service_masked({service_name})={masked}")
    return masked

def is_steamos_manager_masked():
    return is_service_masked(STEAMOS_MANAGER_SERVICE_NAME)

def is_inputplumber_masked(log=True):
    return is_service_masked(INPUTPLUMBER_SERVICE_NAME, log=log)

def is_profile_disabled():
    disabled = os.path.exists(PROFILE_PATH) and not os.path.exists(PROFILE_HIDDEN_PATH)
    log_info(f"is_profile_disabled={disabled}")
    return disabled

def mask_service(service_name, disabled):
    if disabled:
        log_info(f"stopping {service_name}")
        try:
            run_cmd(["systemctl", "stop", service_name])
            log_info(f"{service_name} stopped")
        except Exception as e:
            log_error(f"stopping {service_name} failed: {e}")
        log_info(f"masking {service_name}")
        try:
            run_cmd(["systemctl", "mask", service_name])
            log_info(f"{service_name} masked")
        except Exception as e:
            log_error(f"masking {service_name} failed: {e}")
    else:
        log_info(f"unmasking {service_name}")
        try:
            run_cmd(["systemctl", "unmask", service_name])
            log_info(f"{service_name} unmasked")
        except Exception as e:
            log_error(f"unmasking {service_name} failed: {e}")
        log_info(f"starting {service_name}")
        try:
            run_cmd(["systemctl", "start", service_name])
            log_info(f"{service_name} started")
        except Exception as e:
            log_error(f"starting {service_name} failed: {e}")

def mask_steamos_manager(disabled):
    mask_service(STEAMOS_MANAGER_SERVICE_NAME, disabled)

def mask_inputplumber(disabled):
    mask_service(INPUTPLUMBER_SERVICE_NAME, disabled)

def set_profile_disabled(disabled: bool):
    if disabled:
        if not os.path.exists(PROFILE_PATH) and os.path.exists(PROFILE_HIDDEN_PATH):
            shutil.move(PROFILE_HIDDEN_PATH, PROFILE_PATH)
    else:
        if not os.path.exists(PROFILE_HIDDEN_PATH) and os.path.exists(PROFILE_PATH):
            shutil.move(PROFILE_PATH, PROFILE_HIDDEN_PATH)
    try:
        run_cmd(["systemctl", "restart", "inputplumber"])
        log_info("inputplumber restarted")
    except Exception as e:
        log_error(f"restarting inputplumber failed: {e}")

def set_system_profile_hidden(hide: bool):
    if hide:
        if os.path.exists(SYSTEM_PROFILE_PATH) and not os.path.exists(SYSTEM_PROFILE_HIDDEN_PATH):
            shutil.move(SYSTEM_PROFILE_PATH, SYSTEM_PROFILE_HIDDEN_PATH)
            log_info("hid system profile 50-rog_ally.yaml")
    else:
        if os.path.exists(SYSTEM_PROFILE_HIDDEN_PATH) and not os.path.exists(SYSTEM_PROFILE_PATH):
            shutil.move(SYSTEM_PROFILE_HIDDEN_PATH, SYSTEM_PROFILE_PATH)
            log_info("restored system profile 50-rog_ally.yaml")
    try:
        run_cmd(["systemctl", "restart", "inputplumber"])
        log_info("inputplumber restarted")
    except Exception as e:
        log_error(f"restarting inputplumber failed: {e}")

def is_xpad_device_bound():
    control_files = {"bind", "unbind", "module", "new_id", "remove_id", "uevent"}
    try:
        entries = os.listdir(XPAD_PATH)
    except FileNotFoundError:
        return False
    for entry in entries:
        if entry not in control_files:
            return True
    return False

def unbind_original_ally_xpad():
    interface = get_xpad_interface()
    if not interface:
        log_info("no xpad Xbox 360 pad (045e:028e) bound")
        return
    try:
        with open(f"{XPAD_PATH}/unbind", "w") as f:
            f.write(interface)
        log_info(f"unbound xpad interface {interface}")
    except Exception as e:
        log_error(f"failed to unbind xpad: {e}")

def bind_original_ally_xpad():
    try:
        for path in glob.glob("/sys/bus/usb/devices/*/idVendor"):
            vendor = _sys_read(path)
            if vendor != f"{MICROSOFT_VENDOR_ID:0>4s}":
                continue
            product = _sys_read(path.replace("idVendor", "idProduct"))
            if product != f"{XBOX_PRODUCT_ID:0>4s}":
                continue
            device_dir = path.replace("/idVendor", "")
            for interface in glob.glob(f"{device_dir}/*:1.0"):
                iface = interface.split("/")[-1]
                try:
                    with open(f"{XPAD_PATH}/bind", "w") as f:
                        f.write(iface)
                    log_info(f"bound xpad interface {iface}")
                except Exception as e:
                    log_error(f"failed to bind xpad: {e}")
    except Exception as e:
        log_error(f"error rebinding xpad: {e}")

def set_integrated_disabled(disabled: bool):
    board = get_board_name()
    log_info(f"set_integrated_disabled({disabled}) board_name={board or 'unknown'}")
    if disabled:
        # Stop inputplumber first so it drops hidraw/evdev grabs before unbind.
        mask_inputplumber(True)
        if uses_xpad_gamepad(board):
            unbind_original_ally_xpad()
        if uses_ally_x_hid_gamepad(board):
            set_ally_x_hid_gamepad_bound(False)
    else:
        if uses_xpad_gamepad(board):
            bind_original_ally_xpad()
        if uses_ally_x_hid_gamepad(board):
            set_ally_x_hid_gamepad_bound(True)
        mask_inputplumber(False)
    log_info(f"integrated controller {'disabled' if disabled else 'enabled'}")

def desired_builtin_disabled(prefer_external: bool):
    if not prefer_external:
        return False
    return has_external_controller()

def apply_prefer_external(prefer_external: bool, force=False):
    want_disabled = desired_builtin_disabled(prefer_external)
    currently_disabled = is_inputplumber_masked(log=False)
    if not force and want_disabled == currently_disabled:
        return currently_disabled
    log_info(f"applying builtin disabled={want_disabled} prefer_external={prefer_external}")
    set_integrated_disabled(want_disabled)
    return want_disabled

class Plugin:
    def __init__(self):
        self.prefer_external = False
        self._watch_task = None

    async def _main(self):
        board = get_board_name() or "unknown"
        log_info(f"board_name={board}")
        self.prefer_external = load_prefer_external()
        if not self.prefer_external and is_inputplumber_masked(log=False):
            # Pre-auto-mode installs remembered disable via masked inputplumber.
            self.prefer_external = True
            save_prefer_external(True)
            log_info("migrated masked inputplumber to prefer_external=True")
        apply_prefer_external(self.prefer_external, force=True)
        self._watch_task = asyncio.create_task(self._watch_external_controllers())
        log_info(f"starting prefer_external={self.prefer_external} builtin_disabled={is_inputplumber_masked(log=False)}")
        log_info("plugin started")

    async def _unload(self):
        if self._watch_task:
            self._watch_task.cancel()
            try:
                await self._watch_task
            except asyncio.CancelledError:
                pass
            self._watch_task = None

    async def _watch_external_controllers(self):
        last_external = None
        while True:
            try:
                await asyncio.sleep(WATCH_INTERVAL_SEC)
                if not self.prefer_external:
                    last_external = None
                    continue
                controllers = list_external_controllers()
                external = bool(controllers)
                if external == last_external:
                    continue
                last_external = external
                if external:
                    names = "; ".join(f"{c['name']} {c['id']}" for c in controllers)
                    log_info(f"3rd-party controller connected: {names}")
                else:
                    log_info("3rd-party controller disconnected")
                apply_prefer_external(True)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                log_error(f"watch loop failed: {e}")

    async def is_prefer_external(self):
        return bool(self.prefer_external)

    async def is_integrated_controller_disabled(self):
        return is_inputplumber_masked(log=False)

    async def set_prefer_external(self, enabled: bool):
        self.prefer_external = bool(enabled)
        save_prefer_external(self.prefer_external)
        apply_prefer_external(self.prefer_external, force=True)
        return self.prefer_external

    async def disable_integrated(self):
        return await self.set_prefer_external(True)

    async def enable_integrated(self):
        return await self.set_prefer_external(False)
    