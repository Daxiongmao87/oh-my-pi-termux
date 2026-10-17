# oh-my-pi for ARM64 Termux

Run [oh-my-pi (omp)](https://github.com/can1357/oh-my-pi) in Termux using its
**unmodified upstream Linux ARM64 binary** and `glibc-runner`.

This is a community launcher and updater, not an upstream fork or a native
Android rebuild. It installs no Node.js, Bun or Rust toolchain. The standalone
omp executable includes its runtime and extracts its own native addon.

## Requirements

- ARM64 (`aarch64`) Android device running Termux.
- Termux private storage for installation; shared `/sdcard` storage cannot run
  executables normally.
- `python`, `curl`, `coreutils`, `util-linux`, and `glibc-runner`.
- Approximately 1 GB free for the active binary, rollback copy, temporary
  download and extracted native addons. Additional omp data grows separately.

Install prerequisites using Termux's package manager:

```sh
pkg update
pkg install git python curl coreutils util-linux
pkg install glibc-repo
pkg update
pkg install glibc-runner
```

The glibc packages come from the [Termux glibc repository](https://github.com/termux/glibc-packages).
This project's installer checks for them but does not add repositories or
change system packages automatically.

## Install

Clone this repository into Termux private storage, then install:

```sh
git clone https://github.com/Daxiongmao87/oh-my-pi-termux.git
cd oh-my-pi-termux
bash install.sh
omp
```

The default install root is `~/.local/share/omp-termux`. A symlink in
`$PREFIX/bin/omp` puts the launcher on Termux's standard PATH. An unrelated
existing `omp` is preserved and installation stops with an explanation.
To deliberately migrate an existing launcher, use `--replace-launcher`;
the old launcher is renamed to `omp.before-omp-termux.<timestamp>.<pid>`.

Alternative installation paths and an exact upstream version:

```sh
bash install.sh --prefix "$HOME/apps/omp-termux" --bin-dir "$HOME/bin" --version 18.12.0
```

Custom bin directories must already be on your PATH, or use their full path.

## Use and update

```sh
omp                         # start in your current project
omp -p "Explain this code"  # upstream CLI arguments pass through
omp doctor                  # test loader, version and native grep
omp port-version            # version of this launcher/updater
omp update --check
omp update
omp update --rollback
omp update --version 18.12.0 # exact version, including a deliberate downgrade
omp update --force          # reinstall the offered stable release
```

Use `omp update` **from the Termux shell**. It replaces only the downloaded
ELF, preserving the launcher. Checks include release platform, architecture,
size, SHA-256, ELF header, version reporting and a native-grep smoke check
through `glibc-runner`. Activation is atomic; a failed post-install check
restores the previous binary. Updates and rollback serialize on a file lock.
Exit and relaunch omp to use an installed update. The previous binary is
retained; rollback swaps the two versions after verifying the target.

The adapter supports stable releases and explicit versions, not upstream
plugin-update or channel-switch flags. It uses full downloads, not deltas.
It does not intercept an update triggered inside the application, or one
invoked by bypassing this launcher.

Configure a provider with omp's `/login` or upstream environment variables.
Credentials, sessions and settings stay under omp's own `~/.omp` directory.
This repository contains no provider configuration or credentials.

## Compatibility

Verified on an ARM64 Termux phone: upstream 18.11.3 and 18.12.0 launch;
native grep/read, shell tools, a real provider-backed agent turn and TUI
startup worked during initial investigation. The packaged installer and
update/rollback path were tested separately; see [verification](docs/verification.md).

This is not a guarantee of complete Linux feature parity. Desktop control,
browser/Chromium, clipboard, language servers, debuggers and optional system
integrations need their own Android-compatible dependencies and testing.
Future upstream releases are smoke-tested before activation; regressions
outside those checks may still require rollback.

See [troubleshooting](docs/troubleshooting.md) and
[update design](docs/update-design.md).

## Uninstall

```sh
bash ~/.local/share/omp-termux/uninstall.sh
```

For custom paths, pass both the install root and bin directory:

```sh
bash /path/to/install/uninstall.sh /path/to/install /path/to/bin
```

Only an installation bearing this project's marker and its matching launcher
symlink are removed. `~/.omp` settings, credentials and sessions are preserved,
as are previously backed-up launchers and system glibc packages.

## Development

```sh
python -m unittest discover -s tests -v
bash -n install.sh uninstall.sh bin/omp
```

GitHub Actions configuration is supplied as `ci/tests.yml`. Move it to
`.github/workflows/tests.yml` to enable CI (uploading a workflow requires the
GitHub `workflow` permission).

The unit tests run on Linux without an Android device or network access.
Real loader/addon verification requires an ARM64 Termux device.

## Attribution and license

Launcher, installer and updater: [MIT](LICENSE). Upstream omp is a separate
MIT-licensed project by its respective authors. Upstream binaries and native
addons are downloaded from its official build service, not redistributed in
this source tree. `glibc-runner` and its dependencies are separately maintained
and licensed by their respective projects. No affiliation or upstream support
is implied.
