#!/usr/bin/env python3
"""Regression tests for refute_log.py. Run: python3 refute_log.test.py"""

import contextlib
import datetime
import importlib.util
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "refute_log", os.path.join(HERE, "refute_log.py")
)
refute_log = importlib.util.module_from_spec(spec)
spec.loader.exec_module(refute_log)

NOW = datetime.datetime(2026, 10, 12, 9, 0, tzinfo=datetime.timezone.utc)


def hours(n):
    return NOW + datetime.timedelta(hours=n)


class LogCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = os.path.realpath(tmp.name)
        self.log = os.path.join(self.dir, refute_log.NAME)
        self.file = os.path.join(self.dir, "CLAUDE.md")
        open(self.file, "w").close()

    def record(self, target=None, verdict="reviewed", at=NOW, **kw):
        fields = {"changes": 1, "changed": 0, "tokens": None, "note": ""}
        fields.update(kw)
        return refute_log.record(
            [target or self.file], verdict, now=at, log=self.log, **fields
        )

    def cleared(self, path=None, at=NOW):
        return refute_log.cleared(path or self.file, now=at, candidates=[self.log])


class Cleared(LogCase):
    def test_a_missing_log_clears_nothing(self):
        self.assertFalse(self.cleared())

    def test_a_review_clears_its_target_and_no_other_file(self):
        self.record()
        self.assertTrue(self.cleared())
        self.assertFalse(self.cleared(os.path.join(self.dir, "other", "CLAUDE.md")))

    def test_a_skip_clears_one_edit(self):
        self.record(verdict="skipped", note="link fix")
        self.assertTrue(self.cleared())
        refute_log.passed(self.file, now=hours(1), log=self.log)
        self.assertFalse(self.cleared(at=hours(2)))
        self.record(verdict="skipped", note="second typo", at=hours(3))
        self.assertTrue(self.cleared(at=hours(4)))

    def test_a_review_clears_every_edit_in_its_window(self):
        self.record()
        for n in (1, 2, 3):
            refute_log.passed(self.file, now=hours(n), log=self.log)
        self.assertTrue(self.cleared(at=hours(4)))

    def test_a_carried_review_clears_like_a_review(self):
        self.record(verdict="carried", note="stands from 2026-10-09")
        refute_log.passed(self.file, now=hours(1), log=self.log)
        self.assertTrue(self.cleared(at=hours(2)))

    def test_a_review_older_than_the_window_no_longer_clears(self):
        self.record()
        self.assertTrue(self.cleared(at=hours(refute_log.WINDOW_HOURS)))
        self.assertFalse(self.cleared(at=hours(refute_log.WINDOW_HOURS + 1)))

    def test_a_review_dated_after_now_does_not_clear(self):
        self.record(at=hours(2))
        self.assertFalse(self.cleared())

    def test_a_symlinked_path_matches_the_file_it_points_at(self):
        link = os.path.join(self.dir, "link.md")
        os.symlink(self.file, link)
        self.record(target=link)
        self.assertTrue(self.cleared())

    def test_unreadable_lines_are_passed_over(self):
        with open(self.log, "w") as fh:
            fh.write('not json\n[1]\n{"targets": ["x"], "at": "never"}\n')
        self.record()
        self.assertTrue(self.cleared())

    def test_any_candidate_log_can_clear(self):
        self.record()
        missing = os.path.join(self.dir, "none.jsonl")
        self.assertTrue(
            refute_log.cleared(self.file, now=NOW, candidates=[missing, self.log])
        )


