#!/bin/sh
# Benchwork POSIX installer bootstrap. Persistent configuration is delegated to
# the exact bwork package installed below.

set -eu
# shellcheck disable=SC3040
if (set -o pipefail) 2>/dev/null; then
    # shellcheck disable=SC3040
    set -o pipefail
fi
umask 077

PROGRAM=benchwork-installer
DEFAULT_BASE_URL=https://benchwork.dev
DEFAULT_GITHUB_RELEASES=https://github.com/Endofthestars/benchwork/releases/download
MAX_JSON_SIZE=1048576
MAX_PLUGIN_SIZE=26214400
MAX_WHEEL_SIZE=52428800
if [ -x /usr/bin/id ]; then
    current_uid=$(/usr/bin/id -u)
else
    current_uid=$(id -u)
fi
if [ "${current_uid}" -eq 0 ]; then
    PATH=/usr/local/bin:/usr/bin:/bin
    export PATH
fi

say() {
    if [ "${quiet}" -eq 0 ] && [ "${json_output:-0}" -eq 0 ]; then
        printf '%s\n' "$*"
    fi
}

verbose() {
    if [ "${verbose_mode}" -eq 1 ]; then
        printf '%s\n' "$*" >&2
    fi
}

fail() {
    code=$1
    shift
    printf '%s: %s\n' "${PROGRAM}" "$*" >&2
    exit "${code}"
}

shell_quote() {
    escaped=$(printf '%s' "$1" | sed "s/'/'\"'\"'/g")
    printf "'%s'" "${escaped}"
}

usage() {
    cat <<'EOF'
Install Benchwork in an isolated user environment.

Usage:
  sh install.sh [options]

Release:
  --version VERSION             Install one exact Benchwork version
  --channel stable|rc|nightly   Resolve a release channel (default: stable)
  --backend auto|uv|pipx        Select the isolated tool backend
  --install-dir PATH            Backend tool-environment directory
  --bin-dir PATH                Executable-link directory

Hosts and plugin:
  --with-codex                  Configure detected Codex integration
  --with-claude                 Configure experimental Claude MCP integration
  --without-hosts               Disable all Host configuration
  --plugin-scope user|project|none
  --project-root PATH           Required for project plugin scope

Behavior:
  --modify-path | --no-modify-path
  --dry-run | --print-plan
  --yes
  --quiet | --verbose
  --json
  --repair | --uninstall [--purge]
  --force
  --help

CLI options override BENCHWORK_* environment variables. The installer never
uses sudo, mutates system Python, initializes a research project, or installs a
Host CLI.
EOF
}

parse_boolean() {
    value=$1
    label=$2
    case "${value}" in
        1 | true | TRUE | yes | YES | on | ON) printf '1' ;;
        0 | false | FALSE | no | NO | off | OFF | '') printf '0' ;;
        *) fail 2 "${label} must be a boolean (0/1, true/false, yes/no)" ;;
    esac
}

validate_scalar() {
    value=$1
    label=$2
    carriage_return=$(printf '\r')
    case "${value}" in
        *'
'* | *"${carriage_return}"*) fail 2 "${label} contains a newline or carriage return" ;;
    esac
    without_controls=$(printf '%s' "${value}" | LC_ALL=C tr -d '[:cntrl:]')
    [ "${without_controls}" = "${value}" ] ||
        fail 2 "${label} contains a control character"
}

require_uint() {
    value=$1
    label=$2
    case "${value}" in
        '' | *[!0-9]*) fail 4 "${label} must be an unsigned integer" ;;
    esac
}

require_sha256() {
    value=$1
    label=$2
    case "${value}" in
        '' | *[!0-9a-f]*) fail 4 "${label} must be a lowercase SHA-256 digest" ;;
    esac
    [ "${#value}" -eq 64 ] || fail 4 "${label} must be a lowercase SHA-256 digest"
}

