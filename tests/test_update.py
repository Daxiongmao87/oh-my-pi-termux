import hashlib
import importlib.util
from pathlib import Path
import struct
import tempfile
import subprocess
import sys
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("port", Path(__file__).resolve().parents[1] / "lib/omp_termux.py")
port = importlib.util.module_from_spec(spec)
spec.loader.exec_module(port)


class Updates(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.install = port.Installation(self.temp.name)
        self.install.binary.parent.mkdir()
        self.install.binary.write_bytes(b"original")
        self.candidate = self.install.binary.parent / "candidate"
        self.candidate.write_bytes(b"replacement")

    def test_activation_and_backup(self):
        with patch.object(self.install, "smoke"):
            self.install.activate(self.candidate, "1.0.0")
        self.assertEqual(self.install.binary.read_bytes(), b"replacement")
        self.assertEqual(self.install.previous.read_bytes(), b"original")

    def test_failed_post_install_restores_original(self):
        with patch.object(self.install, "smoke", side_effect=RuntimeError("bad native addon")):
            with self.assertRaises(RuntimeError):
                self.install.activate(self.candidate, "1.0.0")
        self.assertEqual(self.install.binary.read_bytes(), b"original")
        self.assertEqual(self.install.previous.read_bytes(), b"original")

    def test_failed_first_install_leaves_no_binary(self):
        self.install.binary.unlink()
        with patch.object(self.install, "smoke", side_effect=RuntimeError("bad")):
            with self.assertRaises(RuntimeError):
                self.install.activate(self.candidate, "1.0.0")
        self.assertFalse(self.install.binary.exists())

    def test_rollback_toggles_without_losing_either_version(self):
        self.install.previous.write_bytes(b"previous")
        with patch.object(self.install, "version", return_value="1.0.0"), patch.object(self.install, "smoke"):
            self.install.rollback()
        self.assertEqual(self.install.binary.read_bytes(), b"previous")
        self.assertEqual(self.install.previous.read_bytes(), b"original")

    def test_failed_rollback_keeps_active_binary(self):
        self.install.previous.write_bytes(b"broken")
        with patch.object(self.install, "version", return_value="1.0.0"), \
             patch.object(self.install, "smoke", side_effect=RuntimeError("broken")):
            with self.assertRaises(RuntimeError):
                self.install.rollback()
        self.assertEqual(self.install.binary.read_bytes(), b"original")

    def test_elf_and_checksum_checks(self):
        data = bytearray(64)
        data[:6] = b"\x7fELF\x02\x01"
        struct.pack_into("<H", data, 18, 183)
        self.candidate.write_bytes(data)
        metadata = {"size": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        port.verify_file(self.candidate, metadata)
        self.candidate.write_bytes(data[:30])
        with self.assertRaisesRegex(RuntimeError, "SHA-256"):
            port.verify_file(self.candidate, metadata)
        struct.pack_into("<H", data, 18, 62)
        self.candidate.write_bytes(data)
        metadata["sha256"] = hashlib.sha256(data).hexdigest()
        with self.assertRaisesRegex(RuntimeError, "AArch64"):
            port.verify_file(self.candidate, metadata)

    def test_candidate_smoke_failure_never_activates(self):
        answer = {"build": {"version": "2.0.0"}, "file": {"size": 64, "sha256": "0" * 64}, "download": "https://invalid/"}
        with patch.object(self.install, "version", return_value="1.0.0"), \
             patch.object(self.install, "metadata", return_value=answer), \
             patch.object(self.install, "download"), patch.object(port, "verify_file"), \
             patch.object(self.install, "smoke", side_effect=RuntimeError("grep failed")):
            with self.assertRaises(RuntimeError):
                self.install.update()
        self.assertEqual(self.install.binary.read_bytes(), b"original")
        self.assertEqual(list(self.install.binary.parent.glob("download-*")), [])

    def test_clean_env_preserves_credentials_not_loader_overrides(self):
        with patch.dict(port.os.environ, {"LD_PRELOAD": "bad", "LD_LIBRARY_PATH": "bad", "SAMPLE_API_KEY": "kept"}):
            env = port.clean_env()
        self.assertNotIn("LD_PRELOAD", env)
        self.assertNotIn("LD_LIBRARY_PATH", env)
        self.assertEqual(env["SAMPLE_API_KEY"], "kept")

    def test_metadata_rejects_other_platform_and_exact_version_mismatch(self):
        answer = {"build": {"version": "1.0.0"},
                  "file": {"platform": "linux", "arch": "arm64", "name": "omp-linux-arm64",
                           "size": 64, "sha256": "0" * 64}, "download": "https://example.invalid/file"}
        port.validate_metadata(answer, "1.0.0")
        with self.assertRaisesRegex(RuntimeError, "different version"):
            port.validate_metadata(answer, "2.0.0")
        answer["file"]["arch"] = "x86_64"
        with self.assertRaisesRegex(RuntimeError, "architecture"):
            port.validate_metadata(answer)

    def test_second_process_cannot_take_held_lock(self):
        lock_path = self.install.root / "update.lock"
        with lock_path.open("a") as lock:
            port.fcntl.flock(lock, port.fcntl.LOCK_EX)
            probe = (
                "import fcntl,sys; f=open(sys.argv[1],'a'); "
                "fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)"
            )
            result = subprocess.run([sys.executable, "-c", probe, str(lock_path)], capture_output=True)
            self.assertNotEqual(result.returncode, 0)
        result = subprocess.run([sys.executable, "-c", probe, str(lock_path)], capture_output=True)
        self.assertEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
