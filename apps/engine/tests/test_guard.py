"""Process-wide socket guard: second application layer of egress control."""

import socket
import threading
import unittest

from grounded import guard
from grounded.policy import EgressError, from_env

AWS_ENV = {
    "GROUNDED_DEPLOYMENT_MODE": "aws-private",
    "GROUNDED_AWS_REGIONS": "us-east-1",
    "GROUNDED_BEDROCK_MODELS": "amazon.nova-pro-v1:0",
    "GROUNDED_AWS_PRIVATE_DNS": "true",
}


class GuardTest(unittest.TestCase):
    def tearDown(self):
        guard.uninstall()

    def test_public_ip_blocked_before_connect(self):
        guard.install(from_env({}))
        for address in (("1.1.1.1", 443), ("8.8.8.8", 53), ("52.94.0.1", 443)):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                with self.assertRaises(EgressError):
                    sock.connect(address)
            finally:
                sock.close()

    def test_udp_sendto_public_blocked(self):
        guard.install(from_env({}))
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            with self.assertRaises(EgressError):
                sock.sendto(b"x", ("9.9.9.9", 53))
        finally:
            sock.close()

    def test_loopback_allowed(self):
        guard.install(from_env({}))
        server = socket.socket()
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        port = server.getsockname()[1]
        accepted = []
        thread = threading.Thread(target=lambda: accepted.append(server.accept()))
        thread.start()
        client = socket.create_connection(("127.0.0.1", port), timeout=2)
        thread.join(2)
        client.close()
        for conn, _addr in accepted:
            conn.close()
        server.close()
        self.assertEqual(len(accepted), 1)

    def test_aws_private_allows_only_ips_resolved_from_approved_hosts(self):
        guard.install(from_env(AWS_ENV))
        # Simulate resolution of an approved regional endpoint.
        guard._approved_ips.add("52.94.0.10")
        self.assertTrue(guard._ip_allowed(("52.94.0.10", 443)))
        self.assertFalse(guard._ip_allowed(("52.94.0.11", 443)))
        self.assertFalse(guard._ip_allowed(("93.184.216.34", 443)))

    def test_install_is_idempotent_and_uninstall_restores(self):
        original = socket.socket.connect
        guard.install(from_env({}))
        guard.install(from_env({}))
        self.assertIsNot(socket.socket.connect, original)
        guard.uninstall()
        self.assertIs(socket.socket.connect, original)


if __name__ == "__main__":
    unittest.main()
