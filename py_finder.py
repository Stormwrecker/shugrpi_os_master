import shutil
import subprocess
import os

def check_python(path: str, required_version: str | None) -> bool:
    """Return True if 'path' exists and (if required_version) reports that version."""
    if not path or not os.path.exists(path):
        return False
    try:
        out = subprocess.check_output(
            [path, "-c", "import sys;print(f'{sys.version_info.major}.{sys.version_info.minor}')"],
            stderr=subprocess.STDOUT, text=True, timeout=5).strip()
        if required_version is None:
            return True
        return out == required_version
    except Exception:
        return False

def find_python_executable(is_shugr_pi, logger, version=None):
    # Normalize requested version
    req_ver = None
    if version:
        version = str(version).strip()
        parts = version.split(".")
        if len(parts) >= 2:
            req_ver = f"{int(parts[0])}.{int(parts[1])}"
        else:
            # Single number given, treat as major only (not ideal but try)
            req_ver = f"{int(parts[0])}.0"

    # 1) Check pyenv first (if available, works on Windows/Linux)
    pyenv_cmd = shutil.which("pyenv")
    if pyenv_cmd:
        try:
            # List installed pyenv versions
            installed_versions = subprocess.check_output([pyenv_cmd, "versions", "--bare"], text=True, timeout=10).strip().split("\n")
            for v in installed_versions:
                if req_ver and v.startswith(req_ver):
                    exe_path = subprocess.check_output([pyenv_cmd, "which", f"python{req_ver}"], text=True, timeout=None).strip()
                    if check_python(exe_path, req_ver):
                        logger.info(f"Found Python{req_ver} via pyenv at '{exe_path}'")
                        return exe_path
                elif not req_ver and v:  # Any version if none specified
                    exe_path = subprocess.check_output([pyenv_cmd, "which", f"python{req_ver}"], text=True, timeout=None).strip()
                    if check_python(exe_path, None):
                        logger.info(f"Found Python via pyenv at '{exe_path}'")
                        return exe_path

            # If not installed, try to install via pyenv (requires internet; cross-platform)
            if req_ver:
                logger.info(f"Python{req_ver} not found in pyenv; attempting installation...")
                subprocess.run([pyenv_cmd, "install", req_ver], check=True, timeout=None)
                exe_path = subprocess.check_output([pyenv_cmd, "which", f"python{req_ver}"], text=True, timeout=5).strip()
                if check_python(exe_path, req_ver):
                    logger.info(f"Installed and found Python{req_ver} via pyenv at '{exe_path}'")
                    return exe_path
        except subprocess.CalledProcessError as e:
            logger.warning(f"Pyenv operation failed: {e}")
        except subprocess.TimeoutExpired:
            logger.error("Pyenv installation timed out")

    # 2) If py launcher exists (Windows/Linux), try it with the requested version
    if shutil.which("py"):
        if req_ver:
            try:
                out = subprocess.check_output(["py", f"-{req_ver}", "-c", "import sys;print(sys.executable)"],
                                              stderr=subprocess.DEVNULL, text=True, timeout=5).strip()
                if out and check_python(out, req_ver):
                    logger.info(f"Found '{out}' using py launcher")
                    return out
            except Exception:
                logger.warning(f"Unable to find Python{req_ver} using py launcher")
        else:
            try:
                out = subprocess.check_output(["py", "-3", "-c", "import sys;print(sys.executable)"],
                                              stderr=subprocess.DEVNULL, text=True, timeout=5).strip()
                if out and check_python(out, None):
                    logger.info(f"Found '{out}' using py launcher")
                    return out
            except Exception:
                logger.warning("Unable to find Python using py launcher")

    # 3) Candidate executable names (prefer pythonX.Y when version requested; cross-platform)
    candidates = []
    if req_ver:
        candidates.append(f"python{req_ver}")
    # Fallback names (add .exe for Windows)
    exe_suffix = ".exe" if os.name == "nt" else ""  # Windows check
    candidates.extend([f"python3{exe_suffix}", f"python{exe_suffix}"])

    for name in candidates:
        exe = shutil.which(name)
        if exe and check_python(exe, req_ver):
            logger.info(f"Found '{exe}' in candidates")
            return exe

    logger.warning(f"Unable to find Python{req_ver} in candidates")

    # 4) Check common absolute paths for each host type (cross-platform)
    common_paths = []
    if is_shugr_pi:  # ARM64 Linux (Raspberry Pi)
        if req_ver:
            common_paths.extend([f"/usr/bin/python{req_ver}", f"/usr/local/bin/python{req_ver}"])
        common_paths.extend(["/usr/bin/python3", "/usr/bin/python"])
    else:
        # Windows common locations
        if req_ver:
            vershort = req_ver.replace(".", "")
            common_paths.extend([f"C:\\Python{vershort}\\python.exe",
                                 f"C:\\Program Files\\Python{vershort}\\python.exe",
                                 f"C:\\Program Files (x86)\\Python{vershort}\\python.exe"])
        common_paths.extend([r"C:\Python39\python.exe", r"C:\Program Files\Python39\python.exe"])
        # Linux/Unix fallbacks (non-Pi)
        if req_ver:
            common_paths.extend([f"/usr/bin/python{req_ver}", f"/usr/local/bin/python{req_ver}"])
        common_paths.extend(["/usr/bin/python3", "/usr/bin/python"])

    for p in common_paths:
        if check_python(p, req_ver):
            logger.info(f"Found '{p}' in common paths")
            return p

    logger.warning(f"Unable to find Python{req_ver} in common paths")

    # 5) As a last resort, iterate over PATH for python executables (cross-platform)
    path_env = os.environ.get("PATH", "")
    for dirpath in path_env.split(os.pathsep):
        for candidate in (f"python{exe_suffix}", f"python3{exe_suffix}"):
            full = os.path.join(dirpath, candidate)
            if check_python(full, req_ver):
                logger.info(f"Found '{full}' in PATH")
                return full

    # Not found
    logger.warning(f"Unable to find executable for Python{version}")
    return None