absolute_path() {
    value=$1
    label=$2
    validate_scalar "${value}" "${label}"
    case "${value}" in
        /*) ;;
        *) fail 2 "${label} must be an absolute path" ;;
    esac
}

owner_and_mode() {
    target=$1
    if stat -c '%u %a' "${target}" >/dev/null 2>&1; then
        stat -c '%u %a' "${target}"
    else
        stat -f '%u %Lp' "${target}"
    fi
}

check_target_directory() {
    target=$1
    while [ ! -e "${target}" ]; do
        parent=${target%/*}
        [ -n "${parent}" ] || parent=/
        [ "${parent}" != "${target}" ] || break
        target=${parent}
    done
    [ -d "${target}" ] || fail 2 "installation target parent is not a directory: ${target}"
    owner_mode=$(owner_and_mode "${target}")
    owner=${owner_mode%% *}
    mode=${owner_mode#* }
    world_digit=$(printf '%s' "${mode}" | sed 's/.*\(.\)$/\1/')
    case "${world_digit}" in
        2 | 3 | 6 | 7)
            [ "${owner}" = "${current_uid}" ] ||
                fail 2 "target is world-writable and owned by another user: ${target}"
            ;;
    esac
}

version_is_newer() {
    awk -v left="$1" -v right="$2" '
function stage(value, suffix) {
    suffix = value
    if (value ~ /dev[0-9]+$/) { sub(/^.*dev/, "", suffix); return 100000 + suffix }
    if (value ~ /a[0-9]+$/) { sub(/^.*a/, "", suffix); return 200000 + suffix }
    if (value ~ /b[0-9]+$/) { sub(/^.*b/, "", suffix); return 300000 + suffix }
    if (value ~ /rc[0-9]+$/) { sub(/^.*rc/, "", suffix); return 400000 + suffix }
    return 900000
}
function component(value, index, core, count, parts) {
    core = value
    sub(/[a-z].*$/, "", core)
    count = split(core, parts, ".")
    return index <= count ? parts[index] + 0 : 0
}
BEGIN {
    for (index = 1; index <= 3; index++) {
        a = component(left, index)
        b = component(right, index)
        if (a > b) exit 0
        if (a < b) exit 1
    }
    exit !(stage(left) > stage(right))
}'
}

version=${BENCHWORK_VERSION:-}
channel=${BENCHWORK_CHANNEL:-stable}
backend=${BENCHWORK_BACKEND:-auto}
backend_explicit=0
[ "${backend}" = auto ] || backend_explicit=1
install_dir=${BENCHWORK_INSTALL_DIR:-}
bin_dir=${BENCHWORK_BIN_DIR:-}
with_codex=$(parse_boolean "${BENCHWORK_WITH_CODEX:-0}" BENCHWORK_WITH_CODEX)
with_claude=$(parse_boolean "${BENCHWORK_WITH_CLAUDE:-0}" BENCHWORK_WITH_CLAUDE)
without_hosts=$(parse_boolean "${BENCHWORK_WITHOUT_HOSTS:-0}" BENCHWORK_WITHOUT_HOSTS)
plugin_scope=${BENCHWORK_PLUGIN_SCOPE:-}
project_root=${BENCHWORK_PROJECT_ROOT:-}
modify_path=$(parse_boolean "${BENCHWORK_MODIFY_PATH:-0}" BENCHWORK_MODIFY_PATH)
no_modify_path=$(parse_boolean "${BENCHWORK_NO_MODIFY_PATH:-0}" BENCHWORK_NO_MODIFY_PATH)
no_bootstrap_uv=$(parse_boolean "${BENCHWORK_NO_BOOTSTRAP_UV:-0}" BENCHWORK_NO_BOOTSTRAP_UV)
dry_run=$(parse_boolean "${BENCHWORK_DRY_RUN:-0}" BENCHWORK_DRY_RUN)
print_plan=$(parse_boolean "${BENCHWORK_PRINT_PLAN:-0}" BENCHWORK_PRINT_PLAN)
assume_yes=$(parse_boolean "${BENCHWORK_YES:-0}" BENCHWORK_YES)
quiet=$(parse_boolean "${BENCHWORK_QUIET:-0}" BENCHWORK_QUIET)
verbose_mode=$(parse_boolean "${BENCHWORK_VERBOSE:-0}" BENCHWORK_VERBOSE)
json_output=$(parse_boolean "${BENCHWORK_JSON:-0}" BENCHWORK_JSON)
uninstall=$(parse_boolean "${BENCHWORK_UNINSTALL:-0}" BENCHWORK_UNINSTALL)
repair=$(parse_boolean "${BENCHWORK_REPAIR:-0}" BENCHWORK_REPAIR)
purge=$(parse_boolean "${BENCHWORK_PURGE:-0}" BENCHWORK_PURGE)
force=$(parse_boolean "${BENCHWORK_FORCE:-0}" BENCHWORK_FORCE)
base_url=${BENCHWORK_INSTALLER_BASE_URL:-${DEFAULT_BASE_URL}}
install_dir_explicit=0
[ -z "${install_dir}" ] || install_dir_explicit=1
bin_dir_explicit=0
[ -z "${bin_dir}" ] || bin_dir_explicit=1
# Reserved compatibility switch. Benchwork does not contain telemetry.
: "$(parse_boolean "${BENCHWORK_NO_TELEMETRY:-1}" BENCHWORK_NO_TELEMETRY)"
[ "${no_modify_path}" -eq 0 ] || modify_path=0

version_set=0
if [ -n "${version}" ]; then
    version_set=1
fi
channel_set=0
if [ "${BENCHWORK_CHANNEL+x}" = x ]; then
    channel_set=1
fi

while [ "$#" -gt 0 ]; do
    case "$1" in
        --help)
            usage
            exit 0
            ;;
        --version)
            [ "$#" -ge 2 ] || fail 2 "--version requires a value"
            version=$2
            version_set=1
            channel_set=0
            shift 2
            ;;
        --channel)
            [ "$#" -ge 2 ] || fail 2 "--channel requires a value"
            channel=$2
            channel_set=1
            version=
            version_set=0
            shift 2
            ;;
        --backend)
            [ "$#" -ge 2 ] || fail 2 "--backend requires a value"
            backend=$2
            backend_explicit=1
            shift 2
            ;;
        --install-dir)
            [ "$#" -ge 2 ] || fail 2 "--install-dir requires a value"
            install_dir=$2
            install_dir_explicit=1
            shift 2
            ;;
        --bin-dir)
            [ "$#" -ge 2 ] || fail 2 "--bin-dir requires a value"
            bin_dir=$2
            bin_dir_explicit=1
            shift 2
            ;;
        --with-codex)
            with_codex=1
            without_hosts=0
            shift
            ;;
        --with-claude)
            with_claude=1
            without_hosts=0
            shift
            ;;
        --without-hosts)
            without_hosts=1
            with_codex=0
            with_claude=0
            shift
            ;;
        --plugin-scope)
            [ "$#" -ge 2 ] || fail 2 "--plugin-scope requires a value"
            plugin_scope=$2
            shift 2
            ;;
        --project-root)
            [ "$#" -ge 2 ] || fail 2 "--project-root requires a value"
            project_root=$2
            shift 2
            ;;
        --modify-path)
            modify_path=1
            no_modify_path=0
            shift
            ;;
        --no-modify-path)
            no_modify_path=1
            modify_path=0
            shift
            ;;
        --dry-run)
            dry_run=1
            shift
            ;;
        --print-plan)
            print_plan=1
            shift
            ;;
        --yes)
            assume_yes=1
            shift
            ;;
        --quiet)
            quiet=1
            verbose_mode=0
            shift
            ;;
        --verbose)
            verbose_mode=1
            quiet=0
            shift
            ;;
        --json)
            json_output=1
            shift
            ;;
        --uninstall)
            uninstall=1
            repair=0
            shift
            ;;
        --repair)
            repair=1
            uninstall=0
            shift
            ;;
        --purge)
            purge=1
            shift
            ;;
        --force)
            force=1
            shift
            ;;
        --)
            shift
            break
            ;;
        *) fail 2 "unknown option: $1" ;;
    esac
done
[ "$#" -eq 0 ] || fail 2 "unexpected positional argument: $1"

case "${channel}" in stable | rc | nightly) ;; *) fail 2 "invalid channel: ${channel}" ;; esac
case "${backend}" in auto | uv | pipx) ;; *) fail 2 "invalid backend: ${backend}" ;; esac
if [ -n "${plugin_scope}" ]; then
    case "${plugin_scope}" in user | project | none) ;; *) fail 2 "invalid plugin scope: ${plugin_scope}" ;; esac
fi
[ "${quiet}" -eq 0 ] || [ "${verbose_mode}" -eq 0 ] || fail 2 "--quiet conflicts with --verbose"
[ "${uninstall}" -eq 0 ] || [ "${repair}" -eq 0 ] || fail 2 "--uninstall conflicts with --repair"
[ "${purge}" -eq 0 ] || [ "${uninstall}" -eq 1 ] || fail 2 "--purge requires --uninstall"
if [ "${without_hosts}" -eq 1 ] && { [ "${with_codex}" -eq 1 ] || [ "${with_claude}" -eq 1 ]; }; then
    fail 2 "--without-hosts conflicts with requested Host configuration"
fi
if [ "${version_set}" -eq 1 ] && [ "${channel_set}" -eq 1 ]; then
    fail 2 "--version conflicts with --channel"
fi
if [ "${without_hosts}" -eq 1 ]; then
    with_codex=0
    with_claude=0
fi
if [ -z "${plugin_scope}" ]; then
    if [ "${with_codex}" -eq 1 ]; then plugin_scope=user; else plugin_scope=none; fi
fi
if [ "${plugin_scope}" = project ]; then
    [ -n "${project_root}" ] || fail 2 "--plugin-scope project requires --project-root"
    absolute_path "${project_root}" "project root"
    if [ ! -d "${project_root}" ] || [ ! -w "${project_root}" ]; then
        fail 2 "project root must be an existing writable directory: ${project_root}"
    fi
    check_target_directory "${project_root}"
fi
[ -z "${install_dir}" ] || absolute_path "${install_dir}" "installation directory"
[ -z "${bin_dir}" ] || absolute_path "${bin_dir}" "binary directory"
case "${base_url}" in https://*) ;; *) fail 2 "BENCHWORK_INSTALLER_BASE_URL must use HTTPS" ;; esac
validate_scalar "${version}" "version"
case "${version}" in *[!0-9A-Za-z.+-]*) fail 2 "version contains unsupported characters" ;; esac

[ -n "${HOME:-}" ] || fail 2 "HOME is not set; provide a writable user HOME"
if [ ! -d "${HOME}" ] || [ ! -w "${HOME}" ]; then
    fail 2 "HOME is not a writable directory: ${HOME}"
fi

tmp_root=
lock_dir=
cleanup() {
    if [ -n "${lock_dir}" ] && [ -d "${lock_dir}" ]; then
        rm -r "${lock_dir}"
    fi
    if [ -n "${tmp_root}" ] && [ -d "${tmp_root}" ]; then
        rm -r "${tmp_root}"
    fi
}
trap cleanup EXIT HUP INT TERM
tmp_root=$(mktemp -d "${TMPDIR:-/tmp}/benchwork-install.XXXXXX") ||
    fail 2 "cannot create a private temporary directory"
[ -w "${tmp_root}" ] || fail 2 "temporary directory is not writable"

os_name=$(uname -s 2>/dev/null || printf unknown)
arch_name=$(uname -m 2>/dev/null || printf unknown)
case "${os_name}:${arch_name}" in
    Darwin:x86_64 | Darwin:arm64 | Linux:x86_64 | Linux:aarch64 | Linux:arm64) ;;
    *) fail 2 "unsupported platform ${os_name}/${arch_name}; use macOS, Linux, or WSL2" ;;
esac
if [ "${os_name}" = Linux ] && [ -f /etc/alpine-release ]; then
    fail 2 "musl-only Linux is not supported; use a validated glibc distribution"
fi

if command -v python3 >/dev/null 2>&1; then
    json_parser=python3
elif command -v jq >/dev/null 2>&1; then
    json_parser=jq
    jq_version=$(jq --version | sed 's/^jq-//')
    case "${jq_version}" in 1.[6-9]* | [2-9].*) ;; *) fail 2 "jq 1.6 or newer is required" ;; esac
else
    fail 2 "release JSON requires python3 or jq >=1.6; install one and retry"
fi
command -v curl >/dev/null 2>&1 || command -v wget >/dev/null 2>&1 ||
    fail 2 "curl or wget is required"
if command -v sha256sum >/dev/null 2>&1; then
    sha_command=sha256sum
elif command -v shasum >/dev/null 2>&1; then
    sha_command=shasum
else
    fail 2 "sha256sum or shasum is required"
fi
codex_detected=0
command -v codex >/dev/null 2>&1 && codex_detected=1
claude_detected=0
command -v claude >/dev/null 2>&1 && claude_detected=1
git_detected=0
command -v git >/dev/null 2>&1 && git_detected=1
codex_detection=not_detected
[ "${codex_detected}" -eq 0 ] || codex_detection=detected
codex_request=not_requested
[ "${with_codex}" -eq 0 ] || codex_request=requested
claude_detection=not_detected
[ "${claude_detected}" -eq 0 ] || claude_detection=detected
claude_request=not_requested
[ "${with_claude}" -eq 0 ] || claude_request=experimental_requested

download() {
    url=$1
    output=$2
    limit=$3
    case "${url}" in https://*) ;; *) fail 4 "refusing non-HTTPS download: ${url}" ;; esac
    verbose "download ${url}"
    if command -v curl >/dev/null 2>&1; then
        curl --fail --silent --show-error --location --max-redirs 3 \
            --proto '=https' --proto-redir '=https' \
            --connect-timeout 10 --max-time 60 --retry 3 \
            --output "${output}" "${url}" ||
            fail 5 "download failed: ${url}; check network access and retry"
    else
        wget --https-only --max-redirect=3 --timeout=30 --tries=3 \
            --quiet --output-document="${output}" "${url}" ||
            fail 5 "download failed: ${url}; check network access and retry"
    fi
    size=$(wc -c <"${output}" | tr -d ' ')
    [ "${size}" -le "${limit}" ] ||
        fail 4 "download exceeded ${limit} bytes: ${url}"
}

sha256() {
    if [ "${sha_command}" = sha256sum ]; then
        sha256sum "$1" | awk '{print $1}'
    else
        shasum -a 256 "$1" | awk '{print $1}'
    fi
}

verify_sha() {
    file=$1
    expected=$2
    actual=$(sha256 "${file}")
    [ "${actual}" = "${expected}" ] ||
        fail 4 "checksum mismatch for ${file}; expected ${expected}, computed ${actual}"
}

check_duplicate_keys() {
    file=$1
    if [ "${json_parser}" = python3 ]; then
        python3 -c '
import json, sys
def pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError("duplicate JSON key: " + key)
        result[key] = value
    return result
with open(sys.argv[1], "rb") as stream:
    json.load(stream, object_pairs_hook=pairs)
' "${file}" || fail 4 "release JSON is invalid or contains duplicate keys"
    else
        jq -e . "${file}" >/dev/null || fail 4 "release JSON is invalid"
        duplicate=$(
            jq --stream -r 'select(length == 2) | .[0] | @json' "${file}" |
                sort | uniq -d | head -n 1
        )
        [ -z "${duplicate}" ] || fail 4 "release JSON contains a duplicate path: ${duplicate}"
    fi
}

json_get() {
    file=$1
    expression=$2
    if [ "${json_parser}" = python3 ]; then
        python3 -c '
import json, sys
with open(sys.argv[1], "r", encoding="utf-8") as stream:
    value = json.load(stream)
for part in sys.argv[2].split("."):
    value = value[part]
if isinstance(value, bool):
    print("true" if value else "false")
elif isinstance(value, (str, int)):
    print(value)
else:
    raise SystemExit("requested manifest value is not scalar")
' "${file}" "${expression}"
    else
        jq -er ".${expression} | strings, numbers" "${file}"
    fi
}

if [ "${uninstall}" -eq 1 ] || { [ "${repair}" -eq 1 ] && [ "${version_set}" -eq 0 ] && [ "${channel_set}" -eq 0 ]; }; then
    bwork_existing=$(command -v bwork 2>/dev/null || true)
    recovery_state=${BENCHWORK_INSTALL_STATE:-${XDG_DATA_HOME:-${HOME}/.local/share}/benchwork/install-state.json}
    recovered_cli=0
    if [ "${uninstall}" -eq 1 ] && [ -n "${bwork_existing}" ] &&
        ! "${bwork_existing}" --version >/dev/null 2>&1; then
        bwork_existing=
    fi
    if [ "${repair}" -eq 1 ] && [ -n "${bwork_existing}" ]; then
        if ! "${bwork_existing}" install doctor >/dev/null 2>&1 ||
            ! "${bwork_existing}" plugin check >/dev/null 2>&1; then
            bwork_existing=
        fi
    fi
    if [ -z "${bwork_existing}" ]; then
        [ -f "${recovery_state}" ] ||
            fail 5 "no bwork executable or installer state is available for recovery"
        check_duplicate_keys "${recovery_state}"
        recovery_backend=$(json_get "${recovery_state}" backend)
        recovery_install_dir=$(json_get "${recovery_state}" install_dir)
        recovery_bin_dir=$(json_get "${recovery_state}" bin_dir)
        if [ "${uninstall}" -eq 1 ]; then
            if [ "${recovery_backend}" = uv ]; then
                recovery_python=${recovery_install_dir}/benchwork-arcana/bin/python
            else
                recovery_python=${recovery_install_dir}/venvs/benchwork-arcana/bin/python
            fi
            [ -x "${recovery_python}" ] ||
                fail 5 "the recorded Benchwork environment is missing; reinstall the recorded exact version before uninstall"
            set -- -m benchwork.cli install uninstall
            [ "${dry_run}" -eq 0 ] || set -- "$@" --dry-run
            [ "${purge}" -eq 0 ] || set -- "$@" --purge
            "${recovery_python}" "$@"
            exit $?
        fi
        if [ "${dry_run}" -eq 1 ] || [ "${print_plan}" -eq 1 ]; then
            say "Repair plan: reinstall the recorded exact package, then validate installer-owned state."
            exit 0
        fi
        recovery_manifest_url=$(json_get "${recovery_state}" manifest_url)
        recovery_manifest_sha=$(json_get "${recovery_state}" manifest_sha256)
        recovery_manifest=${tmp_root}/recovery-manifest.json
        download "${recovery_manifest_url}" "${recovery_manifest}" "${MAX_JSON_SIZE}"
        verify_sha "${recovery_manifest}" "${recovery_manifest_sha}"
        check_duplicate_keys "${recovery_manifest}"
        recovery_wheel_url=$(json_get "${recovery_manifest}" package.wheel.url)
        recovery_wheel_sha=$(json_get "${recovery_manifest}" package.wheel.sha256)
        recovery_wheel_size=$(json_get "${recovery_manifest}" package.wheel.size)
        recovery_wheel=${tmp_root}/recovery.whl
        download "${recovery_wheel_url}" "${recovery_wheel}" "${recovery_wheel_size}"
        verify_sha "${recovery_wheel}" "${recovery_wheel_sha}"
        PATH="${recovery_bin_dir}:${PATH}"
        export PATH
        if [ "${recovery_backend}" = uv ] && command -v uv >/dev/null 2>&1; then
            UV_TOOL_DIR="${recovery_install_dir}" UV_TOOL_BIN_DIR="${recovery_bin_dir}" \
                uv tool install --force --python 3.11 "${recovery_wheel}" ||
                fail 5 "uv could not repair the recorded Benchwork environment"
        elif [ "${recovery_backend}" = pipx ] && command -v pipx >/dev/null 2>&1; then
            PIPX_HOME="${recovery_install_dir}" PIPX_BIN_DIR="${recovery_bin_dir}" \
                pipx install --force "${recovery_wheel}" ||
                fail 5 "pipx could not repair the recorded Benchwork environment"
        else
            fail 5 "the recorded ${recovery_backend} backend is unavailable"
        fi
        bwork_existing=${recovery_bin_dir}/bwork
        recovered_cli=1
    fi
    if [ "${uninstall}" -eq 1 ]; then
        set -- install uninstall
        [ "${dry_run}" -eq 0 ] || set -- "$@" --dry-run
        [ "${purge}" -eq 0 ] || set -- "$@" --purge
    else
        if [ "${recovered_cli}" -eq 1 ]; then
            recovery_plugin_scope=$(json_get "${recovery_state}" plugin.scope)
            set -- install repair \
                --manifest "${recovery_manifest}" \
                --manifest-url "${recovery_manifest_url}" \
                --manifest-sha256 "${recovery_manifest_sha}" \
                --backend "${recovery_backend}" \
                --install-dir "${recovery_install_dir}" \
                --bin-dir "${recovery_bin_dir}" \
                --bwork-path "${bwork_existing}" \
                --plugin-scope "${recovery_plugin_scope}"
            recovery_bootstrapped=$(json_get "${recovery_state}" backend_bootstrapped)
            [ "${recovery_bootstrapped}" != true ] ||
                set -- "$@" --backend-bootstrapped
            if [ "${recovery_plugin_scope}" = project ]; then
                recovery_project_root=$(json_get "${recovery_state}" plugin.marketplace_path)
                set -- "$@" --project-root "${recovery_project_root}"
            fi
        else
            set -- install repair
        fi
        [ "${dry_run}" -eq 0 ] || set -- "$@" --dry-run
    fi
    "${bwork_existing}" "$@"
    exit $?
fi

manifest_file=${tmp_root}/release-manifest.json
manifest_url=
channel_file=${tmp_root}/channel.json
manifest_outer_sha=
if [ "${version_set}" -eq 1 ]; then
    if [ "${base_url}" = "${DEFAULT_BASE_URL}" ]; then
        manifest_url=${DEFAULT_GITHUB_RELEASES}/v${version}/release-manifest.json
    else
        manifest_url=${base_url%/}/releases/${version}/release-manifest.json
    fi
    download "${manifest_url}" "${manifest_file}" "${MAX_JSON_SIZE}"
else
    channel_url=${base_url%/}/channels/${channel}.json
    download "${channel_url}" "${channel_file}" "${MAX_JSON_SIZE}"
    check_duplicate_keys "${channel_file}"
    channel_schema=$(json_get "${channel_file}" schema_version)
    channel_name=$(json_get "${channel_file}" channel)
    [ "${channel_schema}" = benchwork-release-channel/1.0 ] ||
        fail 4 "unsupported release channel schema: ${channel_schema}"
    [ "${channel_name}" = "${channel}" ] ||
        fail 4 "release channel descriptor does not match request"
    version=$(json_get "${channel_file}" version)
    manifest_url=$(json_get "${channel_file}" manifest_url)
    manifest_outer_sha=$(json_get "${channel_file}" manifest_sha256)
    manifest_size=$(json_get "${channel_file}" manifest_size)
    require_uint "${manifest_size}" "channel manifest size"
    require_sha256 "${manifest_outer_sha}" "channel manifest checksum"
    [ "${manifest_size}" -le "${MAX_JSON_SIZE}" ] || fail 4 "channel manifest size is unsafe"
    download "${manifest_url}" "${manifest_file}" "${manifest_size}"
    verify_sha "${manifest_file}" "${manifest_outer_sha}"
fi
check_duplicate_keys "${manifest_file}"
manifest_sha=$(sha256 "${manifest_file}")

schema_version=$(json_get "${manifest_file}" schema_version)
manifest_version=$(json_get "${manifest_file}" version)
manifest_tag=$(json_get "${manifest_file}" tag)
manifest_channel=$(json_get "${manifest_file}" channel)
package_requirement=$(json_get "${manifest_file}" package.requirement)
wheel_url=$(json_get "${manifest_file}" package.wheel.url)
wheel_sha=$(json_get "${manifest_file}" package.wheel.sha256)
wheel_size=$(json_get "${manifest_file}" package.wheel.size)
python_requirement=$(json_get "${manifest_file}" python_requirement)
plugin_version=$(json_get "${manifest_file}" plugin.version)
plugin_runtime_requirement=$(json_get "${manifest_file}" plugin.runtime_requirement)
plugin_url=$(json_get "${manifest_file}" plugin.archive.url)
plugin_sha=$(json_get "${manifest_file}" plugin.archive.sha256)
plugin_size=$(json_get "${manifest_file}" plugin.archive.size)
uv_installer_url=$(json_get "${manifest_file}" bootstrap.uv.installer.url)
uv_installer_sha=$(json_get "${manifest_file}" bootstrap.uv.installer.sha256)
uv_installer_size=$(json_get "${manifest_file}" bootstrap.uv.installer.size)

validate_scalar "${version}" "resolved version"
case "${version}" in
    '' | *[!0-9A-Za-z.+-]*) fail 4 "resolved version contains unsupported characters" ;;
esac
for size_value in "${wheel_size}" "${plugin_size}" "${uv_installer_size}"; do
    require_uint "${size_value}" "artifact size"
done
for digest_value in "${wheel_sha}" "${plugin_sha}" "${uv_installer_sha}"; do
    require_sha256 "${digest_value}" "artifact checksum"
done
[ "${schema_version}" = benchwork-release-manifest/1.0 ] ||
    fail 4 "unsupported release manifest schema: ${schema_version}"
[ "${manifest_version}" = "${version}" ] || fail 4 "manifest version does not match request"
[ "${manifest_tag}" = "v${version}" ] || fail 4 "manifest tag does not match request"
[ "${package_requirement}" = "benchwork-arcana==${version}" ] ||
    fail 4 "manifest package requirement is not exact"
[ "${plugin_runtime_requirement}" = "${package_requirement}" ] ||
    fail 4 "plugin runtime requirement does not match the package"
expected_plugin_version=$(printf '%s' "${version}" |
    sed -e 's/rc\([0-9][0-9]*\)$/-rc.\1/' \
        -e 's/a\([0-9][0-9]*\)$/-alpha.\1/' \
        -e 's/b\([0-9][0-9]*\)$/-beta.\1/')
[ "${plugin_version}" = "${expected_plugin_version}" ] ||
    fail 4 "plugin version does not match the package version"
[ "${python_requirement}" = ">=3.11" ] || fail 4 "unsupported Python requirement"
[ "${wheel_size}" -le "${MAX_WHEEL_SIZE}" ] || fail 4 "wheel exceeds size limit"
case "${manifest_channel}" in
    rc) case "${version}" in *rc*) ;; *) fail 4 "RC manifest has a non-RC version" ;; esac ;;
    nightly) case "${version}" in *dev*) ;; *) fail 4 "nightly manifest has a non-nightly version" ;; esac ;;
    stable) case "${version}" in *rc* | *dev* | *a* | *b*) fail 4 "stable manifest is a prerelease" ;; esac ;;
    *) fail 4 "unknown manifest channel: ${manifest_channel}" ;;
esac
[ "${plugin_size}" -le "${MAX_PLUGIN_SIZE}" ] || fail 4 "plugin archive exceeds size limit"

if [ "${backend}" = auto ]; then
    if command -v uv >/dev/null 2>&1; then
        backend=uv
    elif command -v pipx >/dev/null 2>&1; then
        backend=pipx
    else
        backend=uv
    fi
fi

if [ -z "${bin_dir}" ]; then
    if [ "${backend}" = uv ] && command -v uv >/dev/null 2>&1; then
        bin_dir=$(uv tool dir --bin)
    elif [ "${backend}" = pipx ] && command -v pipx >/dev/null 2>&1; then
        bin_dir=$(pipx environment --value PIPX_BIN_DIR)
    else
        bin_dir=${HOME}/.local/bin
    fi
fi
absolute_path "${bin_dir}" "binary directory"

if [ -z "${install_dir}" ]; then
    if [ "${backend}" = uv ] && command -v uv >/dev/null 2>&1; then
        install_dir=$(uv tool dir)
    elif [ "${backend}" = pipx ] && command -v pipx >/dev/null 2>&1; then
        install_dir=$(pipx environment --value PIPX_HOME)
    else
        install_dir=${XDG_DATA_HOME:-${HOME}/.local/share}/${backend}/tools
    fi
fi
absolute_path "${install_dir}" "installation directory"
check_target_directory "${install_dir}"
check_target_directory "${bin_dir}"

state_file=${BENCHWORK_INSTALL_STATE:-${XDG_DATA_HOME:-${HOME}/.local/share}/benchwork/install-state.json}
previous_state=
previous_installed_version=
previous_backend=
previous_install_dir=
previous_bin_dir=
previous_manifest_url=
previous_manifest_sha=
already_healthy=0
plugin_request_satisfied=0
reuse_cli=0
install_request_satisfied=1
if [ -f "${state_file}" ]; then
    check_duplicate_keys "${state_file}"
    previous_state=${tmp_root}/previous-install-state.json
    cp "${state_file}" "${previous_state}"
    previous_installed_version=$(json_get "${previous_state}" installed_version)
    previous_backend=$(json_get "${previous_state}" backend)
    previous_install_dir=$(json_get "${previous_state}" install_dir)
    previous_bin_dir=$(json_get "${previous_state}" bin_dir)
    previous_manifest_url=$(json_get "${previous_state}" manifest_url)
    previous_manifest_sha=$(json_get "${previous_state}" manifest_sha256)
    if [ "${backend_explicit}" -eq 1 ] && [ "${backend}" != "${previous_backend}" ]; then
        install_request_satisfied=0
    fi
    if [ "${install_dir_explicit}" -eq 1 ] &&
        [ "${install_dir}" != "${previous_install_dir}" ]; then
        install_request_satisfied=0
    fi
    if [ "${bin_dir_explicit}" -eq 1 ] && [ "${bin_dir}" != "${previous_bin_dir}" ]; then
        install_request_satisfied=0
    fi
    recorded_plugin_scope=$(json_get "${previous_state}" plugin.scope)
    if [ "${plugin_scope}" = none ] || [ "${plugin_scope}" = "${recorded_plugin_scope}" ]; then
        plugin_request_satisfied=1
    fi
    if [ "${plugin_scope}" = project ]; then
        recorded_project_root=$(json_get "${previous_state}" plugin.marketplace_path)
        [ "${project_root}" = "${recorded_project_root}" ] || plugin_request_satisfied=0
    fi
    recorded_bwork=${previous_bin_dir}/bwork
    if [ "${previous_installed_version}" = "${version}" ] &&
        [ -x "${recorded_bwork}" ] &&
        [ "$("${recorded_bwork}" --version 2>/dev/null | awk '{print $NF}' || true)" = "${version}" ] &&
        "${recorded_bwork}" install doctor >/dev/null 2>&1 &&
        "${recorded_bwork}" plugin check >/dev/null 2>&1; then
        already_healthy=1
    fi
    if [ "${already_healthy}" -eq 1 ] && [ "${backend_explicit}" -eq 0 ] &&
        [ "${install_dir_explicit}" -eq 0 ] && [ "${bin_dir_explicit}" -eq 0 ]; then
        reuse_cli=1
        backend=${previous_backend}
        install_dir=${previous_install_dir}
        bin_dir=${previous_bin_dir}
    fi
fi

runtime_root=${XDG_RUNTIME_DIR:-${HOME}/.cache}/benchwork
if [ -d "${runtime_root}/install.lock" ]; then
    fail 2 "another Benchwork installer is active; remove ${runtime_root}/install.lock only if it is stale"
fi

downgrade=0
existing_bwork=$(command -v bwork 2>/dev/null || true)
if [ -n "${existing_bwork}" ]; then
    existing_owner_mode=$(owner_and_mode "${existing_bwork}")
    existing_owner=${existing_owner_mode%% *}
    [ "${existing_owner}" = "${current_uid}" ] ||
        fail 2 "existing bwork is not owned by the current user: ${existing_bwork}"
    existing_version=$("${existing_bwork}" --version 2>/dev/null | awk '{print $NF}' || true)
    if [ -n "${existing_version}" ] && [ "${existing_version}" != "${version}" ] &&
        version_is_newer "${existing_version}" "${version}"; then
        downgrade=1
    fi
fi

if [ "${current_uid}" -eq 0 ]; then
    if [ "${force}" -ne 1 ] || [ "${install_dir_explicit}" -ne 1 ] ||
        [ "${bin_dir_explicit}" -ne 1 ]; then
        fail 2 "root installation requires --force and explicit dedicated install/bin directories"
    fi
fi

if [ "${json_output}" -eq 1 ] && { [ "${dry_run}" -eq 1 ] || [ "${print_plan}" -eq 1 ]; }; then
    if [ "${json_parser}" = python3 ]; then
        python3 - "${version}" "${manifest_channel}" "${backend}" "${install_dir}" "${bin_dir}" \
            "${plugin_scope}" "${with_codex}" "${codex_detected}" "${with_claude}" \
            "${claude_detected}" "${modify_path}" "${git_detected}" <<'PY'
import json, sys
print(json.dumps({
    "schema_version": "benchwork-install-plan/1.0",
    "version": sys.argv[1],
    "channel": sys.argv[2],
    "backend": sys.argv[3],
    "install_dir": sys.argv[4],
    "bin_dir": sys.argv[5],
    "plugin_scope": sys.argv[6],
    "hosts": {
        "codex": {"requested": sys.argv[7] == "1", "detected": sys.argv[8] == "1"},
        "claude": {
            "requested": sys.argv[9] == "1",
            "detected": sys.argv[10] == "1",
            "support": "experimental_mcp_only",
        },
    },
    "modify_path": sys.argv[11] == "1",
    "git_detected": sys.argv[12] == "1",
    "project_state": "NOT_TOUCHED",
}, indent=2))
PY
    else
        jq -n \
            --arg version "${version}" --arg channel "${manifest_channel}" \
            --arg backend "${backend}" --arg install_dir "${install_dir}" \
            --arg bin_dir "${bin_dir}" --arg plugin_scope "${plugin_scope}" \
            --argjson codex_requested "${with_codex}" \
            --argjson codex_detected "${codex_detected}" \
            --argjson claude_requested "${with_claude}" \
            --argjson claude_detected "${claude_detected}" \
            --argjson modify_path "${modify_path}" \
            --argjson git_detected "${git_detected}" \
            '{schema_version:"benchwork-install-plan/1.0",version:$version,channel:$channel,backend:$backend,install_dir:$install_dir,bin_dir:$bin_dir,plugin_scope:$plugin_scope,hosts:{codex:{requested:($codex_requested==1),detected:($codex_detected==1)},claude:{requested:($claude_requested==1),detected:($claude_detected==1),support:"experimental_mcp_only"}},modify_path:($modify_path==1),git_detected:($git_detected==1),project_state:"NOT_TOUCHED"}'
    fi
elif [ "${json_output}" -eq 0 ]; then
    say "Benchwork installation plan"
    say "  Version: ${version} (${manifest_channel})"
    say "  Backend: ${backend}"
    say "  Requirement: ${package_requirement}"
    say "  Tool environment: ${install_dir}"
    say "  Binary: ${bin_dir}/bwork"
    say "  Codex: ${codex_detection}; ${codex_request}"
    say "  Claude: ${claude_detection}; ${claude_request}"
    say "  Plugin scope: ${plugin_scope}"
    if [ "${with_codex}" -eq 1 ]; then
        say "  May change: ${HOME}/.codex/config.toml (backup retained)"
    fi
    if [ "${with_claude}" -eq 1 ]; then
        say "  May change: ${HOME}/.claude.json (backup retained)"
    fi
    if [ "${modify_path}" -eq 1 ]; then
        say "  May change: one recognized shell profile (backup retained)"
    fi
    say "  Post-install: CLI resources, MCP startup, plugin, and requested Hosts"
    say "  Research state: NOT_TOUCHED"
    say "  Rollback: bwork install uninstall"
fi

if [ "${dry_run}" -eq 1 ] || [ "${print_plan}" -eq 1 ]; then
    exit 0
fi

if [ "${downgrade}" -eq 1 ] && [ "${version_set}" -ne 1 ]; then
    fail 3 "downgrade from ${existing_version} requires an exact --version"
fi
if [ "${downgrade}" -eq 1 ] && [ "${assume_yes}" -eq 0 ] && [ ! -t 0 ]; then
    fail 3 "downgrade from ${existing_version} to ${version} requires --yes or an interactive confirmation"
fi
if [ "${assume_yes}" -eq 0 ] && [ -t 0 ]; then
    if [ "${downgrade}" -eq 1 ]; then
        printf 'Downgrade Benchwork from %s to %s? [y/N] ' "${existing_version}" "${version}" >&2
    else
        printf 'Proceed with this installation? [y/N] ' >&2
    fi
    read -r answer
    case "${answer}" in y | Y | yes | YES) ;; *) fail 3 "installation cancelled" ;; esac
fi

if [ "${already_healthy}" -eq 1 ] && [ "${repair}" -eq 0 ] &&
    [ "${with_codex}" -eq 0 ] && [ "${with_claude}" -eq 0 ] &&
    [ "${modify_path}" -eq 0 ] && [ "${plugin_request_satisfied}" -eq 1 ] &&
    [ "${install_request_satisfied}" -eq 1 ]; then
    healthy_path_action=
    healthy_resolved=$(command -v bwork 2>/dev/null || true)
    if [ "${healthy_resolved}" != "${recorded_bwork}" ]; then
        healthy_quoted_bin=$(shell_quote "${previous_bin_dir}")
        healthy_path_action="export PATH=${healthy_quoted_bin}:\"\$PATH\""
    fi
    if [ "${json_output}" -eq 1 ]; then
        if [ "${json_parser}" = python3 ]; then
            python3 - "${version}" "${previous_backend}" "${recorded_bwork}" \
                "${healthy_path_action}" <<'PY'
import json, sys
print(json.dumps({
    "ok": True,
    "already_healthy": True,
    "version": sys.argv[1],
    "backend": sys.argv[2],
    "bwork_path": sys.argv[3],
    "path_action": sys.argv[4] or None,
    "cli": "PASS",
    "mcp_server": "PASS",
    "project_state": "NOT_TOUCHED",
    "rollback": "bwork install uninstall",
}, indent=2))
PY
        else
            jq -n --arg version "${version}" --arg backend "${previous_backend}" \
                --arg bwork_path "${recorded_bwork}" \
                --arg path_action "${healthy_path_action}" \
                '{ok:true,already_healthy:true,version:$version,backend:$backend,bwork_path:$bwork_path,path_action:(if $path_action=="" then null else $path_action end),cli:"PASS",mcp_server:"PASS",project_state:"NOT_TOUCHED",rollback:"bwork install uninstall"}'
        fi
    else
        say "Benchwork ${version} is already healthy; no changes were made."
        if [ -n "${healthy_path_action}" ]; then
            say "PATH action: run ${healthy_path_action}"
        fi
        say "Rollback: bwork install uninstall"
    fi
    exit 0
fi

mkdir -p "${runtime_root}"
lock_dir=${runtime_root}/install.lock
if ! mkdir "${lock_dir}" 2>/dev/null; then
    fail 2 "another Benchwork installer is active; remove ${lock_dir} only if it is stale"
fi
printf '%s\n' "$$" >"${lock_dir}/pid"

backend_bootstrapped=0
wheel_path=${tmp_root}/benchwork.whl
if [ "${reuse_cli}" -eq 0 ]; then
    download "${wheel_url}" "${wheel_path}" "${wheel_size}"
    verify_sha "${wheel_path}" "${wheel_sha}"
fi

restore_previous_state() {
    [ -n "${previous_state}" ] || return 1
    state_parent=${state_file%/*}
    mkdir -p "${state_parent}"
    state_temporary=${state_parent}/.rollback-state-$$
    cp "${previous_state}" "${state_temporary}"
    mv "${state_temporary}" "${state_file}"
    previous_plugin_scope=$(json_get "${previous_state}" plugin.scope)
    if [ "${previous_plugin_scope}" != none ]; then
        previous_plugin_path=$(json_get "${previous_state}" plugin.path)
        plugin_parent=${previous_plugin_path%/*}
        pointer=${plugin_parent}/.rollback-current-$$
        ln -s "${previous_plugin_path##*/}" "${pointer}"
        rm -f "${plugin_parent}/current"
        mv "${pointer}" "${plugin_parent}/current"
    fi
    return 0
}

