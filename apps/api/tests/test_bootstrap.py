import unittest
from pathlib import Path

from app.bootstrap import load_schema, migration_files

SCHEMA = Path(__file__).resolve().parents[3] / "schema" / "schema.sql"


class BootstrapTest(unittest.TestCase):
    def test_splits_schema_into_statements(self):
        statements = load_schema(SCHEMA)
        self.assertGreater(len(statements), 20)
        self.assertTrue(statements[0].startswith('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
        self.assertTrue(statements[-1].startswith("CREATE INDEX audit_events_at"))
        self.assertTrue(all(";" not in statement for statement in statements))
        joined = "\n".join(statements)
        for token in (
            "CREATE TABLE briefings",
            "CREATE TABLE jobs",
            "CREATE TABLE claims",
            "CREATE TABLE workbook_rows",
            "vector(768)",
        ):
            self.assertIn(token, joined)

    def test_migrations_are_idempotent_ddl(self):
        files = migration_files(SCHEMA.parent / "migrations")
        self.assertTrue(files)
        for path in files:
            for statement in load_schema(path):
                head = statement.split()[0].upper()
                self.assertIn(head, {"ALTER", "CREATE", "DROP"}, statement[:60])
                if head == "CREATE":
                    self.assertIn("IF NOT EXISTS", statement.upper(), statement[:60])
                if head == "DROP":
                    self.assertIn("IF EXISTS", statement.upper(), statement[:60])
                if "ADD COLUMN" in statement.upper() or "ADD VALUE" in statement.upper():
                    self.assertIn("IF NOT EXISTS", statement.upper(), statement[:60])


if __name__ == "__main__":
    unittest.main()
