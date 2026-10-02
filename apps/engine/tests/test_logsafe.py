"""Sensitive source content never reaches application logs."""

import io
import logging
import unittest

from grounded import logsafe

SECRET = "CONFIDENTIAL-Q3-margin-31.4%-Project-Falcon"


class LogSafeTest(unittest.TestCase):
    def setUp(self):
        self.stream = io.StringIO()
        self.handler = logging.StreamHandler(self.stream)
        logging.getLogger().addHandler(self.handler)
        logging.getLogger().setLevel(logging.DEBUG)
        logsafe.configure()

    def tearDown(self):
        logging.getLogger().removeHandler(self.handler)

    def test_unknown_fields_dropped(self):
        record = logsafe.log_event("compile.done", briefing_id="b1", text=SECRET, prompt=SECRET, beats=4)
        self.assertNotIn("text", record)
        self.assertNotIn("prompt", record)
        self.assertNotIn(SECRET, self.stream.getvalue())

    def test_long_values_redacted_even_in_safe_fields(self):
        logsafe.log_event("x", skill_id=SECRET * 3, error_class="ValueError")
        self.assertNotIn(SECRET, self.stream.getvalue())

    def test_failures_log_class_not_message(self):
        try:
            raise ValueError(f"cell KPI!B4 says {SECRET}")
        except ValueError as exc:
            logsafe.log_failure("job.failed", exc, job_id="j1")
        out = self.stream.getvalue()
        self.assertIn("ValueError", out)
        self.assertNotIn(SECRET, out)

    def test_sdk_debug_wire_logging_suppressed(self):
        logging.getLogger("botocore.endpoint").debug("Making request ... body=%s", SECRET)
        logging.getLogger("urllib3.connectionpool").debug("POST %s", SECRET)
        self.assertGreaterEqual(logging.getLogger("botocore").level, logging.WARNING)
        root_handlers = [h for h in logging.getLogger().handlers if getattr(h, "_grounded", False)]
        self.assertTrue(root_handlers)
        record = logging.LogRecord("botocore.endpoint", logging.DEBUG, "f", 1, SECRET, (), None)
        self.assertFalse(root_handlers[0].filters[0].filter(record))


if __name__ == "__main__":
    unittest.main()