rollback_previous_installation() {
    [ -n "${previous_state}" ] && [ -n "${previous_installed_version}" ] || return 1
    say "Rolling back to Benchwork ${previous_installed_version}"
    old_manifest=${tmp_root}/rollback-manifest.json
    download "${previous_manifest_url}" "${old_manifest}" "${MAX_JSON_SIZE}"
    verify_sha "${old_manifest}" "${previous_manifest_sha}"
    check_duplicate_keys "${old_manifest}"
    old_wheel_url=$(json_get "${old_manifest}" package.wheel.url)
    old_wheel_sha=$(json_get "${old_manifest}" package.wheel.sha256)
    old_wheel_size=$(json_get "${old_manifest}" package.wheel.size)
    old_wheel=${tmp_root}/rollback.whl
    download "${old_wheel_url}" "${old_wheel}" "${old_wheel_size}"
    verify_sha "${old_wheel}" "${old_wheel_sha}"
    if [ "${previous_backend}" = uv ] && command -v uv >/dev/null 2>&1; then
        UV_TOOL_DIR="${previous_install_dir}" UV_TOOL_BIN_DIR="${previous_bin_dir}" \
            uv tool install --force --python 3.11 "${old_wheel}" || return 1
    elif [ "${previous_backend}" = pipx ] && command -v pipx >/dev/null 2>&1; then
        PIPX_HOME="${previous_install_dir}" PIPX_BIN_DIR="${previous_bin_dir}" \
            pipx install --force "${old_wheel}" || return 1
    else
        return 1
    fi
    restore_previous_state
}

