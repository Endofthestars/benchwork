#!/bin/sh
set -eu

sh -n install.sh
if command -v shellcheck >/dev/null 2>&1; then
    shellcheck -s sh install.sh
fi
if command -v shfmt >/dev/null 2>&1; then
    shfmt -d -i 4 -ci install.sh scripts/installer/check-posix.sh
fi

for forbidden in 'eval ' 'sudo pip' 'pip install --user' 'source http' 'raw.githubusercontent.com/main'; do
    if grep -n "${forbidden}" install.sh; then
        printf 'Forbidden installer pattern: %s\n' "${forbidden}" >&2
        exit 1
    fi
done

printf 'POSIX installer checks passed.\n'
