import os
import time
import requests
import unittest

class TestLogzioDockerCollector(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Get environment variables
        cls.logzio_api_token = os.getenv('LOGZIO_API_TOKEN')

        if not cls.logzio_api_token:
            raise ValueError('LOGZIO_API_TOKEN environment variable must be set')


    def test_logs_received_in_logzio(self):
        # Query Logz.io API
        query_string = 'output_id=ci-tests'
        headers = {
            'X-API-TOKEN': self.logzio_api_token,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        url = 'https://api.logz.io/v1/search'

        payload = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "query_string": {
                                "query": query_string
                            }
                        },
                        {
                            "range": {
                                "@timestamp": {
                                    "gte": "now-15m",
                                    "lte": "now"
                                }
                            }
                        }
                    ]
                }
            },
            "from": 0,
            "size": 10,
            "sort": [],
            "_source": True,  # Retrieve the source documents
            "docvalue_fields": ["@timestamp"],
            "version": True,
            "stored_fields": ["*"],
            "highlight": {}
        }
        response = requests.post(
            url,
            headers=headers,
            json=payload
        )

        if response.status_code != 200:
            print(f"Failed to query Logz.io API. Status code: {response.status_code}")
            print(f"Response headers: {response.headers}")
            print(f"Response content: {response.text}")
            self.fail(f"API returned {response.status_code} instead of 200")

        results = response.json()
        total_hits = results.get('hits', {}).get('total', 0)
        if isinstance(total_hits, dict):
            total_hits = total_hits.get('value', 0)
        self.assertTrue(total_hits > 0, "No logs found in Logz.io")
        print(f"Found {total_hits} logs in Logz.io.")

        # Check the contents of the logs
        hits = results.get('hits', {}).get('hits', [])
        self.assertTrue(len(hits) > 0, "No hits found in the logs")
        log_found = False
        for hit in hits:
            source = hit.get('_source', {})
            message = source.get('message', '')
            docker_image = source.get('docker_container_image', '')
            output_id = source.get('output_id', '')
            # Additional fields can be extracted as needed

            # Check if the log message and other fields match expectations
            if docker_image == 'chentex/random-logger:latest':
                log_found = True
                print(f"Log from 'chentex/random-logger' found with message: {message}")
                # Additional assertions can be added here
                # For example, check if 'output_id' matches
                self.assertEqual(output_id, 'ci-tests', "Output ID does not match")
                break
        self.assertTrue(log_found, "Expected log message not found in the logs")

if __name__ == '__main__':
    unittest.main()
