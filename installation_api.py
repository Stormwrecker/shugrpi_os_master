"""Game-installation API for the SHUGRPi OS"""

import subprocess
import threading
import shutil
import sys
import os


# check if specified python executable is valid
def check_python(path, required_version=None):
    # if path is None or path does not exist
    if not path or not os.path.exists(path):
        return False

    # if required version is not specified
    if required_version is None:
        return True

    try:
        # get version of current python and return match
        out = subprocess.check_output([path, "-c", "import sys;print(f'{sys.version_info.major}.{sys.version_info.minor}')"],
            stderr=subprocess.STDOUT, text=True, timeout=5).strip()
        return out == required_version

    except subprocess.SubprocessError:
        return False


# subprocess helper
def run(p, proc_list):
    process = subprocess.Popen(p, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    proc_list.append(process)
    process.wait()
    return process.returncode


# installation object
class Installation:
    def __init__(self, game, logger, internet_connection):
        self.game = game
        self.logger = logger
        self.internet_connection = internet_connection

        self.name = game.name
        self.path = game.root_path
        self.venv = os.path.join(self.path, ".venv")
        self.requirements = game.requirements

        self.python = None
        self.python_version = self.game.python_version or ""

        self.ready = False
        self.complete = False

        # the conditions required to be True before installation
        conditions = [not os.path.exists(self.venv),
                      self.requirements is not None]
        if False not in conditions:
            self.ready = True
            self.logger.info(f"Attempting to install `{self.name}`...")

        self.processes = []
        self.process_thread = threading.Thread(name=f"`{self.name}` Installation", target=self._handle_processes, daemon=True)
        self.process_lock = threading.Lock()

    def _get_python(self, version=None):
        req_ver = None

        # clean up version string
        if version:
            version = str(version).strip()
            parts = version.split(".")
            if len(parts) >= 2:
                req_ver = f"{int(parts[0])}.{int(parts[1])}"
            self.logger.info(f"Python{req_ver} required to run `{self.name}`; Searching for Python{req_ver}...")
        else:
            req_ver = ""

        # get python via pyenv
        pyenv_cmd = shutil.which("pyenv")
        if pyenv_cmd:
            try:
                # run through already installed version of python
                installed_versions = subprocess.check_output([pyenv_cmd, "versions", "--bare"], text=True, timeout=10).strip().split("\n")
                for v in installed_versions:

                    # check if python version is already installed on pyenv
                    if req_ver and v.startswith(req_ver):
                        python_path = subprocess.check_output([pyenv_cmd, "which", f"python{req_ver}"], text=True, timeout=None).strip()
                        if check_python(python_path, req_ver):
                            self.logger.debug(f"Found Python{req_ver} via pyenv at `{python_path}`")
                            return python_path

                    # get any python version if no version is specified
                    elif not req_ver and v:
                        python_path = subprocess.check_output([pyenv_cmd, "which", "python"], text=True, timeout=None).strip()
                        if check_python(python_path, None):
                            self.logger.debug(f"Found Python via pyenv at '{python_path}'")
                            return python_path

                self.logger.warning(f"Python{req_ver} not found")

            # handle exceptions
            except subprocess.CalledProcessError as e:
                self.logger.warning(f"Pyenv operation failed: {e}")
                self.ready = False
            except subprocess.TimeoutExpired:
                self.logger.error("Pyenv installation timed out")
                self.ready = False

            # if correct version does not exist, install it
            try:
                self.logger.info(f"Installing Python{req_ver} via pyenv...")
                subprocess.run([pyenv_cmd, "install", req_ver], text=True, timeout=None)
                python_path = subprocess.check_output([pyenv_cmd, "which", f"python{req_ver}"], text=True,
                                                      timeout=None).strip()
                if check_python(python_path, req_ver):
                    self.logger.info(f"Found Python{req_ver} via pyenv at `{python_path}`")
                    return python_path

            # handle exceptions
            except subprocess.CalledProcessError as e:
                self.logger.warning(f"Pyenv operation failed: {e}")
                self.ready = False

        else:
            if version:
                self.logger.error(f"Pyenv is required to install `{self.name}`")
                self.ready = False
                return None
            else:
                python_path = sys.executable
                self.logger.info(f"Using `{python_path}` for installation...")
                return python_path

    def _create_venv(self, python):
        self.logger.info(f"Creating venv in `{self.venv}`...")
        try:
            proc = [python, "-m", "venv", self.venv]
            if run(proc, self.processes):
                raise subprocess.SubprocessError
        except subprocess.SubprocessError:
            self.ready = False
            self.logger.error(f"Failed to create venv in `{self.venv}`")

    def _install_dependencies(self, python):
        if self.internet_connection:
            self.logger.info(f"Installing dependencies for `{self.name}`...")
            try:
                proc = [python, "-m", "pip", "install", "-r", self.requirements]
                if run(proc, self.processes):
                    raise subprocess.SubprocessError
            except subprocess.SubprocessError:
                self.logger.error(f"Failed to install dependencies for `{self.name}`")
                self.ready = False
        else:
            self.logger.error(f"Internet connection required to install dependencies for `{self.name}`")
            self.ready = False

    def _handle_processes(self):
        self.python = self._get_python(self.python_version)
        if self.ready and not self.complete:
            self._create_venv(self.python)
        if self.ready and self.requirements and not self.complete:
            self._install_dependencies(self.python)

        if not self.complete:
            if not self.ready:
                self._bailout()
            else:
                self.complete = True
                self.logger.info(f"Successfully installed `{self.name}`")

    def _bailout(self):
        self.logger.info(f"Aborting `{self.name}` installation...")
        self.complete = True

        # kill dependencies process if existing
        if len(self.processes) == 2:
            if self.processes[-1].returncode is None:
                self.processes[-1].terminate()

        # stop process handling
        self.process_thread.join()

        # remove venv folder
        self._remove_venv()
        self.logger.error(f"Failed to install `{self.name}`")

    def _remove_venv(self):
        if os.path.exists(self.venv):
            shutil.rmtree(self.venv)
            self.logger.info(f"Removed venv in `{self.venv}`")

    def start(self):
        self.process_thread.start()


__all__ = ["Installation"]
