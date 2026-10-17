#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
export PREFIX="${PREFIX:-/data/data/com.termux/files/usr}"
source_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
root="$HOME/.local/share/omp-termux"
bin_dir="$PREFIX/bin"
version=""
replace=false
while (($#)); do
    case "$1" in
        --prefix) root="${2:?missing --prefix path}"; shift 2 ;;
        --bin-dir) bin_dir="${2:?missing --bin-dir path}"; shift 2 ;;
        --version) version="${2:?missing version}"; shift 2 ;;
        --replace-launcher) replace=true; shift ;;
        -h|--help)
            printf '%s\n' 'Usage: bash install.sh [--prefix DIR] [--bin-dir DIR] [--version X.Y.Z] [--replace-launcher]'
            exit 0 ;;
        *) printf 'Unknown option: %s\n' "$1" >&2; exit 2 ;;
    esac
done
[[ "$(uname -m)" == aarch64 ]] || { printf 'Requires ARM64 Termux\n' >&2; exit 1; }
for tool in python curl realpath flock; do
    command -v "$tool" >/dev/null || { printf 'Missing %s; run: pkg install python curl coreutils util-linux\n' "$tool" >&2; exit 1; }
done
[[ -f "$PREFIX/opt/glibc-runner/glibc-runner.sh" ]] || {
    printf 'Missing glibc-runner. See README.md prerequisites.\n' >&2; exit 1;
}
mkdir -p "$root" "$bin_dir"
root="$(realpath "$root")"
bin_dir="$(realpath "$bin_dir")"
case "$root/" in /storage/*|/sdcard/*) printf 'Install in Termux private storage, not shared storage\n' >&2; exit 1 ;; esac
if [[ -e "$bin_dir/omp" || -L "$bin_dir/omp" ]]; then
    if [[ "$(realpath "$bin_dir/omp")" != "$root/bin/omp" ]] && ! $replace; then
        printf 'Existing omp launcher preserved: %s\nUse --replace-launcher to back it up and replace it.\n' "$bin_dir/omp" >&2
        exit 1
    fi
fi
if [[ -e "$root/.omp-termux-install" ]]; then
    # Upgrading the wrapper must not race an updater using its old code.
    exec 9>"$root/update.lock"
    flock -x 9
elif [[ -n "$(ls -A "$root")" ]]; then
    printf 'Refusing a nonempty unowned install directory: %s\n' "$root" >&2; exit 1
fi
mkdir -p "$root/bin" "$root/lib" "$root/downloads"
cp "$source_dir/bin/omp" "$root/bin/omp"
cp "$source_dir/lib/omp_termux.py" "$root/lib/omp_termux.py"
cp "$source_dir/uninstall.sh" "$root/uninstall.sh"
chmod 700 "$root/bin/omp" "$root/uninstall.sh"
touch "$root/.omp-termux-install"
# Release the install lock before the Python updater takes the same lock.
if [[ -e /proc/$$/fd/9 ]]; then flock -u 9; exec 9>&-; fi
args=(update)
[[ -z "$version" ]] || args+=(--version "$version")
"$root/bin/omp" "${args[@]}"
if [[ -e "$bin_dir/omp" || -L "$bin_dir/omp" ]]; then
    if [[ "$(realpath "$bin_dir/omp")" != "$root/bin/omp" ]]; then
        mv "$bin_dir/omp" "$bin_dir/omp.before-omp-termux.$(date +%s).$$"
    fi
fi
ln -sfn "$root/bin/omp" "$bin_dir/omp"
printf 'Installed. Launch: %s/omp\n' "$bin_dir"
