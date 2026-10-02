"""Both deployment profiles: offline and aws-private. Synthetic config only."""

import unittest

from grounded.policy import AWS_PRIVATE, OFFLINE, EgressError, assert_runtime, from_env, parse_aws_host

AWS_ENV = {
    "GROUNDED_DEPLOYMENT_MODE": "aws-private",
    "GROUNDED_AWS_REGIONS": "us-east-1",
    "GROUNDED_AWS_SERVICES": "bedrock-runtime,s3",
    "GROUNDED_BEDROCK_MODELS": "amazon.nova-pro-v1:0,amazon.nova-lite-v1:0,amazon.nova-2-multimodal-embeddings-v1:0",
    "GROUNDED_OBJECT_BUCKETS": "grounded-private-artifacts",
    "GROUNDED_AWS_ENDPOINTS": "https://vpce-0abc123-xyz.bedrock-runtime.us-east-1.vpce.amazonaws.com",
}

ARBITRARY = (
    "https://example.com/upload",
    "https://api.openai.com/v1/chat/completions",
    "https://api.anthropic.com/v1/messages",
    "https://api.elevenlabs.io/v1/text-to-speech",
    "https://huggingface.co/openai/whisper-base",
    "https://cdn.jsdelivr.net/npm/swagger-ui",
    "https://t3.storageapi.dev/bucket",
    "https://storage.googleapis.com/bucket",
    "https://8.8.8.8/",
    "https://evil.internal.example.com/",  # suffix trick: not *.internal
    "https://intake.posthog.com/",
)


class OfflineProfileTest(unittest.TestCase):
    def setUp(self):
        self.policy = from_env({"GROUNDED_DEPLOYMENT_MODE": "offline"})

    def test_default_is_offline(self):
        self.assertEqual(from_env({}).mode, OFFLINE)

    def test_private_destinations_allowed(self):
        for url in ("http://minio:9000", "http://10.2.3.4:11434", "http://127.0.0.1:8000",
                    "http://vllm.ml.svc.cluster.local:8000", "http://model.grounded.internal"):
            self.assertEqual(self.policy.check_url(url), url)

    def test_every_aws_endpoint_is_refused(self):
        for url in (
            "https://bedrock-runtime.us-east-1.amazonaws.com",
            AWS_ENV["GROUNDED_AWS_ENDPOINTS"],
            "https://s3.us-east-1.amazonaws.com",
            "https://transcribe.us-east-1.amazonaws.com",
            "https://polly.us-east-1.amazonaws.com",
        ):
            with self.assertRaises(EgressError, msg=url):
                self.policy.check_url(url)

    def test_bedrock_models_refused(self):
        with self.assertRaises(EgressError):
            self.policy.check_bedrock("amazon.nova-pro-v1:0", "us-east-1")

    def test_arbitrary_urls_blocked(self):
        for url in ARBITRARY:
            with self.assertRaises(EgressError, msg=url):
                self.policy.check_url(url)

    def test_public_object_store_refused(self):
        for endpoint in ("https://t3.storageapi.dev", "https://s3.us-east-1.amazonaws.com", "https://r2.cloudflarestorage.com"):
            with self.assertRaises(EgressError):
                self.policy.check_object_store(endpoint, "grounded")
        self.policy.check_object_store("http://minio:9000", "grounded")


