import os

# Define constants for file paths
PLUGIN_PATH = "/fluent-bit/plugins/out_logzio.so"
FLUENT_BIT_CONF_PATH = "/fluent-bit/etc/fluent-bit.conf"
PARSERS_MULTILINE_CONF_PATH = "/fluent-bit/etc/parsers_multiline.conf"


# Configuration object to store environment variables
class Config:
    def __init__(self):
        # Environment variables
        self.log_level = os.getenv('LOG_LEVEL', 'info')
        self.read_from_head = os.getenv('READ_FROM_HEAD', 'true')
        self.ignore_older = os.getenv('IGNORE_OLDER', '')
        self.match_container_name = os.getenv('MATCH_CONTAINER_NAME', '')
        self.skip_container_names = os.getenv('SKIP_CONTAINER_NAMES', '')
        self.match_image_name = os.getenv('MATCH_IMAGE_NAME', '')
        self.skip_image_names = os.getenv('SKIP_IMAGE_NAMES', '')
        self.include_line = os.getenv('INCLUDE_LINE', '')
        self.exclude_lines = os.getenv('EXCLUDE_LINES', '')
        self.additional_fields = os.getenv('ADDITIONAL_FIELDS', '')
        self.set_fields = os.getenv('SET_FIELDS', '')
        self.logzio_logs_token = os.getenv('LOGZIO_LOGS_TOKEN', 'your_logzio_logs_token')
        self.logzio_url = os.getenv('LOGZIO_URL', 'https://listener.logz.io:8071')
        self.logzio_type = os.getenv('LOGZIO_TYPE', 'logzio-docker-logs')
        self.output_id = os.getenv('OUTPUT_ID', 'output_id')
        self.headers = os.getenv('HEADERS', '')
        self.multiline_start_state_rule = os.getenv('MULTILINE_START_STATE_RULE', '')
        self.multiline_custom_rules = os.getenv('MULTILINE_CUSTOM_RULES', '')
        self.logs_path = os.getenv('LOGS_PATH', '/var/lib/docker/containers/*/*.log')


def create_fluent_bit_config(config):
    # Ensure that both match and skip are not set for containers and images
    if config.match_container_name and config.skip_container_names:
        raise ValueError("Cannot use both MATCH_CONTAINER_NAME and SKIP_CONTAINER_NAMES")

    if config.match_image_name and config.skip_image_names:
        raise ValueError("Cannot use both MATCH_IMAGE_NAME and SKIP_IMAGE_NAMES")

    # Ensure that both include and exclude lines are not set at the same time
    if config.include_line and config.exclude_lines:
        raise ValueError("Cannot use both INCLUDE_LINE and EXCLUDE_LINES")

    # Generate the Fluent Bit configuration by combining config blocks
    fluent_bit_config = _get_service_config(config)
    fluent_bit_config += _get_input_config(config)
    fluent_bit_config += _get_lua_filter()
    fluent_bit_config += generate_filters(config)
    fluent_bit_config += _get_modify_filters(config)
    fluent_bit_config += _get_output_config(config)
    return fluent_bit_config


def _get_service_config(config):
    return f"""
[SERVICE]
    Parsers_File parsers.conf
    Parsers_File parsers_multiline.conf
    Flush        1
    Daemon       Off
    Log_Level    {config.log_level}
"""


def _get_input_config(config):
    if config.multiline_start_state_rule:
        input_config = f"""
[INPUT]
    Name         tail
    Path         {config.logs_path}
    Parser       docker
    Tag          docker.*
    read_from_head {config.read_from_head}
    multiline.parser multiline-regex
"""
    else:

        input_config = f"""
[INPUT]
    Name         tail
    Path         {config.logs_path}
    Parser       docker
    Tag          docker.*
"""
    if config.ignore_older:
        input_config += f"    ignore_older {config.ignore_older}\n"
    return input_config


def _get_lua_filter():
    return """
[FILTER]
    Name         lua
    Match        docker.*
    script       /fluent-bit/etc/docker-metadata.lua
    call         enrich_with_docker_metadata
"""


