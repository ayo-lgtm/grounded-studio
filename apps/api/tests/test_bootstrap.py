import unittest
from pathlib import Path

from app.bootstrap import load_schema

SCHEMA = Path(__file__).resolve().parents[3] / "schema" / "schema.sql"


class BootstrapTest(unittest.TestCase):
    def test_splits_schema_into_statements(self):
        statements = load_schema(SCHEMA)
        self.assertGreater(len(statements), 20)
        self.assertTrue(statements[0].startswith('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
        self.assertTrue(statements[-1].startswith("CREATE INDEX audit_events_at"))
        self.assertTrue(all(";" not in statement for statement in statements))
        joined = "\n".join(statements)
        for token in ("CREATE TABLE briefings", "CREATE TABLE jobs", "VECTOR(768)"):
            self.assertIn(token, joined)


if __name__ == "__main__":
    unittest.main()
