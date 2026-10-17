"""Launcher/update support for upstream omp's unmodified Linux ARM64 binary."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import struct
import subprocess
import tempfile

VERSION = "0.1.0"
ORIGIN = "https://build.stencil.so/api/products/omp"
SEMVER = re.compile(r"\d+\.\d+\.\d+(?:-[\w.-]+)?")


def clean_env():
    env = os.environ.copy()
    for name in ("LD_PRELOAD", "LD_LIBRARY_PATH"):
        env.pop(name, None)
    return env


class Installation:
    def __init__(self, root=None):
        self.root = Path(root or Path(__file__).resolve().parent.parent)
        self.prefix = Path(os.environ.get("PREFIX", "/data/data/com.termux/files/usr"))
        self.runner = self.prefix / "opt/glibc-runner/glibc-runner.sh"
        self.binary = self.root / "downloads/omp"
        self.previous = self.root / "downloads/omp.previous"

    def command(self, binary, *args):
        return [str(self.prefix / "bin/bash"), str(self.runner), str(binary), *args]

    def run(self, binary, *args, cwd=None):
        try:
            return subprocess.run(self.command(binary, *args), cwd=cwd, env=clean_env(),
                                  text=True, capture_output=True, timeout=120, check=True).stdout
        except subprocess.CalledProcessError as error:
            raise RuntimeError(f"omp verification failed: {error.stderr.strip()}") from error

    def version(self, binary):
        output = self.run(binary, "--version").strip()
        version = output.removeprefix("omp/")
        if output == version or not SEMVER.fullmatch(version):
            raise RuntimeError(f"Invalid version response: {output!r}")
        return version

    def smoke(self, binary, expected):
        if self.version(binary) != expected:
            raise RuntimeError("Candidate reports the wrong version")
        with tempfile.TemporaryDirectory(prefix="probe-", dir=self.root) as directory:
            Path(directory, "probe.txt").write_text("OMP_TERMUX_PROBE\n")
            output = self.run(binary, "grep", "OMP_TERMUX_PROBE", ".", cwd=directory)
            if "probe.txt:1:" not in output or "Total matches: 1" not in output:
                raise RuntimeError("Native grep smoke check failed")
        print(f"Verified {expected}: loader + native grep", flush=True)

    def metadata(self, exact=None):
        route = f"versions/{exact}/linux-arm64" if exact else "latest/linux-arm64?channel=stable"
        raw = subprocess.check_output([str(self.prefix / "bin/curl"), "-fsSL", "--retry", "2",
                                       "--max-time", "60", f"{ORIGIN}/{route}"],
                                      env=clean_env(), text=True, timeout=200)
        return validate_metadata(json.loads(raw), exact)

    def download(self, url, destination):
        # Keep signed URLs out of exception messages and logs.
        process = subprocess.run([str(self.prefix / "bin/curl"), "-fsSL", "--retry", "2",
                                  "--max-time", "600", "-o", str(destination), url],
                                 env=clean_env(), capture_output=True, timeout=1900)
        if process.returncode:
            raise RuntimeError(f"Download failed (curl exit {process.returncode})")

    def activate(self, candidate, expected):
        """Atomic active-file replacement; retain a fully copied previous binary."""
        had_binary = self.binary.exists()
        backup_temp = self.previous.with_suffix(".pending")
        try:
            if had_binary:
                shutil.copy2(self.binary, backup_temp)
                os.replace(backup_temp, self.previous)
            os.replace(candidate, self.binary)
            try:
                self.smoke(self.binary, expected)
            except BaseException:
                if had_binary:
                    # Keep the rollback copy too, rather than consuming it.
                    shutil.copy2(self.previous, candidate)
                    os.replace(candidate, self.binary)
                else:
                    self.binary.unlink(missing_ok=True)
                raise
        finally:
            backup_temp.unlink(missing_ok=True)

    def rollback(self):
        if not self.previous.exists():
            raise RuntimeError("No previous binary retained")
        expected = self.version(self.previous)
        self.smoke(self.previous, expected)
        # Copy the previous version before activate() changes the backup.
        fd, name = tempfile.mkstemp(prefix="rollback-", dir=self.binary.parent)
        os.close(fd)
        candidate = Path(name)
        try:
            shutil.copy2(self.previous, candidate)
            self.activate(candidate, expected)
        finally:
            candidate.unlink(missing_ok=True)
        print(f"Rolled back to {expected}; restart omp")

    def update(self, check=False, force=False, exact=None):
        current = self.version(self.binary) if self.binary.exists() else None
        print(f"Installed: {current or 'none'}", flush=True)
        answer = self.metadata(exact)
        offered = answer["build"]["version"]
        print(f"Available: {offered} (linux-arm64/glibc)", flush=True)
        if check or (current == offered and not force):
            return
        fd, name = tempfile.mkstemp(prefix="download-", dir=self.binary.parent)
        os.close(fd)
        candidate = Path(name)
        try:
            print(f"Downloading {answer['file']['size']:,} bytes…", flush=True)
            self.download(answer["download"], candidate)
            verify_file(candidate, answer["file"])
            candidate.chmod(0o700)
            self.smoke(candidate, offered)
            self.activate(candidate, offered)
            record = {"previous": current, "installed": offered, "target": "linux-arm64",
                      "size": answer["file"]["size"], "sha256": answer["file"]["sha256"]}
            (self.root / "last-update.json").write_text(json.dumps(record, indent=2) + "\n")
            print(f"Installed {offered}. Restart omp; undo with: omp update --rollback")
        finally:
            candidate.unlink(missing_ok=True)


def validate_metadata(answer, exact=None):
    version = answer["build"]["version"]
    file = answer["file"]
    if not isinstance(version, str) or not SEMVER.fullmatch(version):
        raise RuntimeError("Invalid release version")
    if exact and version != exact:
        raise RuntimeError("Service returned a different version than requested")
    if (file["platform"], file["arch"], file["name"]) != ("linux", "arm64", "omp-linux-arm64"):
        raise RuntimeError("Wrong platform/architecture in release metadata")
    if type(file["size"]) is not int or file["size"] < 20:
        raise RuntimeError("Invalid download size")
    if not re.fullmatch(r"[a-f0-9]{64}", file["sha256"]):
        raise RuntimeError("Invalid SHA-256")
    if not answer["download"].startswith("https://"):
        raise RuntimeError("Expected an HTTPS download")
    return answer


def verify_file(candidate, metadata):
    digest = hashlib.sha256()
    size = 0
    with candidate.open("rb") as stream:
        header = stream.read(20)
        stream.seek(0)
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
            size += len(chunk)
    if size != metadata["size"] or digest.hexdigest() != metadata["sha256"]:
        raise RuntimeError("Download size/SHA-256 mismatch")
    if len(header) < 20 or header[:6] != b"\x7fELF\x02\x01" or struct.unpack_from("<H", header, 18)[0] != 183:
        raise RuntimeError("Not an ELF64 AArch64 binary")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    update = sub.add_parser("update", help="Install/check a stable upstream release")
    update.add_argument("-c", "--check", action="store_true")
    update.add_argument("-f", "--force", action="store_true")
    group = update.add_mutually_exclusive_group()
    group.add_argument("--version")
    group.add_argument("--rollback", action="store_true")
    sub.add_parser("doctor", help="Check loader, binary and native grep")
    sub.add_parser("port-version", help="Print launcher version")
    args = parser.parse_args()
    if args.action == "port-version":
        print(VERSION)
        return
    if platform.machine() not in ("aarch64", "arm64"):
        parser.error("Requires ARM64 Termux")
    install = Installation()
    if not install.runner.exists():
        parser.error("Missing glibc-runner; see README prerequisites")
    if args.action == "doctor":
        install.smoke(install.binary, install.version(install.binary))
        return
    if args.version and not SEMVER.fullmatch(args.version):
        parser.error("Invalid version")
    if args.rollback and (args.check or args.force):
        parser.error("--rollback cannot be combined with --check/--force")
    install.binary.parent.mkdir(parents=True, exist_ok=True)
    with (install.root / "update.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if args.rollback:
            install.rollback()
        else:
            install.update(args.check, args.force, args.version)


if __name__ == "__main__":
    try:
        main()
    except (Exception, KeyboardInterrupt) as error:
        raise SystemExit(f"omp-termux: {error}")
