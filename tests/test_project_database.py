import tempfile
import unittest
from pathlib import Path
from cineforge.project_database import save_project_record, list_project_records, load_project_record


class ProjectDatabaseTests(unittest.TestCase):
    def test_round_trip_and_update(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "projects.sqlite3"
            first = {"original_prompt": "A moonlit city", "scenes": [{"title": "Arrival"}]}
            save_project_record(db, "moonlit_city", "Moonlit City", first)
            self.assertEqual(load_project_record(db, "moonlit_city"), first)
            updated = {"original_prompt": "A new city", "scenes": [{"title": "Opening"}]}
            save_project_record(db, "moonlit_city", "Moonlit City", updated)
            self.assertEqual(load_project_record(db, "moonlit_city"), updated)
            self.assertEqual(len(list_project_records(db)), 1)

    def test_missing_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(KeyError):
                load_project_record(Path(tmp) / "db.sqlite3", "missing")


if __name__ == "__main__":
    unittest.main()