remove_failed_new_installation() {
    if [ "${backend}" = uv ] && command -v uv >/dev/null 2>&1; then
        UV_TOOL_DIR="${install_dir}" UV_TOOL_BIN_DIR="${bin_dir}" \
            uv tool uninstall benchwork-arcana >/dev/null 2>&1 || true
    elif [ "${backend}" = pipx ] && command -v pipx >/dev/null 2>&1; then
        PIPX_HOME="${install_dir}" PIPX_BIN_DIR="${bin_dir}" \
            pipx uninstall benchwork-arcana >/dev/null 2>&1 || true
    fi
    if [ "${plugin_scope}" = user ]; then
        failed_plugin_base=${XDG_DATA_HOME:-${HOME}/.local/share}/benchwork/plugins
    elif [ "${plugin_scope}" = project ]; then
        failed_plugin_base=${project_root}/.agents/benchwork-installer/plugins
    else
        failed_plugin_base=
    fi
    if [ -n "${failed_plugin_base}" ]; then
        rm -r "${failed_plugin_base:?}/${plugin_version}" 2>/dev/null || true
        if [ -L "${failed_plugin_base}/current" ]; then
            rm "${failed_plugin_base}/current"
        fi
    fi
    rm "${state_file}" 2>/dev/null || true
}

