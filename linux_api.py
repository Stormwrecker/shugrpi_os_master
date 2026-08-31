"""Linux API for the SHUGRPi Operating System"""

import subprocess
import sys
import re

# Linux API
class Linux:
    def __init__(self, is_shugrpi, logger):
        self.is_shugrpi = is_shugrpi
        self.logger = logger

    def set_notification(self, notification):
        self.notification = notification

    """set time"""
    def set_time(self, time):
        code, error, _ = self._run(["sudo", "timedatectl", "set-time", time])
        if code == 0:
            self.logger.info(f"Set time to {time}")
            self._notify(f"Set time to {time}")
        elif code > 0:
            self.logger.error(f"Failed to set the time: {error}")
            self._notify(f"Failed to set the time: {error}", True)
        elif code == -1:
            self.logger.warning("Cannot set time on non-SHUGRPi device")
            self._notify("Cannot set time on non-SHUGRPi device", True)
        return code

    """network commands"""
    def scan_networks(self):
        networks = []

        if self.is_shugrpi:
            result = subprocess.run(
                ["nmcli", "-t", "-f", "IN-USE,SSID,SIGNAL,SECURITY", "dev", "wifi"],
                capture_output=True, text=True
            )

            for line in result.stdout.strip().splitlines():
                if not line:
                    continue

                fields = re.split(r"(?<!\\):", line)
                fields = [f.replace("\\:", ":") for f in fields]

                if len(fields) < 4:
                    continue

                in_use_flag, ssid, signal, security = fields[0], fields[1], fields[2], fields[3]

                if not ssid:
                    continue

                try:
                    strength = int(signal)
                except ValueError:
                    strength = None

                networks.append({
                    "ssid": ssid,
                    "strength": strength,
                    "in_use": (in_use_flag.strip() == "*"),
                    "security": security if security else "Open"
                })

        return networks

    def connect_wifi(self, ssid, psk_key):
        if not len(psk_key):
            self._notify("`Password` field cannot be empty")
            return -1

        if not self.is_shugrpi:
            self.logger.warning(f"Non-SHUGRPi device cannot connect to `{ssid}`")
            self._notify(f"Non-SHUGRPi device cannot connect to `{ssid}`")
            return -1

        self.logger.info(f"Attempting a connection to `{ssid}`...")

        iface = "wlan0"
        if iface is None:
            self._notify("No Wi-Fi adapter detected")
            return 1

        con_name = "shugrpi-wifi"
        masked = len(psk_key) * "*"

        self._run(["nmcli", "con", "delete", con_name])

        steps = [
            ["nmcli", "con", "add", "type", "wifi", "ifname", iface, "con-name", con_name, "ssid", ssid],
            ["nmcli", "con", "modify", con_name, "wifi-sec.key-mgmt", "wpa-psk"],
            ["nmcli", "con", "modify", con_name, "wifi-sec.psk", psk_key],
            ["nmcli", "con", "up", con_name],
        ]

        for step in steps:
            code, err, _ = self._run(step)
            if code != 0:
                self.logger.error(
                    f"Failed to connect to `{ssid}` using the password '{masked}': {(err or 'unknown error').strip()}")
                self._notify(f"Failed to connect to `{ssid}`")
                self._run(["nmcli", "con", "delete", con_name])
                return 1

        self.logger.info(f"Connected successfully to `{ssid}` using the password '{masked}'")
        self._notify(f"Connected successfully to `{ssid}`")
        return 0

    def is_wifi_connected(self):
        if not self.is_shugrpi:
            return -1
        code, _, out = self._run(["nmcli", "-t", "-f", "NAME", "con", "show", "--active"])
        if code != 0:
            return False
        return "shugrpi-wifi" in out.strip().splitlines()

    def disconnect_wifi(self, forget=False):
        if not self.is_shugrpi:
            return -1

        con_name = "shugrpi-wifi"

        code, err, _ = self._run(["nmcli", "con", "down", con_name])
        if code != 0:
            self.logger.error(f"Failed to disconnect wifi: {(err or 'unknown error').strip()}")
            self._notify("Failed to disconnect Wi-Fi")
            return 1

        if forget:
            del_code, del_err, _ = self._run(["nmcli", "con", "delete", con_name])
            if del_code != 0:
                self.logger.warning(f"Disconnected but failed to forget saved network: {(del_err or '').strip()}")

        msg = "Disconnected from Wi-Fi" + (" and forgot the network" if forget else "")
        self.logger.info(msg)
        self._notify(msg)
        return 0

    def reload_wifi(self, ssid, psk_key):
        if not self.is_wifi_connected():
            con_name = "shugrpi-wifi"
            code, err, _ = self._run(["nmcli", "con", "up", con_name])
            if code != 0:
                self.logger.error(f"Failed to connect wifi: {(err or 'unknown error').strip()}")
                return 1
        else:
            self.logger.info("Wi-Fi already connected")

    def ping(self):
        code = self._call(["ping", "-c", "2", "8.8.8.8"])
        return code

    """git commands"""
    def git_clone(self, repo="https://github.com/Stormwrecker/shugrpi_os_master.git"):
        return self._call(["git", "clone", repo])

    def git_fetch(self):
        return self._call(["git", "fetch", "origin"])

    def git_change_branch(self, branch="origin/main"):
        if branch in ["origin/main", "catalog/games"]:
            return self._call(["git", "reset", "--hard", branch])
        else:
            return -1

    def git_partial_clone(self, repo):
        clone_proc = self._call(["git", "clone", "--filter=blob:none", "--no-checkout", repo])
        chdir_proc = self._call(["cd", repo])
        if clone_proc == 0 and chdir_proc == 0:
            return 0
        elif 1 in [clone_proc, chdir_proc]:
            return 1
        else:
            return -1

    def git_sparse_init(self):
        return self._call(["git", "sparse", "-checkout", "init", "--cone"])

    def git_partial_pull(self):
        return self._call(["git", "sparse-checkout", "set", "catalog/games", "catalog/titles.json"])

    def git_check_updates(self):
        return self._run(["git", "diff", "--quiet", "main", "origin/main"])

    def git_pull(self):
        return self._call(["git", "pull"])

    """power commands"""
    def power_off(self):
        self._run(["sudo", "poweroff"])

    def reboot(self):
        if self.is_shugrpi:
            self.logger.info("Rebooting OS...")
        self._run(["pkill", "Xorg"])

    """runners"""
    def _call(self, proc):
        if self.is_shugrpi:
            return subprocess.call(proc, stdout=subprocess.DEVNULL) == 0
        return -1

    def _run(self, proc):
        if self.is_shugrpi:
            done_proc = subprocess.run(proc, capture_output=True, text=True)
            return done_proc.returncode, done_proc.stderr, done_proc.stdout
        return -1, None

    """notify"""
    def _notify(self, msg, error=False):
        self.notification.reset(msg, error)


"""unused code"""

CATALOG_PATH = "/opt/catalog-repo"

def git(*args):
    subprocess.run(["git", *args], cwd=CATALOG_PATH, check=True)

def update_catalog():
    git("fetch", "origin")
    git("reset", "--hard", "origin/main")

__all__ = ["Linux"]
