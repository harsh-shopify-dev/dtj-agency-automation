"""github_secrets.py against a stand-in `gh` (no network, no real repo, no Windows settings read).

    python -m unittest discover -s tools/team-setup -t tools/team-setup
"""
import contextlib
import io
import subprocess
import unittest

import github_secrets as gs

TOKEN = "1//refresh-must-never-be-printed-0123456789"


class FakeGh:
    def __init__(self, names=(), refuse=()):
        self.names, self.refuse, self.calls = set(names), set(refuse), []

    def __call__(self, args, stdin):
        self.calls.append((args, stdin))
        if args[:2] == ["secret", "list"]:
            return subprocess.CompletedProcess(args, 0, "".join(n + "\n" for n in sorted(self.names)), "")
        if args[:2] == ["secret", "set"]:
            if args[2] in self.refuse:
                return subprocess.CompletedProcess(args, 1, "", f"HTTP 403: no admin rights (body {stdin})")
            self.names.add(args[2])
            return subprocess.CompletedProcess(args, 0, "", "")
        raise AssertionError(f"unexpected gh call {args}")


def run(argv, fake, local):
    with contextlib.redirect_stdout(io.StringIO()) as out:
        code = gs.main(argv, run=fake, local=local)
    return code, out.getvalue()


class GithubSecrets(unittest.TestCase):
    def test_status_lists_names_only_and_exits_1_while_one_is_missing(self):
        fake = FakeGh(names={"DTJ_TELEGRAM_BOT_TOKEN"})
        code, text = run([], fake, {"DTJ_GDRIVE_REFRESH_TOKEN": TOKEN})
        self.assertEqual(code, 1)
        self.assertIn("DTJ_GDRIVE_REFRESH_TOKEN: NOT on GitHub, on this laptop", text)
        self.assertIn("DTJ_TELEGRAM_BOT_TOKEN: on GitHub, not on this laptop", text)
        self.assertNotIn(TOKEN, text)
        self.assertTrue(all(a[:2] == ["secret", "list"] for a, _ in fake.calls))  # status only reads

    def test_push_sends_values_through_stdin_never_the_command_line(self):
        fake = FakeGh(names={"DTJ_GDRIVE_CLIENT_ID"})
        local = {n: f"{TOKEN}-{n}" for n in gs.NEEDED}
        code, text = run(["push"], fake, local)
        self.assertEqual(code, 0, text)
        sets = [(a, s) for a, s in fake.calls if a[:2] == ["secret", "set"]]
        self.assertEqual([a[2] for a, _ in sets], list(gs.NEEDED))
        for args, stdin in sets:
            self.assertEqual(args, ["secret", "set", args[2], "--repo", gs.REPO])
            self.assertEqual(stdin, local[args[2]])
            self.assertFalse(any(TOKEN in a for a in args))
        self.assertIn("DTJ_GDRIVE_CLIENT_ID: replaced", text)
        self.assertIn("DTJ_GDRIVE_REFRESH_TOKEN: added", text)
        self.assertNotIn(TOKEN, text)

    def test_a_missing_value_or_a_refusal_is_reported_and_hidden(self):
        fake = FakeGh(refuse={"DTJ_GDRIVE_REFRESH_TOKEN"})
        code, text = run(["push", "DTJ_GDRIVE_REFRESH_TOKEN", "DTJ_GDRIVE_CLIENT_ID"], fake, {"DTJ_GDRIVE_REFRESH_TOKEN": TOKEN})
        self.assertEqual(code, 1)
        self.assertIn("DTJ_GDRIVE_REFRESH_TOKEN: GitHub refused: HTTP 403", text)
        self.assertIn("DTJ_GDRIVE_CLIENT_ID: not on this laptop", text)
        self.assertNotIn(TOKEN, text)

    def test_only_known_names_are_accepted(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            gs.main(["push", "DTJ_CATCHER_VAULT_KEY"], run=FakeGh(), local={})


if __name__ == "__main__":
    unittest.main()
