"""The product page's own questions (page_questions.py): ChatGPT pictures and the competitor study, asked in Telegram after the Start
tap, the same buttons as a whole store (Harsh, 23 Oct 2026). Stand-in Telegram and answers table; nothing reaches Telegram or n8n.

    python -m unittest discover -s n8n/store-factory -t n8n/store-factory -p "test_page_questions.py"
"""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import page_questions
import store_job
import worker
from test_store_job import CHAT, Answers, Clock, Telegram


class PageQuestions(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.tg, self.answers, self.clock, self.printed = Telegram(), Answers(), Clock(), []

    def job(self):
        return page_questions.page_job("9", CHAT, send=self.tg, rows=self.answers, state_dir=self.tmp, add_row=None,
                                       out=self.printed.append, sleep=self.clock.sleep, clock=self.clock)

    def test_pictures_then_the_study_then_one_json_line(self):
        j = self.job()
        self.assertEqual(page_questions.ask(j, 1), store_job.WAITING)
        self.assertIn("Should ChatGPT make new pictures for this page?", self.tg.questions()[0]["text"])
        self.assertEqual(self.tg.questions()[0]["reply_markup"]["inline_keyboard"][0][0]["callback_data"], "a:p9:pictures:0")
        for label in ("Yes: make them and add them to the page", "Yes: find them yourself", "Everything", "I'll type it"):
            self.answers.tap(self.tg, label)
            page_questions.ask(self.job(), 1)
        self.answers.type(self.tg, "how they show the protein per scoop")
        self.assertEqual(page_questions.ask(self.job(), 1), 0)
        out = json.loads(self.printed[-1])
        self.assertEqual((out["pictures"], out["pictures_by"]), ("make", "Harsh"))
        self.assertEqual(out["competitors"], {"how": "find", "focus": list(store_job.FOCUS), "note": "how they show the protein per scoop"})
        self.assertIn("that is all I need", self.tg.last()["text"])
        asked = len(self.tg.questions())
        self.assertEqual(page_questions.ask(self.job(), 1), 0)  # a rerun asks nothing again
        self.assertEqual(len(self.tg.questions()), asked)

    def test_the_study_is_kept_and_sent(self):
        j = self.job()
        page_questions.ask(j, 1)
        for label in ("No: the product's own pictures", "Yes: find them yourself", "Only what I type"):
            self.answers.tap(self.tg, label)
            page_questions.ask(self.job(), 1)
        self.answers.type(self.tg, "their bundles")
        page_questions.ask(self.job(), 1)
        f = self.tmp / "study.md"
        f.write_text("# Your request\n" + "They sell 3-packs; we show only our own pack sizes and prices. " * 5, encoding="utf-8")
        self.assertEqual(self.job().study(f), 0)
        self.assertIn("Competitor study for <b>brief 9</b>", self.tg.last()["text"])

    def test_the_worker_may_keep_its_wait(self):
        argv, why = worker.wait_command("DTJ_WAIT: python n8n/store-factory/page_questions.py --brief 9 --chat 7051933055")
        self.assertEqual((argv[1:3], why), (["n8n/store-factory/page_questions.py", "--brief"], ""))
        self.assertEqual(argv[-2:], ["--minutes", worker.WAIT_MINUTES])


if __name__ == "__main__":
    unittest.main()
