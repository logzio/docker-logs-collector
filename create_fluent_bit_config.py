import os

# Function to create the Fluent Bit configuration
def create_fluent_bit_config():
    # Get log level from environment variable
    log_level = os.getenv('LOG_LEVEL', 'info')

    # Base configuration for Fluent Bit SERVICE and INPUT sections
    config = f"""
[SERVICE]
    Parsers_File parsers.conf
    Parsers_File parsers_multiline.conf
    Flush        1
    Daemon       Off
    Log_Level    {log_level}
"""

    # Add multiline parser configuration if specified
    if os.getenv('MULTILINE_START_STATE_RULE'):
        config += f"""
[INPUT]
    Name         tail
    Path         /var/lib/docker/containers/*/*.log
    Parser       docker
    Tag          docker.*
    read_from_head {os.getenv('READ_FROM_HEAD', 'true')}
    multiline.parser multiline-regex
"""
    else:
        config += """
[INPUT]
    Name         tail
    Path         /var/lib/docker/containers/*/*.log
    Parser       docker
    Tag          docker.*
"""
    # Add ignore_older if specified
    ignore_older = os.getenv('IGNORE_OLDER', '')
    if ignore_older:
        config += f"    ignore_older {ignore_older}\n"

    # Add LUA filter for enrichment with Docker metadata
    config += """
[FILTER]
    Name         lua
    Match        docker.*
    script       /fluent-bit/etc/docker-metadata.lua
    call         enrich_with_docker_metadata
"""

    # Check for container names or image names to include or exclude
    match_container_name = os.getenv('MATCH_CONTAINER_NAME', '')
    skip_container_names = os.getenv('SKIP_CONTAINER_NAMES', '')
    match_image_name = os.getenv('MATCH_IMAGE_NAME', '')
    skip_image_names = os.getenv('SKIP_IMAGE_NAMES', '')
    include_line = os.getenv('INCLUDE_LINE', '')
    exclude_lines = os.getenv('EXCLUDE_LINES', '')

    # Ensure that both match and skip are not set for containers and images
    if match_container_name and skip_container_names:
        raise ValueError("Cannot use both matchContainerName and skipContainerName")

    if match_image_name and skip_image_names:
        raise ValueError("Cannot use both matchImageName and skipImageName")

    # Ensure that both include and exclude lines are not set at the same time
    if include_line and exclude_lines:
        raise ValueError("Cannot use both includeLines and excludeLines")

    # Add filter for matching container names
    if match_container_name:
        config += """
[FILTER]
    Name         nest
    Match        *
    Operation    lift
    Nested_under _source
"""
        config += """
[FILTER]
    Name    grep
    Match   *
"""
        config += f"    Regex docker_container_name {match_container_name.strip()}\n"

    # Add filter for skipping container names
    if skip_container_names:
        config += """
[FILTER]
    Name         nest
    Match        *
    Operation    lift
    Nested_under _source
"""
        names = skip_container_names.split(',')
        config += """
[FILTER]
    Name    grep
    Match   *
"""
        for name in names:
            config += f"    Exclude docker_container_name {name.strip()}\n"

    # Add filter for matching image names (single match)
    if match_image_name:
        config += """
[FILTER]
    Name         nest
    Match        *
    Operation    lift
    Nested_under _source
"""
        config += """
[FILTER]
    Name    grep
    Match   *
"""
        config += f"    Regex docker_container_image {match_image_name.strip()}\n"

    # Add filter for skipping image names
    if skip_image_names:
        config += """
[FILTER]
    Name         nest
    Match        *
    Operation    lift
    Nested_under _source
"""
        images = skip_image_names.split(',')
        config += """
[FILTER]
    Name    grep
    Match   *
"""
        for image in images:
            config += f"    Exclude docker_container_image {image.strip()}\n"

    # Add filter for including lines based on message content (single include line)
    if include_line:
        config += """
[FILTER]
    Name    grep
    Match   *
"""
        config += f"    Regex message {include_line.strip()}\n"

    # Add filter for excluding lines based on message content (multiple exclude lines)
    if exclude_lines:
        lines = exclude_lines.split(',')
        config += """
[FILTER]
    Name    grep
    Match   *
"""
        for line in lines:
            config += f"    Exclude message {line.strip()}\n"

    # Add additional fields specified as environment variables
    additional_fields = os.getenv('ADDITIONAL_FIELDS', '')
    if additional_fields:
        fields = additional_fields.split(',')
        config += """
[FILTER]
    Name modify
    Match *
"""
        for field in fields:
            key, value = field.split(':')
            config += f"    Add {key.strip()} {value.strip()}\n"

    # Add set fields specified as environment variables
    set_fields = os.getenv('SET_FIELDS', '')
    if set_fields:
        fields = set_fields.split(',')
        config += """
[FILTER]
    Name modify
    Match *
"""
        for field in fields:
            key, value = field.split(':')
            config += f"    Set {key.strip()} {value.strip()}\n"

    # Add the OUTPUT section to send logs to Logz.io
    logzio_logs_token = os.getenv('LOGZIO_LOGS_TOKEN', 'your_logzio_logs_token')
    logzio_url = os.getenv('LOGZIO_URL', 'https://listener.logz.io:8071')
    output_id = os.getenv('OUTPUT_ID', 'output_id')
    headers = os.getenv('HEADERS', '')

    config += f"""
[OUTPUT]
    Name  logzio
    Match *
    logzio_token {logzio_logs_token}
    logzio_url   {logzio_url}
    id {output_id}
    headers user-agent:logzio-docker-fluentbit-logs
"""

    # Add custom headers if specified
    if headers:
        config += f"    headers      {headers}\n"

    return config


