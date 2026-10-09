# TAP control plane image (multi-stage, non-root).
FROM python:3.12-slim AS builder

WORKDIR /build
COPY pyproject.toml README.md* ./
COPY tap_platform ./tap_platform
RUN pip install --no-cache-dir --prefix=/install .

FROM python:3.12-slim

LABEL org.opencontainers.image.title="tap-platform" \
      org.opencontainers.image.description="Terraform Agent Platform control plane" \
      org.opencontainers.image.licenses="Apache-2.0"

RUN useradd --uid 65532 --no-create-home --shell /usr/sbin/nologin tap
COPY --from=builder /install /usr/local
COPY config /etc/tap/config

USER 65532
EXPOSE 8080

# Health: GET /healthz
ENTRYPOINT ["tap-server"]
CMD ["--config", "/etc/tap/config/dev.yaml"]
