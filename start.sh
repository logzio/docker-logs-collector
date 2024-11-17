#!/bin/bash
set -e  # Exit immediately if a command exits with a non-zero status

# Run the Python script to generate the Fluent Bit configuration files
python3 /opt/fluent-bit/docker-collector-logs/create_fluent_bit_config.py

# Start Fluent Bit using the generated configuration
exec /usr/local/bin/fluent-bit -e /fluent-bit/plugins/out_logzio.so -c /fluent-bit/etc/fluent-bit.conf -vv