# Function to create the multiline parser configuration
def create_multiline_parser_config():
    # Base multiline parser configuration
    multiline_config = """
[MULTILINE_PARSER]
    name          multiline-regex
    type          regex
    flush_timeout 1000
    #
    # Regex rules for multiline parsing
    # ---------------------------------
    #
    # configuration hints:
    #
    #  - first state always has the name: start_state
    #  - every field in the rule must be inside double quotes
    #
    # rules |   state name  | regex pattern                  | next state
    # ------|---------------|--------------------------------------------
"""

    # Get start state and custom rules from environment variables
    start_state_rule = os.getenv('MULTILINE_START_STATE_RULE', '([a-zA-Z]+ \\d+ \\d+\\:\\d+\\:\\d+)(.*)')
    custom_rules = os.getenv('MULTILINE_CUSTOM_RULES', '')

    # Add custom rules as cont state
    if custom_rules:
        multiline_config += f'    rule      "start_state"   "/{start_state_rule}/"  "cont"\n'
        rules = custom_rules.split(';')
        for rule in rules:
            multiline_config += f'    rule      "cont"          "{rule.strip()}"                     "cont"\n'

    # If no custom rules, add default start state rule without cont
    if not custom_rules:
        multiline_config += f'    rule      "start_state"   "/{start_state_rule}/"\n'

    return multiline_config


# Generalized function to save configuration files
def save_config_file(config, filename):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, 'w') as file:
        file.write(config)
    print(f"Configuration file '{filename}' created successfully.")


def main():
    # Generate and save Fluent Bit configuration
    fluent_bit_config = create_fluent_bit_config()
    save_config_file(fluent_bit_config, "/fluent-bit/etc/fluent-bit.conf")

    # Generate and save multiline parser configuration if rules are defined
    if os.getenv('MULTILINE_START_STATE_RULE'):
        multiline_config = create_multiline_parser_config()
        save_config_file(multiline_config, "/fluent-bit/etc/parsers_multiline.conf")
    plugin_path = "/fluent-bit/plugins/out_logzio.so"

    try:
        with open(plugin_path, 'r') as f:
            print(f"{plugin_path} File found")
    except FileNotFoundError:
        print(f"{plugin_path} File not found")
        

if __name__ == "__main__":
    main()
