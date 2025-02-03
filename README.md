# docker-logs-collector

docker-logs-collector is a Docker container that uses Fluent Bit to collect logs from other Docker containers and forward those logs to your Logz.io account.

To use this container, you'll set environment variables in your `docker run` command.
docker-logs-collector uses those environment variables to generate a valid Fluent Bit configuration for the container.
docker-logs-collector mounts docker.sock and the Docker logs directory to the container itself, allowing Fluent Bit to collect the logs and metadata.

docker-logs-collector ships logs only.
If you want to ship metrics to Logz.io, see [docker-collector-metrics](https://github.com/logzio/docker-collector-metrics).

**Note:**
- Ensure your Fluent Bit configuration matches your logging requirements and environment variables are set correctly.

## docker-logs-collector setup

### 1. Pull the Docker image

Download the appropriate Docker image for your architecture (amd64 or arm64):

```shell
docker pull logzio/docker-logs-collector:latest
```

### 2. Run the container

For a complete list of options, see the parameters below the code block.👇

```shell
docker run --name docker-logs-collector \
--env LOGZIO_LOGS_TOKEN="<LOGS-SHIPPING-TOKEN>" \
-v /var/run/docker.sock:/var/run/docker.sock:ro \
-v /var/lib/docker/containers:/var/lib/docker/containers \
-e HEADERS="user-agent:logzio-docker-logs" \
logzio/docker-logs-collector:latest
```

#### Parameters

| Parameter                      | Description                                                                                                                                                                                                                                                                                            |
|--------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **LOGZIO_LOGS_TOKEN**          | **Required**. Your Logz.io account logs token. Replace `<LOGS-SHIPPING-TOKEN>` with the [token](https://app.logz.io/#/dashboard/settings/general) of the account you want to ship to.                                                                                                                  |
| **LOGZIO_URL**                 | **Default**: `https://listener.logz.io:8071`.<br> The full URL to send logs to, including your region if needed. For example, for the EU region, use `https://listener-eu.logz.io:8071`. to.                                                                                                           |
| **LOGZIO_TYPE**                | **Default**: `logzio-docker-logs`. Sets the log type.                                                                                                                                                                                                                                                  |
| **LOGS_PATH**                  | **Dfault**: `/var/lib/docker/containers/*/*.log`. The path to docker container logs, supports globs                                                                                                                                                                                                    |
| **MATCH_CONTAINER_NAME**       | Specify a container to collect logs from. If the container's name matches, its logs are shipped; otherwise, its logs are ignored. <br /> **Note**: This option cannot be used with SKIP_CONTAINER_NAMES. Use regular expressions to keep records that match a specific field.                          |
| **SKIP_CONTAINER_NAMES**       | Comma-separated list of containers to ignore. If a container's name matches a name on this list, its logs are ignored; otherwise, its logs are shipped. <br /> **Note**: This option cannot be used with MATCH_CONTAINER_NAME. Use regular expressions to exclude records that match a specific field. |
| **MATCH_IMAGE_NAME**           | Specify a image to collect logs from. If the image's name matches, its logs are shipped; otherwise, its logs are ignored. <br /> **Note**: This option cannot be used with SKIP_IMAGE_NAMES. Use regular expressions to keep records that match a specific field.                                      |
| **SKIP_IMAGE_NAMES**           | Comma-separated list of images to ignore. If a image's name matches a name on this list, its logs are ignored; otherwise, its logs are shipped. <br /> **Note**: This option cannot be used with MATCH_IMAGE_NAME. Use regular expressions to exclude records that match a specific field.             |
| **INCLUDE_LINE**               | Regular expression to match the lines that you want Fluent Bit to include.                                                                                                                                                                                                                             |
| **EXCLUDE_LINES**              | Regular expression to match the lines that you want Fluent Bit to exclude.                                                                                                                                                                                                                             |
| **ADDITIONAL_FIELDS**          | Include additional fields with every message sent, formatted as `"fieldName1:fieldValue1,fieldName2:fieldValue2"`.                                                                                                                                                                                     |
| **SET_FIELDS**                 | Set fields with every message sent, formatted as `"fieldName1:fieldValue1,fieldName2:fieldValue2"`.                                                                                                                                                                                                    |
| **LOG_LEVEL**                  | **Default** `info`. Set log level for Fluent Bit. Allowed values are: `debug`, `info`, `warning`, `error`.                                                                                                                                                                                             |
| **MULTILINE_START_STATE_RULE** | Regular expression for the start state rule of multiline parsing. <br /> See [Fluent Bit's official documentation](https://docs.fluentbit.io/manual/administration/configuring-fluent-bit/multiline-parsing#rules-definition) for further info.                                                        |
| **MULTILINE_CUSTOM_RULES**     | Custom rules for multiline parsing, separated by semicolons `;`.                                                                                                                                                                                                                                       |
| **READ_FROM_HEAD**             | **Default** `true`. Specify if Fluent Bit should read logs from the beginning.                                                                                                                                                                                                                         |
| **OUTPUT_ID**                  | **Default** `output_id`. Specify the output ID for Fluent Bit logs.                                                                                                                                                                                                                                    |
| **HEADERS**                    | Custom headers for Fluent Bit logs.                                                                                                                                                                                                                                                                    |


### 3. Check Logz.io for your logs

Spin up your Docker containers if you haven’t done so already. Give your logs a few minutes to get from your system to your Logz.io account.

### Change log
- 0.1.1:
  - Add `LOGS_PATH` option.
- 0.1.0:
  - Initial release using Fluent Bit.