def generate_filters(config):
    filters = ""
    # Add filters based on container and image names
    if any([config.match_container_name, config.skip_container_names, config.match_image_name,
            config.skip_image_names]):
        filters += """
[FILTER]
    Name         nest
    Match        *
    Operation    lift
    Nested_under _source
"""
    # Match container names
    if config.match_container_name:
        filters += """
[FILTER]
    Name    grep
    Match   *
"""
        filters += f"    Regex docker_container_name {config.match_container_name.strip()}\n"

    # Skip container names
    if config.skip_container_names:
        names = config.skip_container_names.split(',')
        filters += """
[FILTER]
    Name    grep
    Match   *
"""
        for name in names:
            filters += f"    Exclude docker_container_name {name.strip()}\n"

    # Match image names
    if config.match_image_name:
        filters += """
[FILTER]
    Name    grep
    Match   *
"""
        filters += f"    Regex docker_container_image {config.match_image_name.strip()}\n"

    # Skip image names
    if config.skip_image_names:
        images = config.skip_image_names.split(',')
        filters += """
[FILTER]
    Name    grep
    Match   *
"""
        for image in images:
            filters += f"    Exclude docker_container_image {image.strip()}\n"

    # Include lines based on message content
    if config.include_line:
        filters += """
[FILTER]
    Name    grep
    Match   *
"""
        filters += f"    Regex message {config.include_line.strip()}\n"

    # Exclude lines based on message content
    if config.exclude_lines:
        lines = config.exclude_lines.split(',')
        filters += """
[FILTER]
    Name    grep
    Match   *
"""
        for line in lines:
            filters += f"    Exclude message {line.strip()}\n"

    return filters


def _get_modify_filters(config):
    filters = """
[FILTER]
    Name modify
    Match *
    Rename log message
"""
    # Add additional fields if specified
    if config.additional_fields:
        fields = config.additional_fields.split(',')
        for field in fields:
            try:
                key, value = field.split(':', 1)
                filters += f"    Add {key.strip()} {value.strip()}\n"
            except ValueError:
                print(f"Warning: Skipping invalid additional field '{field}'. Expected format 'key:value'.")

    # Add set fields if specified
    if config.set_fields:
        fields = config.set_fields.split(',')
        for field in fields:
            try:
                key, value = field.split(':', 1)
                filters += f"    Set {key.strip()} {value.strip()}\n"
            except ValueError:
                print(f"Warning: Skipping invalid set field '{field}'. Expected format 'key:value'.")

    return filters


def _get_output_config(config):
    output_config = f"""
[OUTPUT]
    Name  logzio
    Match *
    logzio_token {config.logzio_logs_token}
    logzio_url   {config.logzio_url}
    logzio_type  {config.logzio_type}
    id {config.output_id}
    headers user-agent:logzio-docker-collector-logs
"""
    if config.headers:
        output_config += f"    headers      {config.headers}\n"
    return output_config


def create_multiline_parser_config(config):
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
    # Add custom rules
    if config.multiline_custom_rules and config.multiline_start_state_rule:
        multiline_config += f'    rule      "start_state"   "/{config.multiline_start_state_rule}/"  "cont"\n'
        rules = config.multiline_custom_rules.split(';')
        for rule in rules:
            multiline_config += f'    rule      "cont"          "{rule.strip()}"                     "cont"\n'
    elif config.multiline_start_state_rule:
        multiline_config += f'    rule      "start_state"   "/{config.multiline_start_state_rule}/"\n'

    return multiline_config


def save_config_file(config_content, filename):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, 'w') as file:
        file.write(config_content)
    print(f"Configuration file '{filename}' created successfully.")


def main():
    # Instantiate the configuration object
    config = Config()

    # Check if the Logz.io plugin exists before proceeding with configuration
    try:
        # Attempt to open the plugin file to check for its existence
        with open(PLUGIN_PATH, 'r') as f:
            print(f"{PLUGIN_PATH} File found")
    except FileNotFoundError:
        print(f"Error: {PLUGIN_PATH} file not found. Configuration will not be created.")
        return
    except PermissionError:
        print(f"Error: Permission denied when accessing {PLUGIN_PATH}. Check your file permissions.")
        return
    except Exception as e:
        print(f"An unexpected error occurred while checking {PLUGIN_PATH}: {e}")
        return

    # Generate and save Fluent Bit configuration
    fluent_bit_config = create_fluent_bit_config(config)
    save_config_file(fluent_bit_config, FLUENT_BIT_CONF_PATH)

    # Generate and save multiline parser configuration if rules are defined
    if config.multiline_start_state_rule:
        multiline_config = create_multiline_parser_config(config)
        save_config_file(multiline_config, PARSERS_MULTILINE_CONF_PATH)


if __name__ == "__main__":
    main()
