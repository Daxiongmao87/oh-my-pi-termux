#!/data/data/com.termux/files/usr/bin/bash
# Opt-in: downloads real upstream releases. Uses an isolated install + bin dir.
set -euo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
scratch="$(mktemp -d "${TMPDIR:?}/omp-port-test.XXXXXX")"
trap 'rm -rf -- "$scratch"' EXIT
mkdir "$scratch/bin"
printf '== Clean install 18.11.3 ==\n'
bash "$repo/install.sh" --prefix "$scratch/install" --bin-dir "$scratch/bin" --version 18.11.3
"$scratch/bin/omp" doctor
printf '== Exact-version update 18.12.0 ==\n'
"$scratch/bin/omp" update --version 18.12.0
[[ "$("$scratch/bin/omp" --version)" == omp/18.12.0 ]]
printf '== Offline rollback ==\n'
"$scratch/bin/omp" update --rollback
[[ "$("$scratch/bin/omp" --version)" == omp/18.11.3 ]]
printf '== Wrapper reinstall, no download ==\n'
bash "$repo/install.sh" --prefix "$scratch/install" --bin-dir "$scratch/bin" --version 18.11.3
printf '== Existing launcher preserved ==\n'
mkdir "$scratch/other-bin"
printf 'existing\n' > "$scratch/other-bin/omp"
if bash "$repo/install.sh" --prefix "$scratch/other-install" --bin-dir "$scratch/other-bin"; then
    printf 'Expected launcher conflict to fail\n' >&2; exit 1
fi
[[ "$(<"$scratch/other-bin/omp")" == existing ]]
printf '== Refuse uninstall of an unowned directory ==\n'
mkdir "$scratch/unowned"
if bash "$repo/uninstall.sh" "$scratch/unowned" "$scratch/bin"; then
    printf 'Expected ownership check to fail\n' >&2; exit 1
fi
printf '== Uninstall owned install ==\n'
bash "$repo/uninstall.sh" "$scratch/install" "$scratch/bin"
[[ ! -e "$scratch/install" && ! -L "$scratch/bin/omp" ]]
printf 'PASS: real install/update/rollback/reinstall/conflict/uninstall\n'
