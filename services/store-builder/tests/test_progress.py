"""The brand intake's live progress bar in Telegram (Harsh, 19 Oct 2026: "add a progress bar or time duration in the telegram bot").
Telegram is a stand-in here: nothing is sent."""
import contextlib
import io
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from page_builder import brand_intake, progress  # noqa: E402
from page_builder.drive_upload import Drive  # noqa: E402
from page_builder.progress import Progress, bar, took  # noqa: E402

TOKEN = "123456:TEST-token-must-never-be-printed"


class FakeTelegram:
    def __init__(self, status=200):
        self.calls, self.status = [], status

    def __call__(self, url, data):
        self.calls.append((url.rsplit("/", 1)[1], dict(data)))
        if self.status != 200:
            return self.status, {}
        return 200, {"ok": True, "result": {"message_id": 77}}

    def texts(self):
        return [d["text"] for _, d in self.calls]


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


class ProgressTests(unittest.TestCase):
    def test_the_bar_and_the_time_read_plainly(self):
        self.assertEqual(bar(0), "░░░░░░░░░░ 0%")
        self.assertEqual(bar(70), "███████░░░ 70%")
        self.assertEqual(bar(100), "██████████ 100%")
        self.assertEqual(took(45.4), "45 s")
        self.assertEqual(took(125), "2 min 05 s")

    def test_one_message_is_sent_then_edited_at_most_every_few_seconds_and_ends_with_the_time(self):
        tg, clock = FakeTelegram(), Clock()
        p = Progress("freesoul.com", token=TOKEN, chat="555", post=tg, clock=clock)
        p.start()
        p.update("products", 3, 20)  # too soon after the first message: no edit
        clock.now += 5
        p.update("products", 14, 20)
        clock.now += 1
        p.update("products", 15, 20)  # too soon again
        clock.now += 60
        spent = p.finish(True)
        self.assertEqual([m for m, _ in tg.calls], ["sendMessage", "editMessageText", "editMessageText"])
        self.assertTrue(tg.calls[0][1]["disable_notification"])  # the progress message itself does not buzz the phone
        self.assertEqual({d.get("message_id") for m, d in tg.calls[1:]}, {77})
        self.assertIn("Brand intake: freesoul.com\n█████░░░░░ 52%\nDownloading pictures and videos: product 14 of 20\nTime so far: 5 s",
                      tg.texts()[1])  # 10 + 60 * 14/20
        self.assertIn("██████████ 100%\nDone in 1 min 06 s.", tg.texts()[2])
        self.assertEqual(spent, "1 min 06 s")

    def test_without_a_token_or_chat_nothing_is_sent_but_the_time_is_still_counted(self):
        tg, clock = FakeTelegram(), Clock()
        with mock.patch.dict(os.environ, {"DTJ_TELEGRAM_BOT_TOKEN": "", "DTJ_PROGRESS_CHAT": ""}):
            p = Progress("freesoul.com", post=tg, clock=clock)
        p.start()
        p.update("drive", 5, 10)
        clock.now += 30
        self.assertEqual(p.finish(True), "30 s")
        self.assertEqual(tg.calls, [])

    def test_a_telegram_error_never_stops_the_intake_never_shows_the_token_and_it_stops_trying_after_three(self):
        tg, clock = FakeTelegram(status=401), Clock()
        p = Progress("freesoul.com", token=TOKEN, chat="555", post=tg, clock=clock)
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            p.start()
            p.message_id = 77  # pretend the first message went out, so edits are tried
            for _ in range(6):
                clock.now += 10
                p.update("drive", 1, 2)
                p.update("drive", 2, 2)
            p.finish(False)
        self.assertEqual(len(tg.calls), 3)
        self.assertIn("Telegram answered 401 (the intake goes on)", printed.getvalue())
        self.assertNotIn(TOKEN, printed.getvalue())

    def test_a_stopped_intake_says_how_long_it_ran(self):
        tg, clock = FakeTelegram(), Clock()
        p = Progress("freesoul.com", token=TOKEN, chat="555", post=tg, clock=clock)
        p.start()
        clock.now += 12
        p.finish(False)
        self.assertEqual(tg.texts()[-1], "Brand intake: freesoul.com\nStopped after 12 s.\nThe next message says why.")


class IntakeProgressTests(unittest.TestCase):
    def test_a_real_intake_moves_through_every_stage_in_order_and_github_gets_the_time(self):
        from test_brand_intake import BASE, store  # noqa: PLC0415
        from test_drive_upload import KEYS, FakeDrive  # noqa: PLC0415
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        get, _ = store(n_products=3)
        tg = FakeTelegram()
        heard = []
        real_update = Progress.update

        def spy(self, stage, done=0, total=0):
            heard.append((stage, done, total))
            return real_update(self, stage, done, total)

        gh_out = tmp / "out.txt"
        env = {"DTJ_TELEGRAM_BOT_TOKEN": TOKEN, "DTJ_PROGRESS_CHAT": "555", "GITHUB_OUTPUT": str(gh_out)}
        with mock.patch.object(brand_intake, "POLITE_DELAY", 0), mock.patch.dict(os.environ, env), \
                mock.patch.object(progress, "_post", tg), mock.patch.object(Progress, "update", spy), \
                mock.patch.object(Progress.__init__, "__defaults__", (None, None, tg, progress.time.monotonic, 0.0)), \
                contextlib.redirect_stdout(io.StringIO()):
            code = brand_intake.main([BASE, "--client", str(tmp / "c"), "--drive", "DTJ Clients"], get=get, drive=Drive(KEYS, FakeDrive()))
        self.assertEqual(code, 0)
        stages = [s for s, _, _ in heard]
        self.assertEqual(sorted(set(stages), key=stages.index), ["read", "products", "extras", "write", "drive"])
        self.assertIn(("products", 3, 3), heard)
        files = [(d, t) for s, d, t in heard if s == "drive"]
        self.assertEqual(files[-1][0], files[-1][1])  # every file counted
        self.assertEqual(tg.calls[0][0], "sendMessage")
        self.assertIn("100%", tg.texts()[-1])
        self.assertNotIn(TOKEN, "".join(tg.texts()))
        self.assertRegex(gh_out.read_text(encoding="utf-8"), r"took=\d+ s\n")


if __name__ == "__main__":
    unittest.main()
