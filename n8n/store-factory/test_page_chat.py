"""page_chat.py: a message about a page always ends with the line a reply is routed by; nothing reaches Telegram here.

    python -m unittest discover -s n8n/store-factory -t n8n/store-factory -p "test_page_chat.py"
"""
import re
import unittest

import page_chat

READ = re.compile(r"\(job ([a-z0-9][a-z0-9-]{1,23}), answer ([a-z0-9_]{1,20})\)\s*$")  # bot_read.js reads a reply's message so


class Send(unittest.TestCase):
    def test_the_message_ends_with_the_reply_line_the_bot_reads(self):
        sent = []
        ok = page_chat.send("7051933055", "12", "Hero now leads with protein.\nPreview: https://x", token="t",
                            post=lambda url, data: sent.append((url, data)) or (200, {}))
        self.assertTrue(ok)
        url, data = sent[0]
        self.assertTrue(url.endswith("/bott/sendMessage"))
        self.assertEqual(READ.search(data["text"]).groups(), ("page-12", "chat"))
        self.assertTrue(data["text"].startswith("Hero now leads with protein."))

    def test_nothing_is_sent_without_a_token_or_with_a_wrong_chat_or_brief(self):
        post = lambda url, data: (_ for _ in ()).throw(AssertionError("sent"))  # noqa: E731
        self.assertFalse(page_chat.send("7051933055", "12", "x", token="", post=post))
        self.assertFalse(page_chat.send("not-a-chat", "12", "x", token="t", post=post))
        self.assertFalse(page_chat.send("7051933055", "12; rm", "x", token="t", post=post))


if __name__ == "__main__":
    unittest.main()
