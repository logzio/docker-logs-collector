# syntax=docker/dockerfile:1

FROM python:3.12.4-slim-bullseye AS base

# Install dependencies using apt-get
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    bash \
    libyaml-dev \
    libsystemd-dev \
    libsasl2-dev \
    libpq-dev \
    openssl \
    libssl-dev \
    gdb \
    && rm -rf /var/lib/apt/lists/*

# Define build argument for architecture
ARG TARGETARCH

# Set the plugin URL based on the architecture
ENV LOGZIO_PLUGIN_URL_AMD64=https://github.com/logzio/fluent-bit-logzio-output/raw/master/build/out_logzio-linux.so
ENV LOGZIO_PLUGIN_URL_ARM64=https://github.com/logzio/fluent-bit-logzio-output/raw/master/build/out_logzio-linux-arm64.so

# Determine the correct plugin URL based on TARGETARCH
RUN mkdir -p /fluent-bit/plugins && \
    if [ "$TARGETARCH" = "amd64" ]; then \
        export LOGZIO_PLUGIN_URL=$LOGZIO_PLUGIN_URL_AMD64; \
    elif [ "$TARGETARCH" = "arm64" ]; then \
        export LOGZIO_PLUGIN_URL=$LOGZIO_PLUGIN_URL_ARM64; \
    else \
        echo "Unsupported architecture: $TARGETARCH"; exit 1; \
    fi && \
    wget -O /fluent-bit/plugins/out_logzio.so $LOGZIO_PLUGIN_URL

# Set working directory
WORKDIR /opt/fluent-bit

# Copy configuration files and Lua script
COPY configs/parser_multiline.conf /fluent-bit/etc/parsers_multiline.conf
COPY configs/parsers.conf /fluent-bit/etc/parsers.conf
COPY configs/plugins.conf /fluent-bit/etc/plugins.conf
COPY docker-metadata.lua /fluent-bit/etc/docker-metadata.lua
COPY create_fluent_bit_config.py /opt/fluent-bit/docker-collector-logs/create_fluent_bit_config.py

# Use official Fluent Bit image for Fluent Bit binaries
FROM fluent/fluent-bit:1.9.10 AS fluent-bit

# Copy Fluent Bit binary to the base image
FROM base
COPY --from=fluent-bit /fluent-bit/bin/fluent-bit /usr/local/bin/fluent-bit

# Copy entrypoint script
COPY start.sh /start.sh
RUN chmod +x /start.sh

# Set the entrypoint to run the shell script
ENTRYPOINT ["/start.sh"]
