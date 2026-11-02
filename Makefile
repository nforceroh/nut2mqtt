# Local build and test only — CI is the sole publisher.
# Shared pipelines: https://github.com/nforceroh/.github
SHELL := /bin/bash
IMAGE ?= ghcr.io/nforceroh/nut2mqtt
TAG   ?= dev

.PHONY: build test run

build:
	docker build \
		--build-arg BUILD_DATE="$(shell date -u +'%Y-%m-%dT%H:%M:%SZ')" \
		--build-arg VERSION="$(TAG)" \
		--tag $(IMAGE):$(TAG) .

test: build
	./tests/run_tests.sh "$(IMAGE):$(TAG)"

# No published ports: nut2mqtt is an outbound-only MQTT publisher.
run: build
	docker run --rm -it \
		--env-file .env \
		$(IMAGE):$(TAG)
