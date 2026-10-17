#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail
root="${1:-$HOME/.local/share/omp-termux}"
bin_dir="${2:-${PREFIX:-/data/data/com.termux/files/usr}/bin}"
root="$(realpath "$root")"
[[ -f "$root/.omp-termux-install" ]] || { printf 'Not an omp-termux installation: %s\n' "$root" >&2; exit 1; }
exec 9>"$root/update.lock"
flock -x 9
if [[ -L "$bin_dir/omp" && "$(realpath "$bin_dir/omp")" == "$root/bin/omp" ]]; then
    rm "$bin_dir/omp"
fi
rm -r -- "$root"
printf 'Removed omp-termux. Your ~/.omp settings, credentials and sessions were preserved.\n'
