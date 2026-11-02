#!/usr/bin/env bash
# Smoke tests for nforceroh/nut2mqtt. Pass an image reference as $1.
set -uo pipefail

IMAGE="${1:-ghcr.io/nforceroh/nut2mqtt:dev}"
export IMAGE
PASS=0
FAIL=0
SETTLE_SECONDS="${SETTLE_SECONDS:-15}"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

check() {
	local label="$1"; shift
	if "$@" >/dev/null 2>&1; then
		echo -e "  ${GREEN}PASS${NC}  ${label}"
		PASS=$((PASS + 1))
	else
		echo -e "  ${RED}FAIL${NC}  ${label}"
		FAIL=$((FAIL + 1))
	fi
}

# Runs a command inside the image with the entrypoint bypassed. Use for static
# checks that must not depend on the service having started.
in_image() { docker run --rm --entrypoint sh "$IMAGE" -c "$1"; }

# Runs the image with the real entrypoint, lets it settle, and greps its logs.
# The container is started detached and its logs read afterwards: the service
# under test never exits on its own, and piping a long-running `docker run`
# into `grep -q` trips pipefail with SIGPIPE (141) even when grep matched.
check_output() {
	# Call as: check_output "label" "pattern" [docker opts...] -- <command...>
	local label="$1"; local pattern="$2"; shift 2
	local opts="" cmd="" seen_sep=0
	for arg in "$@"; do
		if [ "$arg" = "--" ]; then seen_sep=1; continue; fi
		if [ "$seen_sep" -eq 1 ]; then cmd="$cmd $arg"; else opts="$opts $arg"; fi
	done
	local name="out-$$-$RANDOM" out
	# shellcheck disable=SC2086
	docker run -d --name "$name" $opts "$IMAGE" $cmd >/dev/null 2>&1
	sleep "${CHECK_SETTLE_SECONDS:-8}"
	out=$(docker logs "$name" 2>&1)
	docker rm -f "$name" >/dev/null 2>&1
	if grep -qE -- "$pattern" <<<"$out"; then
		echo -e "  ${GREEN}PASS${NC}  ${label}"
		PASS=$((PASS + 1))
	else
		echo -e "  ${RED}FAIL${NC}  ${label}"
		FAIL=$((FAIL + 1))
	fi
}

echo -e "${YELLOW}== nforceroh/nut2mqtt ==${NC}"
echo "  image: ${IMAGE}"

if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
	echo -e "${RED}image ${IMAGE} not found — build it first (make build)${NC}"
	exit 1
fi

# --- static filesystem checks (need no external services) -------------------
check "application module present" in_image 'test -f /app/nut2mqtt/main.py'
check "python3 present" in_image 'command -v python3'
check "python is 3.12" in_image 'python3 -c "import sys; sys.exit(0 if sys.version_info[:2] == (3, 12) else 1)"'
check "paho-mqtt importable" in_image 'python3 -c "import paho.mqtt.client"'
check "nut2 importable" in_image 'python3 -c "from nut2 import PyNUTClient"'
check "application module compiles" in_image 'python3 -m py_compile /app/nut2mqtt/main.py'

# --- default environment ----------------------------------------------------
check "MQTT_PUB_ROOT default" in_image 'test "$MQTT_PUB_ROOT" = UPS'
check "MQTT_PORT default" in_image 'test "$MQTT_PORT" = 1883'
check "NUT_PORT default" in_image 'test "$NUT_PORT" = 3493'
check "NUT_INTR default" in_image 'test "$NUT_INTR" = 30'

# --- runtime behaviour ------------------------------------------------------
# With no reachable NUT server the service must log the failure and keep
# retrying rather than exiting — that is the whole point of the retry loop.
check_output "logs NUT connection failure" \
	"Can't connect to NUT host" \
	-e NUT_HOST=127.0.0.1 -e NUT_INTR=2 -- python3 -u /app/nut2mqtt/main.py

# --- boot check -------------------------------------------------------------
# The service needs a reachable NUT server, so still running after the settle
# window counts as success. A crash does not. The container is started detached
# because `timeout docker run` cannot reliably terminate a container whose main
# process ignores SIGTERM (podman in particular waits on its supervisor rather
# than the process).
echo
echo "  booting for ${SETTLE_SECONDS}s (still running afterwards is expected)"
BOOT_NAME="smoke-$$-$RANDOM"
docker run -d --name "$BOOT_NAME" -e NUT_HOST=127.0.0.1 -e NUT_INTR=2 "$IMAGE" >/dev/null 2>&1
sleep "$SETTLE_SECONDS"
BOOT_STATE=$(docker inspect --format '{{.State.Status}}:{{.State.ExitCode}}' "$BOOT_NAME" 2>/dev/null)
docker rm -f "$BOOT_NAME" >/dev/null 2>&1

case "$BOOT_STATE" in
	running:*)
		echo -e "  ${GREEN}PASS${NC}  still running after ${SETTLE_SECONDS}s"
		PASS=$((PASS + 1))
		;;
	exited:0)
		echo -e "  ${GREEN}PASS${NC}  exited cleanly"
		PASS=$((PASS + 1))
		;;
	*)
		echo -e "  ${RED}FAIL${NC}  boot state ${BOOT_STATE:-unknown}"
		FAIL=$((FAIL + 1))
		;;
esac


echo
if [ "${FAIL}" -gt 0 ]; then
	echo -e "${RED}${FAIL} failed${NC}, ${PASS} passed"
	exit 1
fi
echo -e "${GREEN}all ${PASS} checks passed${NC}"
