# Troubleshooting

**`omp: command not found`** — default installs link into `$PREFIX/bin`.
Run `command -v omp`; for a custom `--bin-dir`, add that directory to PATH.

**Missing glibc-runner** — install `glibc-repo`, refresh the package list, then
install `glibc-runner`. The installer does not provision system packages.

**Binary says “No such file or directory” although it exists** — the upstream
ELF expects a glibc loader at `/lib/ld-linux-aarch64.so.1`. Use this project's
launcher rather than invoking the downloaded file directly.

**`libc.so` has bad ELF magic** — avoid exporting glibc library paths into the
bionic shell. The launcher removes `LD_LIBRARY_PATH` and `LD_PRELOAD` before
starting the runner. The runner configures its own environment.

**Update fails** — the active version is left alone if download or candidate
verification fails. Run `omp doctor`. If a later upstream regression is found,
run `omp update --rollback` from Termux, then restart omp.

**Existing launcher** — inspect `command -v omp` before choosing
`--replace-launcher`. The displaced launcher is backed up alongside the new
symlink; uninstall does not restore it automatically.

**No model / authentication** — use upstream `/login` or configure a provider
as described in the upstream docs. Loader verification requires no API key.

**Report an issue** — include `omp port-version`, `omp --version`, `uname -m`,
`termux-info` and the output of `omp doctor`. Review diagnostic output before
posting; never post credentials, sessions or full environment dumps.
