FROM python:3.12-alpine
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION
ARG	BASE_IMAGE

LABEL \
  org.label-schema.build-date=$BUILD_DATE \
  org.label-schema.name="k3s-nut2mqtt" \
  org.label-schema.description="nut2mqtt docker container on alpine linux" \
  org.label-schema.url="https://github.com/nforceroh/nut2influxdb" \
  org.label-schema.vcs-ref=$VCS_REF \
  org.label-schema.vcs-url="https://github.com/nforceroh/nut2influxdb" \
  org.label-schema.vendor="nforceroh" \
  org.label-schema.version=$VERSION \
  org.label-schema.schema-version="1.0"

ENV PYTHONUNBUFFERED=true

WORKDIR /app
COPY src/ /app/
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

CMD [ "python", "/app/main.py" ]