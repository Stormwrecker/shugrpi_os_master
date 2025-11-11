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
            # single number given, treat as major only (not ideal but try)
            req_ver = f"{int(parts[0])}.0"

    # 1) If py launcher exists on Windows, try it with the requested version
    if shutil.which("py"):
        if req_ver:
            try:
                out = subprocess.check_output(["py", f"-{req_ver}", "-c", "import sys;print(sys.executable)"],
                                              stderr=subprocess.DEVNULL, text=True, timeout=5).strip()
                if out and check_python(out, req_ver):
                    logger.info(f"Found {out} using py launcher")
                    return out
            except Exception:
                logger.warning(f"Unable to find {req_ver} using py launcher")

        else:
            try:
                out = subprocess.check_output(["py", "-3", "-c", "import sys;print(sys.executable)"],
                                              stderr=subprocess.DEVNULL, text=True, timeout=5).strip()
                if out and check_python(out, None):
                    logger.info(f"Found {out} using py launcher")
                    return out
            except Exception:
                logger.warning(f"Unable to find {req_ver} using py launcher")

    # 2) Candidate executable names (prefer pythonX.Y when version requested)
    candidates = []
    if req_ver:
        candidates.append(f"python{req_ver}")
    # fallback names
    candidates.extend(["python3", "python"])

    for name in candidates:
        exe = shutil.which(name)
        if exe and check_python(exe, req_ver):
            logger.info(f"Found {exe} in candidates")
            return exe

    logger.warning(f"Unable to find {req_ver} in candidates")

    # 3) Check a few common absolute paths for each host type, using is_shugr_pi
    common_paths = []
    if is_shugr_pi:
        if req_ver:
            common_paths.extend([f"/usr/bin/python{req_ver}", f"/usr/local/bin/python{req_ver}"])
        common_paths.extend(["/usr/bin/python3", "/usr/bin/python"])
    else:
        # Windows common locations (best-effort)
        if req_ver:
            vershort = req_ver.replace(".", "")
            common_paths.extend([f"C:\\Python{vershort}\\python.exe",
                                 f"C:\\Program Files\\Python{vershort}\\python.exe",
                                 f"C:\\Program Files (x86)\\Python{vershort}\\python.exe"])
        common_paths.extend([r"C:\Python39\python.exe", r"C:\Program Files\Python39\python.exe"])

    for p in common_paths:
        if check_python(p, req_ver):
            logger.info(f"Found {p} in common paths")
            return p

    logger.warning(f"Unable to find {req_ver} in common paths")

    # 4) As a last resort, try any 'python' found on PATH and verify version
    # (iterate over PATH entries for python executables)
    path_env = os.environ.get("PATH", "")
    for dirpath in path_env.split(os.pathsep):
        for candidate in ("python.exe" if not is_shugr_pi else "python3", "python"):
            full = os.path.join(dirpath, candidate)
            if check_python(full, req_ver):
                logger.info(f"Found {full} in PATH")
                return full

    # Not found
    logger.warning(f"Unable to find {'an executable' if is_shugr_pi else 'a binary'} for {version}")
    return None