class Logs(unittest.TestCase):
    def test_the_profile_log_comes_first_then_the_default(self):
        with mock.patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": "/work/.claude"}):
            first, second = refute_log.logs()
        self.assertEqual(str(first), f"/work/.claude/{refute_log.NAME}")
        self.assertEqual(
            str(second), os.path.expanduser(f"~/.claude/{refute_log.NAME}")
        )

    def test_the_default_profile_has_one_log(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("CLAUDE_CONFIG_DIR", None)
            self.assertEqual(len(refute_log.logs()), 1)


class Passed(LogCase):
    def test_an_edit_let_through_is_logged_and_clears_nothing(self):
        refute_log.passed(self.file, now=NOW, log=self.log)
        self.assertFalse(self.cleared())
        self.assertEqual(refute_log.entries(self.log)[0]["verdict"], refute_log.EDIT)


class Summary(LogCase):
    def summary(self):
        return refute_log.summary(refute_log.entries(self.log))

    def test_counts_cost_and_edits_and_lists_every_entry_with_its_note(self):
        self.record(changes=13, changed=4, tokens=390000, note="G1 to W5")
        self.record(changes=1, changed=0, tokens=110000, at=hours(1), note="B1")
        self.record(verdict="skipped", note="link fix", at=hours(2))
        self.record(verdict="carried", note="G1 to W5, from 10-12", at=hours(30))
        for n in (3, 4, 5):
            refute_log.passed(self.file, now=hours(n), log=self.log)
        self.assertEqual(
            self.summary(),
            [
                "reviews      2",
                f"  2026-10-12  {self.file}: G1 to W5",
                f"  2026-10-12  {self.file}: B1",
                "changes      4 of 14 drew an objection that held",
                "tokens       500,000 over 2 costed reviews (250,000 a review, 35,714 a change)",
                "edits        3 let through, against 14 changes reviewed",
                "skips        1",
                f"  2026-10-12  {self.file}: link fix",
                "carried      1",
                f"  2026-10-13  {self.file}: G1 to W5, from 10-12",
                "since        2026-10-12",
            ],
        )

    def test_a_review_without_a_token_figure_is_left_out_of_the_cost(self):
        self.record(changes=2, changed=1, tokens=100000)
        self.record(changes=5, changed=0, at=hours(1))
        self.assertIn(
            "100,000 over 1 costed reviews (100,000 a review, 50,000 a change)",
            "\n".join(self.summary()),
        )

    def test_since_keeps_the_entries_dated_on_or_after_the_day(self):
        self.record(note="before")
        self.record(note="on the day", at=hours(24))
        self.record(note="after", at=hours(72))
        found = refute_log.entries(self.log)
        kept = refute_log.since(found, "2026-10-13")
        self.assertEqual([e["note"] for e in kept], ["on the day", "after"])
        self.assertEqual(refute_log.since(found, ""), found)

    def test_an_empty_log_reports_zeroes(self):
        self.assertEqual(
            refute_log.summary([]),
            [
                "reviews      0",
                "edits        0 let through, against 0 changes reviewed",
                "skips        0",
                "carried      0",
            ],
        )


class Cli(LogCase):
    def run_cli(self, *args):
        argv = ["refute_log.py", *args]
        with (
            mock.patch.object(sys, "argv", argv),
            mock.patch.object(refute_log, "logs", return_value=[self.log]),
        ):
            return refute_log.main()

    def test_an_entry_without_a_note_is_refused(self):
        for verdict in refute_log.VERDICTS:
            with (
                self.assertRaises(SystemExit),
                contextlib.redirect_stderr(io.StringIO()),
            ):
                self.run_cli("record", "--target", self.file, "--verdict", verdict)
        self.assertEqual(refute_log.entries(self.log), [])

    def test_the_script_names_no_instruction_file(self):
        # The instruction-file gate holds any run of a script whose text names one.
        text = Path(HERE, "refute_log.py").read_text(encoding="utf-8")
        for literal in ("CLAUDE" + ".md", "SKILL" + ".md", "/skills/", "/hooks/"):
            self.assertNotIn(literal, text)

    def test_a_token_figure_per_refuter_is_summed(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.run_cli(
                "record",
                *("--target", self.file, "--verdict", "reviewed", "--note", "L1"),
                *("--tokens", "100", "--tokens", "20", "--tokens", "3"),
            )
        self.assertEqual(refute_log.entries(self.log)[0]["tokens"], 123)

    def test_a_skip_with_a_reason_is_logged(self):
        with contextlib.redirect_stdout(io.StringIO()):
            code = self.run_cli(
                "record",
                "--target",
                self.file,
                "--verdict",
                "skipped",
                "--note",
                "typo",
            )
        self.assertEqual(code, 0)
        self.assertEqual(refute_log.entries(self.log)[0]["note"], "typo")


if __name__ == "__main__":
    unittest.main()
