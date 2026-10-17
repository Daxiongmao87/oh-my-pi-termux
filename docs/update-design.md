# Why a wrapper-owned updater?

The upstream implementation inspected at commit
`eb74cf84d8e16ac9b8c4fa5d7c43037023d016ac` has three relevant behaviors:

1. The glibc-hosted executable reports Linux/ARM64, correctly selecting
   `linux-arm64` from the build service.
2. Update destination selection uses the PATH-resolved `omp` entry. In this
   installation that entry is a script, not the upstream executable.
3. Replacement verification executes the binary directly. Termux instead
   needs `glibc-runner` to launch it with the correct dynamic loader.

The wrapper reserves `update`, `doctor` and `port-version` and forwards all
other arguments unchanged to the upstream binary. The executable stays
unmodified, so releases do not need rebuilding or binary patching.

The updater verifies official HTTPS metadata and file size/SHA-256, rejects
non-AArch64 ELF headers, and tests version and native grep before and after
activation. SHA-256 checks integrity against service metadata; they are not
an independent publisher signature.

A per-install `flock` serializes updater processes. The new file is staged on
the same filesystem as the active binary for atomic rename. A complete copy
of the old binary is retained before switching. Running sessions can continue
using their already-mapped executable; new sessions use the replacement.

Rollback does not need network access. It verifies the previous binary,
stages a copy, then uses the same activation path. A second rollback toggles
back. System power loss during backup copying may leave a `.pending` file,
but the active path is not removed during staging.

System glibc packages and the launcher version are updated separately from
upstream omp. Rerun `install.sh` from an updated checkout to upgrade wrapper
code. Future upstream CLI or metadata changes may require wrapper changes.
