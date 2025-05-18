# syntax=docker/dockerfile:1

FROM python:3.12-slim-bookworm AS base

# Install dependencies using apt-get
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    libyaml-dev \
    libsystemd-dev \
    libsasl2-dev \
    libpq-dev \
    openssl \
    libssl-dev \
    gdb \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Define build argument for architecture
ARG TARGETARCH

# Define the base URL for your plugin's GitHub releases
ENV GITHUB_REPO_URL=https://github.com/logzio/fluent-bit-logzio-output
# Define the specific asset names as they appear in your GitHub Release
ENV LOGZIO_PLUGIN_ASSET_AMD64=out_logzio-linux-amd64.so
ENV LOGZIO_PLUGIN_ASSET_ARM64=out_logzio-linux-arm64.so

# Determine the correct plugin URL and download
RUN mkdir -p /fluent-bit/plugins && \
    PLUGIN_DOWNLOAD_URL="" && \
    if [ "$TARGETARCH" = "amd64" ]; then \
        PLUGIN_DOWNLOAD_URL="${GITHUB_REPO_URL}/releases/latest/download/${LOGZIO_PLUGIN_ASSET_AMD64}"; \
    elif [ "$TARGETARCH" = "arm64" ]; then \
        PLUGIN_DOWNLOAD_URL="${GITHUB_REPO_URL}/releases/latest/download/${LOGZIO_PLUGIN_ASSET_ARM64}"; \
    else \
        echo "Unsupported architecture: $TARGETARCH"; exit 1; \
    fi && \
    echo "Downloading plugin from: $PLUGIN_DOWNLOAD_URL" && \
    # Using curl -L to follow redirects (important for /latest/) and -o to output to file
    curl -fsSL -o /fluent-bit/plugins/out_logzio.so "$PLUGIN_DOWNLOAD_URL" && \
    if [ ! -s /fluent-bit/plugins/out_logzio.so ]; then echo "Error: Downloaded plugin is empty or failed."; exit 1; fi

# Set working directory
WORKDIR /opt/fluent-bit

# Copy configuration files and Lua script
COPY configs/parser_multiline.conf /fluent-bit/etc/parsers_multiline.conf
COPY configs/parsers.conf /fluent-bit/etc/parsers.conf
COPY configs/plugins.conf /fluent-bit/etc/plugins.conf
COPY docker-metadata.lua /fluent-bit/etc/docker-metadata.lua
COPY create_fluent_bit_config.py /opt/fluent-bit/docker-collector-logs/create_fluent_bit_config.py

# Use official Fluent Bit image for Fluent Bit binaries
FROM fluent/fluent-bit:3.2.2 AS fluent-bit

# Copy Fluent Bit binary to the base image
FROM base
COPY --from=fluent-bit /fluent-bit/bin/fluent-bit /usr/local/bin/fluent-bit

# Copy entrypoint script
COPY start.sh /start.sh
RUN chmod +x /start.sh

# Set the entrypoint to run the shell script
ENTRYPOINT ["/start.sh"]
