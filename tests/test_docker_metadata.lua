package.path = "../?.lua;" .. package.path
local docker_metadata = require("docker-metadata")  -- Adjust the path if necessary
local busted = require("busted")

describe("Docker Metadata Enrichment", function()

    local original_getenv
    local original_os_time

    before_each(function()
        -- Backup the original os.time function
        original_os_time = os.time
        os.time = function() return 1600000000 end  -- Fixed timestamp for consistency

        -- Backup the original os.getenv function
        original_getenv = os.getenv

        -- Mock os.getenv to simulate DEBUG_MODE environment variable
        os.getenv = function(var)
            if var == "DEBUG_MODE" then
                return "true"  -- Simulate DEBUG_MODE=true
            end
            return nil  -- For other environment variables, return nil
        end

        -- Clear cache before each test
        docker_metadata.cache = {}
    end)

    after_each(function()
        -- Restore the original os.time function after each test
        os.time = original_os_time

        -- Restore the original os.getenv function after each test
        os.getenv = original_getenv
    end)

    it("extracts container ID from log tag", function()
        local tag = "containers.abcdef12345"
        local container_id = docker_metadata.get_container_id_from_tag(tag)
        assert.are.equal("abcdef12345", container_id)
    end)

    it("returns nil when container ID is missing in tag", function()
        local tag = "invalid.tag.format"
        local container_id = docker_metadata.get_container_id_from_tag(tag)
        assert.is_nil(container_id)
    end)

    it("reads metadata from Docker config file", function()
        -- Mock reading from Docker config file
        local mock_file_content = [[
            {"Name":"/my-container","Image":"my-image","StartedAt":"2021-10-15T12:34:56"}
        ]]
        -- Mock the io.open function to return our test data
        stub(io, "open", function()
            return {
                lines = function() return mock_file_content:gmatch("[^\r\n]+") end,
                close = function() end
            }
        end)

        local container_id = "abcdef12345"
        local metadata = docker_metadata.get_container_metadata_from_disk(container_id)

        assert.are.equal("my-container", metadata['docker_container_name'])
        assert.are.equal("my-image", metadata['docker_container_image'])
        assert.are.equal("2021-10-15T12:34:56", metadata['docker_container_started'])

        io.open:revert()  -- Revert the mock
    end)

    it("uses cache when metadata is available and fresh", function()
        local container_id = "abcdef12345"
        local tag = "containers." .. container_id
        local record = { log = "some log message" }
        local timestamp = os.time()

        -- Set up the cache with fresh metadata
        docker_metadata.cache[container_id] = {
            time = os.time(),
            docker_container_name = "cached-container",
            docker_container_image = "cached-image"
        }

        -- Mock the function that reads from disk to ensure it doesn't get called
        stub(docker_metadata, "get_container_metadata_from_disk")

        -- Call the function that enriches the log record with metadata (this will check the cache)
        local status, enriched_timestamp, enriched_record = docker_metadata.enrich_with_docker_metadata(tag, timestamp, record)

        -- Check that the cache was used and the disk read was not
        assert.are.equal("cached-container", enriched_record.docker_container_name)
        assert.are.equal("cached-image", enriched_record.docker_container_image)
        assert.are.equal('cache', enriched_record.source)

        -- Ensure the function to read from disk was not called
        assert.spy(docker_metadata.get_container_metadata_from_disk).was_not_called()

        -- Restore the original function
        docker_metadata.get_container_metadata_from_disk:revert()
    end)

    -- Additional Test 1: Updates cache when cached data is stale
    it("updates cache when cached data is stale", function()
        local container_id = "abcdef12345"
        local tag = "containers." .. container_id
        local record = { log = "some log message" }
        local stale_time = os.time() - (docker_metadata.CACHE_TTL_SEC + 1)
        local timestamp = os.time()

        -- Set up the cache with stale metadata
        docker_metadata.cache[container_id] = {
            time = stale_time,
            docker_container_name = "stale-container",
            docker_container_image = "stale-image"
        }

        -- Mock the function that reads from disk to return fresh data
        local fresh_metadata = {
            time = os.time(),
            docker_container_name = "fresh-container",
            docker_container_image = "fresh-image"
        }
        stub(docker_metadata, "get_container_metadata_from_disk", function() return fresh_metadata end)

        -- Call the function that enriches the log record with metadata
        local status, enriched_timestamp, enriched_record = docker_metadata.enrich_with_docker_metadata(tag, timestamp, record)

        -- Check that the disk read function was called and cache was updated
        assert.are.equal("fresh-container", enriched_record.docker_container_name)
        assert.are.equal("fresh-image", enriched_record.docker_container_image)
        assert.are.equal('disk', enriched_record.source)
        assert.spy(docker_metadata.get_container_metadata_from_disk).was_called()

        -- Ensure that the cache was updated with fresh data
        assert.are.equal(fresh_metadata, docker_metadata.cache[container_id])

        -- Restore the original function
        docker_metadata.get_container_metadata_from_disk:revert()
    end)

    -- Additional Test 2: Handles missing Docker config file gracefully
    it("handles missing Docker config file gracefully", function()
        local container_id = "abc123def456"
        local tag = "containers." .. container_id
        local record = { log = "log message" }
        local timestamp = os.time()

        -- Mock io.open to return nil, simulating a missing file
        stub(io, "open", function() return nil end)

        -- Call the function that enriches the log record with metadata
        local status, enriched_timestamp, enriched_record = docker_metadata.enrich_with_docker_metadata(tag, timestamp, record)

        -- Check that the metadata fields are not added
        assert.is_nil(enriched_record.docker_container_name)
        assert.is_nil(enriched_record.docker_container_image)
        assert.are.equal('disk', enriched_record.source)

        io.open:revert()
    end)

    -- Additional Test 3: Handles malformed Docker config file gracefully
    it("handles malformed Docker config file gracefully", function()
        local container_id = "def456abc789"
        local tag = "containers." .. container_id
        local record = { log = "log message" }
        local timestamp = os.time()

        -- Mock io.open to return a file with malformed content
        local mock_file_content = [[
            this is not valid json
        ]]
        stub(io, "open", function()
            return {
                lines = function() return mock_file_content:gmatch("[^\r\n]+") end,
                close = function() end
            }
        end)

        -- Call the function that enriches the log record with metadata
        local status, enriched_timestamp, enriched_record = docker_metadata.enrich_with_docker_metadata(tag, timestamp, record)

        -- Check that the metadata fields are not added
        assert.is_nil(enriched_record.docker_container_name)
        assert.is_nil(enriched_record.docker_container_image)
        assert.are.equal('disk', enriched_record.source)

        io.open:revert()
    end)

    -- Additional Test 4: Handles log tag without container ID
    it("handles log tag without container ID", function()
        local tag = "invalid.tag.format"
        local record = { log = "log message" }
        local timestamp = os.time()

        -- Call the function that enriches the log record with metadata
        local status, enriched_timestamp, enriched_record = docker_metadata.enrich_with_docker_metadata(tag, timestamp, record)

        -- Check that the function returns zeros and does not modify the record
        assert.are.equal(0, status)
        assert.are.equal(0, enriched_timestamp)
        assert.are.equal(0, enriched_record)
    end)

    -- Additional Test 5: Reads from disk and populates cache when cache is empty
    it("reads from disk and populates cache when cache is empty", function()
        local container_id = "fedcba654321"
        local tag = "containers." .. container_id
        local record = { log = "some log message" }
        local timestamp = os.time()

        -- Ensure cache is empty
        docker_metadata.cache = {}

        -- Mock the function that reads from disk to return data
        local metadata_from_disk = {
            time = os.time(),
            docker_container_name = "new-container",
            docker_container_image = "new-image"
        }
        stub(docker_metadata, "get_container_metadata_from_disk", function() return metadata_from_disk end)

        -- Call the function that enriches the log record with metadata
        local status, enriched_timestamp, enriched_record = docker_metadata.enrich_with_docker_metadata(tag, timestamp, record)

        -- Check that the disk read function was called and cache was updated
        assert.are.equal("new-container", enriched_record.docker_container_name)
        assert.are.equal("new-image", enriched_record.docker_container_image)
        assert.are.equal('disk', enriched_record.source)
        assert.spy(docker_metadata.get_container_metadata_from_disk).was_called()

        -- Ensure that the cache was updated with the data from disk
        assert.are.equal(metadata_from_disk, docker_metadata.cache[container_id])

        -- Restore the original function
        docker_metadata.get_container_metadata_from_disk:revert()
    end)

    -- Additional Test 6: Handles DEBUG_MODE correctly
    it("handles DEBUG_MODE correctly", function()
        -- Mock os.getenv to return false for DEBUG_MODE
        os.getenv = function(var)
            if var == "DEBUG_MODE" then
                return "false"
            end
            return nil
        end

        -- Spy on the print function
        spy.on(_G, "print")

        -- Call a function that would trigger debug_print
        local tag = "containers.abcdef12345"
        docker_metadata.get_container_id_from_tag(tag)

        -- Ensure that print was not called
        assert.spy(_G.print).was_not_called()

        -- Restore the original print function
        _G.print:revert()

        -- Reset os.getenv mock
        os.getenv = function(var)
            if var == "DEBUG_MODE" then
                return "true"
            end
            return nil
        end
    end)

    -- Additional Test 7: Handles multiple containers in cache correctly
    it("handles multiple containers in cache correctly", function()
        local container_id1 = "abc123def456"
        local container_id2 = "def456abc789"
        local tag1 = "containers." .. container_id1
        local tag2 = "containers." .. container_id2
        local record = { log = "some log message" }
        local timestamp = os.time()

        -- Set up the cache with metadata for two containers
        docker_metadata.cache[container_id1] = {
            time = os.time(),
            docker_container_name = "container-one",
            docker_container_image = "image-one"
        }
        docker_metadata.cache[container_id2] = {
            time = os.time(),
            docker_container_name = "container-two",
            docker_container_image = "image-two"
        }

        -- Mock the function that reads from disk to ensure it doesn't get called
        stub(docker_metadata, "get_container_metadata_from_disk")

        -- Enrich record for the first container
        local _, _, enriched_record1 = docker_metadata.enrich_with_docker_metadata(tag1, timestamp, record)
        assert.are.equal("container-one", enriched_record1.docker_container_name)
        assert.are.equal("image-one", enriched_record1.docker_container_image)
        assert.are.equal('cache', enriched_record1.source)

        -- Enrich record for the second container
        local _, _, enriched_record2 = docker_metadata.enrich_with_docker_metadata(tag2, timestamp, record)
        assert.are.equal("container-two", enriched_record2.docker_container_name)
        assert.are.equal("image-two", enriched_record2.docker_container_image)
        assert.are.equal('cache', enriched_record2.source)

        -- Ensure the function to read from disk was not called
        assert.spy(docker_metadata.get_container_metadata_from_disk).was_not_called()

        -- Restore the original function
        docker_metadata.get_container_metadata_from_disk:revert()
    end)

end)
