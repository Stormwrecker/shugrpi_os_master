"""Linux API for the SHUGRPi Operating System"""

import subprocess

# Linux API
class Linux:
    def __init__(self, is_shugrpi, logger):
        self.is_shugrpi = is_shugrpi
        self.logger = logger

    """set time"""
    def set_time(self, time):
        code = self._call(["sudo", "timedatectl", "set-time", time])
        if code == 0:
            self.logger.info(f"Set time to `{time}`")
        elif code > 0:
            self.logger.error("Failed to set the time")
        elif code == -1:
            self.logger.warning("Cannot set time on non-SHUGRPi device")
        return code

    """network commands"""
    def connect_to_wifi(self, ssid, psk_key):
        self.logger.info(f"Attempting a connection to '{ssid}'...")
        con_name = "shugrpi-wifi"
        make_profile_proc = self._run(["nmcli", "con", "add", "type", "wifi", "ifname"
                                       "con-name", con_name, "ssid", ssid])
        set_security_proc = self._run(["nmcli", "con", "mod", con_name, "wifi-sec.key-mgmt", "wpa-psk"])
        set_psk_proc = self._run(["nmcli", "con", "mod", con_name, "wifi-sec.key-psk", psk_key])
        all_procs = [make_profile_proc, set_security_proc, set_psk_proc]
        if 1 not in all_procs and -1 not in all_procs:
            self.logger.info(f"Connected successfully to '{ssid}' using the password '{len(psk_key) * '*'}'")
            return 0
        else:
            self.logger.error(f"Failed to connect to '{ssid}' using the password '{len(psk_key) * '*'}'")
            return 1

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
        self.logger.info("Powering off device...")
        self._run(["sudo", "poweroff"])

    def reboot(self):
        self.logger.info("Rebooting OS...")
        self._run(["pkill", "Xorg"])

    """runners"""
    def _call(self, proc):
        if self.is_shugrpi:
            return subprocess.call(proc) == 0
        return -1

    def _run(self, proc):
        if self.is_shugrpi:
            return subprocess.run(proc, check=True, capture_output=True, text=True)
        return -1


CATALOG_PATH = "/opt/catalog-repo"

def git(*args):
    subprocess.run(["git", *args], cwd=CATALOG_PATH, check=True)

def update_catalog():
    git("fetch", "origin")
    git("reset", "--hard", "origin/main")

__all__ = ["Linux"]