recover_after_failure() {
    if [ -n "${previous_state}" ]; then
        if [ "${reuse_cli}" -eq 1 ]; then
            restore_previous_state
        else
            rollback_previous_installation
        fi
    else
        remove_failed_new_installation
    fi
}

if [ "${reuse_cli}" -eq 1 ]; then
    say "Reusing the healthy Benchwork ${version} CLI environment."
elif [ "${backend}" = uv ]; then
    if ! command -v uv >/dev/null 2>&1; then
        [ "${no_bootstrap_uv}" -eq 0 ] ||
            fail 5 "uv is absent and BENCHWORK_NO_BOOTSTRAP_UV=1; install uv or select pipx"
        uv_script=${tmp_root}/uv-install.sh
        download "${uv_installer_url}" "${uv_script}" "${uv_installer_size}"
        verify_sha "${uv_script}" "${uv_installer_sha}"
        say "Installing the release-pinned uv bootstrap into ${bin_dir}"
        UV_NO_MODIFY_PATH=1 UV_INSTALL_DIR="${bin_dir}" sh "${uv_script}" >&2
        backend_bootstrapped=1
        PATH="${bin_dir}:${PATH}"
        export PATH
    fi
    command -v uv >/dev/null 2>&1 || fail 5 "uv bootstrap did not expose uv"
    say "Installing ${package_requirement} with uv"
    UV_TOOL_DIR="${install_dir}" UV_TOOL_BIN_DIR="${bin_dir}" \
        uv tool install --force --python 3.11 "${wheel_path}" >&2 ||
        fail 5 "uv could not install the exact Benchwork package"
