local M = {}

-- Directory where Docker stores container data
M.DOCKER_VAR_DIR = '/var/lib/docker/containers/'

-- Docker container configuration file
M.DOCKER_CONTAINER_CONFIG_FILE = '/config.v2.json'

-- Cache Time-To-Live in seconds
M.CACHE_TTL_SEC = 300

-- Table defining patterns to extract metadata from Docker config file
M.DOCKER_CONTAINER_METADATA = {
  ['docker_container_name'] = '\"Name\":\"/?(.-)\"',  -- Extract container name
  ['docker_container_image'] = '\"Image\":\"/?(.-)\"',  -- Extract container image name
  ['docker_container_started'] = '\"StartedAt\":\"/?(.-)\"'  -- Extract container start time
}

-- Cache to store metadata for containers
M.cache = {}

local debug_mode = os.getenv("DEBUG_MODE") == "true"

-- Function to print debug messages if debug mode is enabled
local function debug_print(...)
  if debug_mode then
    print(...)
  end
end

-- Function to extract container ID from log tag
function M.get_container_id_from_tag(tag)
  debug_print("Getting container ID from tag:", tag)
  local container_id = tag:match('containers%.([a-f0-9]+)')
  debug_print("Container ID:", container_id)
  return container_id
end

-- Function to read and extract metadata from Docker config file
function M.get_container_metadata_from_disk(container_id)
  local docker_config_file = M.DOCKER_VAR_DIR .. container_id .. M.DOCKER_CONTAINER_CONFIG_FILE
  debug_print("Reading metadata from:", docker_config_file)

  local fl = io.open(docker_config_file, 'r')
  if fl == nil then
    debug_print("Failed to open file:", docker_config_file)
    return nil
  end

  local data = { time = os.time() }

  for line in fl:lines() do
    for key, regex in pairs(M.DOCKER_CONTAINER_METADATA) do
      local match = line:match(regex)
      if match then
        data[key] = match
        debug_print("Found metadata:", key, match)
      end
    end
  end
  fl:close()

  if next(data) == nil then
    debug_print("No metadata found in file:", docker_config_file)
    return nil
  else
    debug_print("Metadata extracted for container:", container_id)
    return data
  end
end

-- Function to enrich log records with Docker metadata
function M.enrich_with_docker_metadata(tag, timestamp, record)
  debug_print("Enriching record with tag:", tag)

  local container_id = M.get_container_id_from_tag(tag)
  if not container_id then
    debug_print("No container ID found for tag:", tag)
    return 0, 0, 0
  end

  local new_record = record
  new_record['docker_container_id'] = container_id
  new_record['message'] = record.log
  new_record['log'] = nil

  local cached_data = M.cache[container_id]
  if cached_data == nil or (os.time() - cached_data['time'] > M.CACHE_TTL_SEC) then
    cached_data = M.get_container_metadata_from_disk(container_id)
    M.cache[container_id] = cached_data
    new_record['source'] = 'disk'
  else
    new_record['source'] = 'cache'
  end

  if cached_data then
    for key, value in pairs(cached_data) do
      new_record[key] = value
    end
  end

  debug_print("Enriched record:", new_record)
  for k, v in pairs(new_record) do
    debug_print(k, v)
  end

  return 1, timestamp, new_record
end

-- Make functions globally accessible
_G['enrich_with_docker_metadata'] = M.enrich_with_docker_metadata

return M