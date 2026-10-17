# Verification record

## Tested environment

- Android ARM64 (`aarch64`) phone with Termux 0.118.3.
- Python 3.14, existing glibc 2.44 and glibc-runner 2.0-3 packages.
- Upstream omp Linux ARM64 releases 18.11.3 and 18.12.0.

## Automated unit tests

`python -m unittest discover -s tests -v`: **10 passed**.

Coverage includes successful activation and backup, restoration after a
post-install smoke failure, failed first-install cleanup, rollback without
losing either version, rejection of broken rollback targets, truncated/hash-
mismatched downloads, wrong ELF architecture, wrong metadata platform/version,
loader-environment cleanup, rejected candidate cleanup, and inter-process lock
exclusion.

The GitHub Actions template at `ci/tests.yml` runs these tests and shell syntax
checks on Linux. Move it to `.github/workflows/tests.yml` to enable it. Uploading
an active workflow requires GitHub authorization with the `workflow` scope.
It has not yet run on GitHub; local success is not a claim of remote CI success.

## Real ARM64 Termux integration test

Run explicitly (downloads roughly 430 MB):

```sh
bash tests/termux-integration.sh
```

Passed locally:

1. Install into an empty private-storage directory and create the PATH symlink.
2. Download 18.11.3 from the official service; verify size, SHA-256, ELF header,
   reported version and native grep.
3. `omp doctor` through the generated symlink.
4. Download and install 18.12.0; verify it before and after activation.
5. Roll back without network access; verify 18.11.3 is active.
6. Reinstall wrapper files while keeping the selected upstream version.
7. Refuse to overwrite an unrelated launcher.
8. Refuse uninstall of a directory without the installation marker.
9. Remove the owned installation and its matching symlink.

The test uses a separate bin directory and does not change the user's existing
`omp` launcher. It uses the device's existing glibc environment and default
omp data directory; it is not a reset of the device or a sandbox for upstream
cache files.

## Limitations of this verification

glibc provisioning on a completely fresh Termux install has not been tested.
The prerequisite commands are taken from the Termux glibc repository README.
Optional integrations and full Linux feature parity are not established by
these tests. No model credentials are needed for the packaged integration test.
