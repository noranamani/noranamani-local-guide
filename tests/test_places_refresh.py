"""Regression tests for source-scoped place replacement (no network calls)."""
import copy
import unittest

from localguide.core import GuideError
from localguide.places import ensure_event_place_references, replace_places


def place(pid, sid, extra_sources=()):
    return {"place_id": pid, "name": "fixture " + pid,
            "sources": [{"source_id": x} for x in (sid, *extra_sources)]}


class PlaceRefreshTests(unittest.TestCase):
    def test_removes_missing_rows_in_successful_same_source_snapshot(self):
        result = replace_places([place("A", "one"), place("B", "one"), place("C", "other")],
                                [place("A", "one")], "one")
        self.assertEqual([p["place_id"] for p in result], ["C", "A"])

    def test_does_not_remove_other_sources_with_same_names(self):
        original = [place("X", "other")]
        incoming = [place("Y", "one")]
        self.assertEqual([p["place_id"] for p in replace_places(original, incoming, "one")], ["X", "Y"])

    def test_snapshot_update_keeps_old_and_incoming_immutable(self):
        old = [place("A", "one")]
        incoming = [place("A", "one")]
        expected_old, expected_incoming = copy.deepcopy(old), copy.deepcopy(incoming)
        result = replace_places(old, incoming, "one")
        result[0]["sources"][0]["source_id"] = "modified"
        self.assertEqual(old, expected_old)
        self.assertEqual(incoming, expected_incoming)

    def test_duplicate_incoming_ids_rejected(self):
        with self.assertRaises(GuideError):
            replace_places([], [place("A", "one"), place("A", "one")], "one")

    def test_wrong_source_in_incoming_rejected(self):
        with self.assertRaises(GuideError):
            replace_places([], [place("A", "other")], "one")

    def test_multiple_provenances_must_not_be_erased(self):
        with self.assertRaises(GuideError):
            replace_places([place("A", "one", ("other",))], [], "one")

    def test_collision_with_other_sources_rejected(self):
        with self.assertRaises(GuideError):
            replace_places([place("A", "other")], [place("A", "one")], "one")

    def test_stale_event_reference_is_rejected(self):
        with self.assertRaises(GuideError):
            ensure_event_place_references([place("A", "one")], [{"place_id": "B"}])

    def test_null_event_place_reference_allowed(self):
        ensure_event_place_references([], [{"place_id": None}, {"place_id": ""}])

    def test_existing_event_reference_retained(self):
        ensure_event_place_references([place("A", "one")], [{"place_id": "A"}])


if __name__ == "__main__":
    unittest.main()
