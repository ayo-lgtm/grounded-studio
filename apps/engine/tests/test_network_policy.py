import os
import unittest
from unittest.mock import patch

from grounded.network_policy import EgressPolicyError, assert_internal_url, assert_private_runtime


class NetworkPolicyTest(unittest.TestCase):
    def test_loopback_and_service_names_are_allowed(self):
        self.assertEqual(assert_internal_url("http://127.0.0.1:9000"), "http://127.0.0.1:9000")
        self.assertEqual(assert_internal_url("redis://redis:6379/0"), "redis://redis:6379/0")
        self.assertEqual(assert_internal_url("http://minio:9000"), "http://minio:9000")

    def test_public_host_is_blocked(self):
        with self.assertRaises(EgressPolicyError):
            assert_internal_url("https://example.com")

    def test_private_ip_is_allowed(self):
        self.assertEqual(assert_internal_url("http://10.10.0.8:11434"), "http://10.10.0.8:11434")

    def test_managed_hosting_env_is_blocked_in_private_mode(self):
        with patch.dict(os.environ, {"RAILWAY_ENVIRONMENT": "production"}, clear=False):
            with self.assertRaises(EgressPolicyError):
                assert_private_runtime(("MINIO_ENDPOINT", "http://minio:9000"))


if __name__ == "__main__":
    unittest.main()
