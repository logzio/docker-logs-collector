import unittest
from unittest.mock import patch, mock_open
import os

# Import the module to be tested
import create_fluent_bit_config

class TestCreateFluentBitConfig(unittest.TestCase):

    def setUp(self):
        # Mock os.makedirs to prevent actual directory creation
        self.makedirs_patcher = patch('os.makedirs')
        self.mock_makedirs = self.makedirs_patcher.start()

        # Mock open to prevent actual file I/O
        self.open_patcher = patch('builtins.open', mock_open())
        self.mock_open = self.open_patcher.start()

        # Mock os.system to prevent actual system calls
        self.system_patcher = patch('os.system')
        self.mock_system = self.system_patcher.start()

        # Mock print to capture print statements
        self.print_patcher = patch('builtins.print')
        self.mock_print = self.print_patcher.start()

    def tearDown(self):
        self.makedirs_patcher.stop()
        self.open_patcher.stop()
        self.system_patcher.stop()
        self.print_patcher.stop()

    @patch.dict(os.environ, {'LOGZIO_LOGS_TOKEN': 'test_token'})
    def test_default_configuration(self):
        config = create_fluent_bit_config.create_fluent_bit_config()
        self.assertIn('Log_Level    info', config)
        self.assertIn('logzio_token test_token', config)
        self.assertIn('logzio_url   https://listener.logz.io:8071', config)
        self.assertIn('id output_id', config)
        self.assertIn('[INPUT]', config)
        self.assertIn('Name         tail', config)
        self.assertNotIn('multiline.parser', config)

    @patch.dict(os.environ, {
        'LOGZIO_LOGS_TOKEN': 'test_token',
        'LOG_LEVEL': 'debug',
        'MULTILINE_START_STATE_RULE': '^[ERROR]',
        'MULTILINE_CUSTOM_RULES': r'^\s+at',
        'READ_FROM_HEAD': 'false',
        'IGNORE_OLDER': '1h'
    })
    def test_multiline_configuration(self):
        config = create_fluent_bit_config.create_fluent_bit_config()
        self.assertIn('Log_Level    debug', config)
        self.assertIn('multiline.parser multiline-regex', config)
        self.assertIn('read_from_head false', config)
        self.assertIn('ignore_older 1h', config)

        multiline_config = create_fluent_bit_config.create_multiline_parser_config()
        self.assertIn('name          multiline-regex', multiline_config)
        self.assertIn('rule      "start_state"   "/^[ERROR]/"  "cont"', multiline_config)
        self.assertIn(r'rule      "cont"          "^\s+at"                     "cont"', multiline_config)

    @patch.dict(os.environ, {
        'LOGZIO_LOGS_TOKEN': 'test_token',
        'MATCH_CONTAINER_NAME': 'my_app',
        'SKIP_CONTAINER_NAMES': 'db',
    })
    def test_conflicting_container_filters(self):
        with self.assertRaises(ValueError) as context:
            create_fluent_bit_config.create_fluent_bit_config()
        self.assertIn('Cannot use both matchContainerName and skipContainerName', str(context.exception))

    @patch.dict(os.environ, {
        'LOGZIO_LOGS_TOKEN': 'test_token',
        'MATCH_IMAGE_NAME': 'my_image',
        'SKIP_IMAGE_NAMES': 'redis',
    })
    def test_conflicting_image_filters(self):
        with self.assertRaises(ValueError) as context:
            create_fluent_bit_config.create_fluent_bit_config()
        self.assertIn('Cannot use both matchImageName and skipImageName', str(context.exception))

    @patch.dict(os.environ, {
        'LOGZIO_LOGS_TOKEN': 'test_token',
        'ADDITIONAL_FIELDS': 'env:production,team:backend',
        'SET_FIELDS': 'service:web,version:1.0.0'
    })
    def test_additional_and_set_fields(self):
        config = create_fluent_bit_config.create_fluent_bit_config()
        self.assertIn('[FILTER]\n    Name modify\n    Match *\n    Add env production\n    Add team backend', config)
        self.assertIn('[FILTER]\n    Name modify\n    Match *\n    Set service web\n    Set version 1.0.0', config)

    @patch.dict(os.environ, {
        'LOGZIO_LOGS_TOKEN': 'test_token',
        'MATCH_CONTAINER_NAME': 'my_app',
        'LOG_LEVEL': 'info'
    })
    def test_match_container_name(self):
        config = create_fluent_bit_config.create_fluent_bit_config()
        self.assertIn('Regex docker_container_name my_app', config)

    @patch.dict(os.environ, {
        'LOGZIO_LOGS_TOKEN': 'test_token',
        'SKIP_CONTAINER_NAMES': 'db,cache',
        'LOG_LEVEL': 'info'
    })
    def test_skip_container_names(self):
        config = create_fluent_bit_config.create_fluent_bit_config()
        self.assertIn('Exclude docker_container_name db', config)
        self.assertIn('Exclude docker_container_name cache', config)

    @patch.dict(os.environ, {
        'LOGZIO_LOGS_TOKEN': 'test_token',
        'MATCH_IMAGE_NAME': 'my_image',
        'LOG_LEVEL': 'info'
    })
    def test_match_image_name(self):
        config = create_fluent_bit_config.create_fluent_bit_config()
        self.assertIn('Regex docker_container_image my_image', config)

    @patch.dict(os.environ, {
        'LOGZIO_LOGS_TOKEN': 'test_token',
        'SKIP_IMAGE_NAMES': 'redis,postgres',
        'LOG_LEVEL': 'info'
    })
    def test_skip_image_names(self):
        config = create_fluent_bit_config.create_fluent_bit_config()
        self.assertIn('Exclude docker_container_image redis', config)
        self.assertIn('Exclude docker_container_image postgres', config)

    @patch.dict(os.environ, {
        'LOGZIO_LOGS_TOKEN': 'test_token',
        'INCLUDE_LINE': 'ERROR',
        'EXCLUDE_LINES': 'DEBUG,TRACE'
    })
    def test_conflicting_line_filters(self):
        with self.assertRaises(ValueError) as context:
            create_fluent_bit_config.create_fluent_bit_config()
        self.assertIn('Cannot use both includeLines and excludeLines', str(context.exception))

    @patch.dict(os.environ, {
        'LOGZIO_LOGS_TOKEN': 'test_token',
        'INCLUDE_LINE': 'ERROR',
    })
    def test_include_line(self):
        config = create_fluent_bit_config.create_fluent_bit_config()
        self.assertIn('Regex message ERROR', config)

    @patch.dict(os.environ, {
        'LOGZIO_LOGS_TOKEN': 'test_token',
        'EXCLUDE_LINES': 'DEBUG,TRACE',
    })
    def test_exclude_lines(self):
        config = create_fluent_bit_config.create_fluent_bit_config()
        self.assertIn('Exclude message DEBUG', config)
        self.assertIn('Exclude message TRACE', config)

    @patch.dict(os.environ, {'LOGZIO_LOGS_TOKEN': 'test_token'})
    def test_save_config_file(self):
        config_content = "Test Config Content"
        filename = "configs/test.conf"
        create_fluent_bit_config.save_config_file(config_content, filename)
        self.mock_makedirs.assert_called_once_with('configs', exist_ok=True)
        self.mock_open.assert_called_once_with(filename, 'w')
        self.mock_open().write.assert_called_once_with(config_content)
        self.mock_print.assert_called_with(f"Configuration file '{filename}' created successfully.")

    @patch.dict(os.environ, {
        'LOGZIO_LOGS_TOKEN': 'test_token',
        'HEADERS': 'X-Api-Key:12345'
    })
    def test_custom_headers(self):
        config = create_fluent_bit_config.create_fluent_bit_config()
        self.assertIn('headers      X-Api-Key:12345', config)

    @patch.dict(os.environ, {
        'LOGZIO_LOGS_TOKEN': 'test_token',
        'LOGZIO_URL': 'https://custom-listener.logz.io:8071',
        'OUTPUT_ID': 'custom_output_id',
    })
    def test_custom_logzio_url_and_output_id(self):
        config = create_fluent_bit_config.create_fluent_bit_config()
        self.assertIn('logzio_url   https://custom-listener.logz.io:8071', config)
        self.assertIn('id custom_output_id', config)

    @patch.dict(os.environ, {'LOGZIO_LOGS_TOKEN': 'test_token'})
    def test_main_execution(self):
        with patch('create_fluent_bit_config.create_fluent_bit_config') as mock_create_config, \
             patch('create_fluent_bit_config.create_multiline_parser_config') as mock_create_multiline_config, \
             patch('create_fluent_bit_config.save_config_file') as mock_save_config_file, \
             patch('builtins.open', mock_open()), \
             patch('os.makedirs'), \
             patch('os.system') as mock_system:

            # Mock the functions to prevent actual execution
            mock_create_config.return_value = 'Test Fluent Bit Config'
            mock_create_multiline_config.return_value = 'Test Multiline Parser Config'

            # Call the main function
            create_fluent_bit_config.main()

            # Check that configurations were created and saved
            mock_create_config.assert_called_once()
            mock_save_config_file.assert_any_call('Test Fluent Bit Config', '/fluent-bit/etc/fluent-bit.conf')

            # Since MULTILINE_START_STATE_RULE is not set, multiline config should not be created
            mock_create_multiline_config.assert_not_called()

if __name__ == '__main__':
    unittest.main()
