FROM python:3.12-alpine

ARG \
  BUILD_DATE=now \
  VERSION=unknown

LABEL \
  org.label-schema.maintainer="Sylvain Martin (sylvain@nforcer.com)" \
  org.label-schema.build-date="${BUILD_DATE}" \
  org.label-schema.version="${VERSION}" \
  org.label-schema.vcs-url="https://github.com/nforceroh/nut2mqtt" \
  org.label-schema.vcs-ref="${VERSION}" \
  org.label-schema.schema-version="1.0"

ENV \
  PYTHONUNBUFFERED=true \
  MQTT_PUB_ROOT=UPS \
  MQTT_HOST=localhost \
  MQTT_PORT=1883 \
  MQTT_USER="" \
  MQTT_PASS="" \
  MQTT_KEEPALIVE=60 \
  NUT_HOST="" \
  NUT_PORT=3493 \
  NUT_USER="" \
  NUT_PASS="" \
  NUT_INTR=30 \
  DEBUG=False

### Install Dependencies
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt \
  && rm -f /tmp/requirements.txt

### Add Files
COPY content/app /app

CMD [ "python", "-u", "/app/nut2mqtt/main.py" ]