else
    command -v pipx >/dev/null 2>&1 ||
        fail 5 "pipx is not installed; install pipx safely or select the uv backend"
    python_executable=
    for candidate in python3.14 python3.13 python3.12 python3.11 python3; do
        if command -v "${candidate}" >/dev/null 2>&1 &&
            "${candidate}" -c 'import sys; raise SystemExit(sys.version_info < (3, 11))'; then
            python_executable=$(command -v "${candidate}")
            break
        fi
    done
    [ -n "${python_executable}" ] ||
        fail 5 "pipx requires an existing Python 3.11 or newer; select uv to bootstrap Python"
    say "Installing ${package_requirement} with pipx"
    PIPX_HOME="${install_dir}" PIPX_BIN_DIR="${bin_dir}" \
        pipx install --force --python "${python_executable}" "${wheel_path}" >&2 ||
        fail 5 "pipx could not install the exact Benchwork package"
fi

bwork_path=${bin_dir}/bwork
[ -x "${bwork_path}" ] || fail 5 "installed bwork is missing from ${bin_dir}"
installed_version=$("${bwork_path}" --version | awk '{print $NF}')
[ "${installed_version}" = "${version}" ] ||
    fail 4 "installed CLI version ${installed_version} does not match ${version}"
"${bwork_path}" --help >/dev/null
"${bwork_path}" mcp --help >/dev/null
[ ! -e .benchwork ] ||
    verbose "Existing .benchwork directory was present and was not used by installation checks."

