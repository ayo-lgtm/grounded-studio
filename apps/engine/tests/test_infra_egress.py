"""Infrastructure egress controls are present and not weakened."""

import re
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
DATA_SERVICES = {"postgres", "redis", "minio", "api", "worker"}


class ComposeTest(unittest.TestCase):
    def _check(self, path: Path):
        spec = yaml.safe_load(path.read_text(encoding="utf-8"))
        self.assertTrue(spec["networks"]["private"]["internal"], path)
        for name in DATA_SERVICES:
            service = spec["services"][name]
            self.assertEqual(service.get("networks"), ["private"], f"{path}:{name}")
            self.assertNotIn("ports", service, f"{path}:{name} must not publish ports")
        gateway = spec["services"]["gateway"]
        self.assertIn("edge", gateway["networks"])
        for port in gateway.get("ports") or []:
            self.assertTrue(str(port).startswith("127.0.0.1:"), port)
        text = path.read_text(encoding="utf-8")
        self.assertIn("GROUNDED_DEPLOYMENT_MODE: offline", text)
        self.assertNotRegex(text, r"DEV_BYPASS_AUTH:\s*\"?true")
        self.assertIn("AUTH_MODE: ${AUTH_MODE:?", text)

    def test_local_compose(self):
        self._check(ROOT / "infra" / "compose.yaml")

    def test_coolify_compose(self):
        self._check(ROOT / "docker-compose.coolify.yml")


class KubernetesTest(unittest.TestCase):
    def test_default_deny(self):
        docs = list(yaml.safe_load_all((ROOT / "infra" / "k8s" / "networkpolicy.yaml").read_text(encoding="utf-8")))
        deny = next(d for d in docs if d["metadata"]["name"] == "default-deny-all")
        self.assertEqual(deny["spec"]["podSelector"], {})
        self.assertEqual(set(deny["spec"]["policyTypes"]), {"Ingress", "Egress"})
        for doc in docs:
            for rule in doc["spec"].get("egress") or []:
                for peer in rule.get("to") or []:
                    cidr = (peer.get("ipBlock") or {}).get("cidr")
                    self.assertNotEqual(cidr, "0.0.0.0/0", doc["metadata"]["name"])


class TerraformTest(unittest.TestCase):
    def setUp(self):
        self.text = "\n".join(p.read_text(encoding="utf-8") for p in (ROOT / "infra" / "aws" / "terraform").glob("*.tf"))

    def test_no_internet_path(self):
        for resource in ("aws_internet_gateway", "aws_nat_gateway", "aws_egress_only_internet_gateway", "aws_eip"):
            self.assertIsNone(re.search(rf'resource\s+"{resource}"', self.text), resource)
        self.assertIn("map_public_ip_on_launch = false", self.text)

    def test_endpoints_and_policies(self):
        self.assertIn("bedrock-runtime", self.text)
        self.assertIn("ApprovedModelsOnly", self.text)
        self.assertIn("aws:SourceVpce", self.text)
        self.assertIn("DenyInsecureTransport", self.text)
        self.assertIn('sse_algorithm     = "aws:kms"', self.text)
        self.assertIn("block_public_policy     = true", self.text)
        self.assertNotIn("aws_bedrock_model_invocation_logging_configuration", self.text)
        self.assertNotIn("aws_iam_access_key", self.text)

    def test_security_groups_have_no_open_egress(self):
        for block in re.findall(r'resource "aws_vpc_security_group_egress_rule"[^}]+}', self.text):
            self.assertNotIn("0.0.0.0/0", block)


class RailwayTest(unittest.TestCase):
    def test_railway_declares_no_resources(self):
        text = (ROOT / ".railway" / "railway.ts").read_text(encoding="utf-8")
        self.assertIn("resources: []", text)
        self.assertNotIn("service(", text)


if __name__ == "__main__":
    unittest.main()
