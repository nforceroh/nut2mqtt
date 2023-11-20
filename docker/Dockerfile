FROM python:3.12-alpine
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION
ARG	BASE_IMAGE

LABEL \
  org.label-schema.build-date=$BUILD_DATE \
  org.label-schema.name="k3s-nut2influxdb" \
  org.label-schema.description="nut2influxdb docker container on alpine linux" \
  org.label-schema.url="https://github.com/nforceroh/nut2influxdb" \
  org.label-schema.vcs-ref=$VCS_REF \
  org.label-schema.vcs-url="https://github.com/nforceroh/nut2influxdb" \
  org.label-schema.vendor="nforceroh" \
  org.label-schema.version=$VERSION \
  org.label-schema.schema-version="1.0"

ENV PYTHONUNBUFFERED=true

WORKDIR /app
COPY src/* /app
RUN pip install --no-cache-dir -r requirements.txt

CMD [ "python", "/app/app.py" ]