import subprocess
import os
import shutil
import glob
import decky

PROFILE_DISABLED_PATH = "/etc/inputplumber/devices.d/49-rog_ally_no_gamepad.yaml"
PROFILE_ENABLED_PATH = "/etc/inputplumber/devices.d/49-rog_ally_no_gamepad.yaml.disabled"
XPAD_PATH = "/sys/bus/usb/drivers/xpad"

ASUS_VENDOR_ID="b05"
ASUS_N_KEY_PRODUCT_ID="1abe"
MICROSOFT_VENDOR_ID = "45e"
XBOX_PRODUCT_ID = "28e"

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
source_devices:
  - group: gamepad
    ignore: true
    hidraw:
      vendor_id: 0x{ASUS_VENDOR_ID:0>4s}
      product_id: 0x{ASUS_N_KEY_PRODUCT_ID:0>4s}
      interface_num: 2
  - group: gamepad
    ignore: true
    evdev:
      name: Microsoft X-Box 360 pad
      vendor_id: 0x{MICROSOFT_VENDOR_ID:0>4s}
      product_id: 0x{XBOX_PRODUCT_ID:0>4s}
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

def run_cmd(args):
    env = os.environ.copy()
    env.pop("LD_LIBRARY_PATH", None)
    env.pop("LD_PRELOAD", None)
    return subprocess.run(args, capture_output=True, text=True, env=env)

def ensure_profile_exists(disabled):
    os.makedirs("/etc/inputplumber/devices.d", exist_ok=True)
    if not os.path.exists(PROFILE_ENABLED_PATH) and not os.path.exists(PROFILE_DISABLED_PATH):
        with open(PROFILE_DISABLED_PATH if disabled else PROFILE_ENABLED_PATH, "w") as f:
            f.write(PROFILE_CONTENT)
        log_info("created inputplumber profile")

def get_xpad_interface():
    for uevent in glob.glob("/sys/bus/usb/drivers/xpad/*/uevent"):
        with open(uevent) as f:
            content = f.read()
        if f"PRODUCT={MICROSOFT_VENDOR_ID}/{XBOX_PRODUCT_ID}" in content or f"{MICROSOFT_VENDOR_ID:0>4s}" in content.lower():
            interface = uevent.replace("/uevent", "").split("/")[-1]
            return interface
    return None

def log_info(s):
    decky.logger.info(f"{PLUGIN_NAME}: {s}")

def log_error(s):
    decky.logger.error(f"{PLUGIN_NAME}: {s}")

def is_steamos_manager_masked():
    return run_cmd(["systemctl", "is-enabled", "steamos-manager"]).stdout.strip() == "masked"

def is_profile_disabled():
    return os.path.exists(PROFILE_DISABLED_PATH) and not os.path.exists(PROFILE_ENABLED_PATH)

def mask_steamos_manager(disabled):
    if disabled:
        run_cmd(["systemctl", "stop", "steamos-manager"])
        run_cmd(["systemctl", "mask", "steamos-manager"])
    else:
        run_cmd(["systemctl", "unmask", "steamos-manager"])
        run_cmd(["systemctl", "start", "steamos-manager"])
    run_cmd(["systemctl", "restart", "inputplumber"])

def set_profile_disabled(disabled: bool):
    if disabled:
        if not os.path.exists(PROFILE_DISABLED_PATH) and os.path.exists(PROFILE_ENABLED_PATH):
            shutil.move(PROFILE_ENABLED_PATH, PROFILE_DISABLED_PATH)
    else:
        if not os.path.exists(PROFILE_ENABLED_PATH) and os.path.exists(PROFILE_DISABLED_PATH):
            shutil.move(PROFILE_DISABLED_PATH, PROFILE_ENABLED_PATH)

def set_integrated_disabled(disabled: bool):
    if disabled:
        interface = get_xpad_interface()
        if interface:
            try:
                with open(f"{XPAD_PATH}/unbind", "w") as f:
                    f.write(interface)
                log_info(f"unbound xpad interface {interface}")
            except Exception as e:
                log_error(f"failed to unbind xpad: {e}")
    else:
        try:
            for path in glob.glob("/sys/bus/usb/devices/*/idVendor"):
                with open(path) as f:
                    vendor = f.read().strip()
                if vendor == f"{MICROSOFT_VENDOR_ID:0>4s}":
                    prod_path = path.replace("idVendor", "idProduct")
                    with open(prod_path) as f:
                        product = f.read().strip()
                    if product == f"{XBOX_PRODUCT_ID:0>4s}":
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
    set_profile_disabled(disabled)
    mask_steamos_manager(disabled)
    log_info(f"integrated controller {'disabled' if disabled else 'enabled'}")

class Plugin:
    async def _main(self):
        previously_disabled = is_steamos_manager_masked() or is_profile_disabled()
        if previously_disabled:
            log_info("detected previously disabled integrated controller, re-applying on startup")
        ensure_profile_exists(previously_disabled)
        set_integrated_disabled(previously_disabled)
        log_info(f"starting with integrated controller {'disabled' if previously_disabled else 'enabled'}")
        log_info("plugin started")

    async def is_integrated_controller_disabled(self):
        return is_steamos_manager_masked() or is_profile_disabled()

    async def disable_integrated(self):
        set_integrated_disabled(True)
        return True

    async def enable_integrated(self):
        set_integrated_disabled(False)
        return True