class AwsPrivateProfileTest(unittest.TestCase):
    def setUp(self):
        self.policy = from_env(AWS_ENV)

    def test_mode(self):
        self.assertEqual(self.policy.mode, AWS_PRIVATE)

    def test_allowlisted_vpc_endpoint_accepted(self):
        url = AWS_ENV["GROUNDED_AWS_ENDPOINTS"]
        self.assertEqual(self.policy.check_url(url), url)
        self.policy.check_bedrock("amazon.nova-pro-v1:0", "us-east-1")

    def test_regional_name_needs_private_dns_declaration(self):
        url = "https://bedrock-runtime.us-east-1.amazonaws.com"
        with self.assertRaises(EgressError):
            self.policy.check_url(url)
        declared = from_env({**AWS_ENV, "GROUNDED_AWS_PRIVATE_DNS": "true"})
        self.assertEqual(declared.check_url(url), url)

    def test_other_region_refused(self):
        with self.assertRaises(EgressError):
            self.policy.check_url("https://vpce-0abc-1.bedrock-runtime.eu-west-1.vpce.amazonaws.com")
        with self.assertRaises(EgressError):
            self.policy.check_bedrock("amazon.nova-pro-v1:0", "us-west-2")

    def test_unlisted_model_refused(self):
        for model in ("amazon.nova-premier-v1:0", "anthropic.claude-3-5-sonnet-20241022-v2:0", "", "us.amazon.nova-pro-v1:0"):
            with self.assertRaises(EgressError, msg=model):
                self.policy.check_bedrock(model, "us-east-1")

    def test_unapproved_aws_services_refused(self):
        for url in (
            "https://vpce-1.transcribe.us-east-1.vpce.amazonaws.com",
            "https://vpce-1.polly.us-east-1.vpce.amazonaws.com",
            "https://vpce-1.sagemaker.us-east-1.vpce.amazonaws.com",
            "https://sts.amazonaws.com",
            "https://console.aws.amazon.com",
        ):
            with self.assertRaises(EgressError, msg=url):
                self.policy.check_url(url)

    def test_services_outside_ceiling_cannot_be_approved(self):
        with self.assertRaises(EgressError):
            from_env({**AWS_ENV, "GROUNDED_AWS_SERVICES": "bedrock-runtime,transcribe"})
        with self.assertRaises(EgressError):
            from_env({**AWS_ENV, "GROUNDED_AWS_SERVICES": "polly"})

    def test_s3_bucket_allowlist(self):
        endpoint = "https://bucket.vpce-0abc-1.s3.us-east-1.vpce.amazonaws.com"
        self.policy.check_object_store(endpoint, "grounded-private-artifacts")
        with self.assertRaises(EgressError):
            self.policy.check_object_store(endpoint, "someone-elses-bucket")
        with self.assertRaises(EgressError):
            self.policy.check_object_store("https://s3.us-east-1.amazonaws.com", "grounded-private-artifacts")

    def test_arbitrary_urls_blocked(self):
        for url in ARBITRARY:
            with self.assertRaises(EgressError, msg=url):
                self.policy.check_url(url)

    def test_aws_private_requires_explicit_allowlists(self):
        with self.assertRaises(EgressError):
            from_env({"GROUNDED_DEPLOYMENT_MODE": "aws-private"})
        with self.assertRaises(EgressError):
            from_env({"GROUNDED_DEPLOYMENT_MODE": "aws-private", "GROUNDED_AWS_REGIONS": "us-east-1"})


class EscapeHatchTest(unittest.TestCase):
    def test_unknown_or_retired_modes_fail_closed(self):
        for mode in ("aws-in-region", "public", "online", "hybrid"):
            with self.assertRaises(EgressError, msg=mode):
                from_env({"GROUNDED_DEPLOYMENT_MODE": mode})

    def test_public_egress_switch_is_retired(self):
        for value in ("1", "true", "yes"):
            with self.assertRaises(EgressError):
                from_env({"GROUND_ALLOW_PUBLIC_EGRESS": value})

    def test_hosted_runtimes_refused(self):
        with self.assertRaises(EgressError):
            assert_runtime(env={"RAILWAY_ENVIRONMENT": "production"})
        with self.assertRaises(EgressError):
            assert_runtime(env={**AWS_ENV, "VERCEL": "1"})

    def test_startup_rejects_public_infrastructure(self):
        with self.assertRaises(EgressError):
            assert_runtime(("DATABASE_URL", "postgresql://u:p@db.example.com:5432/x"), env={})
        with self.assertRaises(EgressError):
            assert_runtime(("REDIS_URL", "redis://redis.example.com:6379/0"), env=AWS_ENV)
        assert_runtime(("DATABASE_URL", "postgresql://u:p@postgres:5432/x"), ("REDIS_URL", "redis://redis:6379/0"), env={})


class HostParsingTest(unittest.TestCase):
    def test_parse(self):
        parsed = parse_aws_host("vpce-0abc-xyz.bedrock-runtime.us-east-1.vpce.amazonaws.com")
        self.assertEqual((parsed.service, parsed.region, parsed.vpce), ("bedrock-runtime", "us-east-1", True))
        s3 = parse_aws_host("my-bucket.s3.eu-west-1.amazonaws.com")
        self.assertEqual((s3.service, s3.bucket), ("s3", "my-bucket"))
        self.assertIsNone(parse_aws_host("example.com"))


if __name__ == "__main__":
    unittest.main()