plugin_archive=
if [ "${plugin_scope}" != none ]; then
    plugin_archive=${tmp_root}/benchwork-plugin.tar.gz
    download "${plugin_url}" "${plugin_archive}" "${plugin_size}"
    verify_sha "${plugin_archive}" "${plugin_sha}"
fi

set -- install repair \
    --manifest "${manifest_file}" \
    --manifest-url "${manifest_url}" \
    --manifest-sha256 "${manifest_sha}" \
    --backend "${backend}" \
    --install-dir "${install_dir}" \
    --bin-dir "${bin_dir}" \
    --bwork-path "${bwork_path}" \
    --plugin-scope "${plugin_scope}"
[ "${backend_bootstrapped}" -eq 0 ] || set -- "$@" --backend-bootstrapped
[ -z "${plugin_archive}" ] || set -- "$@" --plugin-archive "${plugin_archive}"
[ -z "${project_root}" ] || set -- "$@" --project-root "${project_root}"
[ "${with_codex}" -eq 0 ] || set -- "$@" --with-codex
[ "${with_claude}" -eq 0 ] || set -- "$@" --with-claude
[ "${modify_path}" -eq 0 ] || set -- "$@" --modify-path
[ "${force}" -eq 0 ] || set -- "$@" --force
configuration_result=${tmp_root}/configuration-result.json
if ! "${bwork_path}" "$@" >"${configuration_result}"; then
    recover_after_failure ||
        fail 7 "configuration failed and automatic rollback was not possible; inspect ${state_file}"
    fail 6 "structured Benchwork configuration failed; installer changes were rolled back"
fi

doctor_status=0
"${bwork_path}" install doctor >/dev/null || doctor_status=$?
if [ "${doctor_status}" -ne 0 ]; then
    recover_after_failure ||
        fail 7 "verification failed and automatic rollback was not possible; inspect ${state_file}"
    fail 4 "final installation verification failed; installer changes were rolled back"
fi

codex_mcp=NOT_CONFIGURED
codex_plugin=NOT_CONFIGURED
claude_mcp=NOT_CONFIGURED
path_action=
resolved_bwork=$(command -v bwork 2>/dev/null || true)
if [ "${resolved_bwork}" != "${bwork_path}" ]; then
    quoted_bin=$(shell_quote "${bin_dir}")
    path_action="export PATH=${quoted_bin}:\"\$PATH\""
fi
if [ "${with_codex}" -eq 1 ]; then
    codex_mcp_state=$(json_get "${configuration_result}" hosts.codex.mcp)
    codex_plugin_state=$(json_get "${configuration_result}" hosts.codex.plugin)
    case "${codex_mcp_state}" in
        configured | plugin_managed) codex_mcp=PASS ;;
        *) codex_mcp=BLOCKED ;;
    esac
    case "${codex_plugin_state}" in
        configured) codex_plugin=PASS ;;
        unsupported | known_upstream_limitation) codex_plugin=KNOWN_UPSTREAM_LIMITATION ;;
        *) codex_plugin=NOT_CONFIGURED ;;
    esac
fi
if [ "${with_claude}" -eq 1 ]; then
    claude_mcp_state=$(json_get "${configuration_result}" hosts.claude.mcp)
    case "${claude_mcp_state}" in
        experimental) claude_mcp=EXPERIMENTAL ;;
        *) claude_mcp=BLOCKED ;;
    esac
fi

if [ "${json_output}" -eq 1 ]; then
    if [ "${json_parser}" = python3 ]; then
        python3 - "${version}" "${backend}" "${bwork_path}" "${codex_mcp}" \
            "${codex_plugin}" "${claude_mcp}" "${path_action}" <<'PY'
import json, sys
print(json.dumps({
    "ok": True,
    "version": sys.argv[1],
    "backend": sys.argv[2],
    "bwork_path": sys.argv[3],
    "cli": "PASS",
    "mcp_server": "PASS",
    "codex_mcp": sys.argv[4],
    "codex_plugin": sys.argv[5],
    "claude_mcp": sys.argv[6],
    "path_action": sys.argv[7] or None,
    "project_state": "NOT_TOUCHED",
    "rollback": "bwork install uninstall",
}, indent=2))
PY
    else
        jq -n --arg version "${version}" --arg backend "${backend}" \
            --arg bwork_path "${bwork_path}" --arg codex_mcp "${codex_mcp}" \
            --arg codex_plugin "${codex_plugin}" --arg claude_mcp "${claude_mcp}" \
            --arg path_action "${path_action}" \
            '{ok:true,version:$version,backend:$backend,bwork_path:$bwork_path,cli:"PASS",mcp_server:"PASS",codex_mcp:$codex_mcp,codex_plugin:$codex_plugin,claude_mcp:$claude_mcp,path_action:(if $path_action=="" then null else $path_action end),project_state:"NOT_TOUCHED",rollback:"bwork install uninstall"}'
    fi
else
    say ""
    say "Benchwork ${version} installed"
    say "  CLI: PASS (${bwork_path})"
    say "  MCP server: PASS"
    say "  Codex MCP: ${codex_mcp}"
    say "  Codex Plugin: ${codex_plugin}"
    say "  Claude MCP: ${claude_mcp}"
    say "  Project state: NOT_TOUCHED"
    if [ -n "${path_action}" ]; then
        say "  PATH action: run ${path_action}"
    fi
    say ""
    say "Next: restart configured Hosts, then run bwork install doctor."
    say "Rollback: bwork install uninstall"
fi
