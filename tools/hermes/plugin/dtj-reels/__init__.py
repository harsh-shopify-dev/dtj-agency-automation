"""Hermes plugin dtj-reels: the Hermes reel bot handles a reel's buttons and answers itself (Harsh, 26 Oct 2026: "i want only that
bot to handle everything").

Only on the reel bot (the profile ugc_generation_automation's own Telegram bot; every other Hermes bot is left alone) it catches:
- a reel job's button tap ("a:<job>:<key>:<n>": the worker's Start / Stop, the plan / pictures / final Approve, Keep / Skip)
- a reply to a reel job's typed question (its last line "(job <job>, answer <key>)")
- the reel commands /remake /reel /refs /audience /reels
and hands the Telegram update, as it came, to `dtj tg` (tools/hermes/dtj.py on DTJ's VPS), which runs the reel bot's own rules and
saves the answer where the worker and reel_job.py read it. Everything else goes to Hermes as usual.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from pathlib import Path

log = logging.getLogger("dtj-reels")
PROFILE = Path("/opt/data/profiles/ugc_generation_automation")
DTJ = PROFILE / "dtj" / "dtj"
TAP = r"^a:[a-z0-9][a-z0-9-]{1,23}:[a-z0-9_]{1,20}:\d{1,2}$"
QUESTION = re.compile(r"\(job ([a-z0-9][a-z0-9-]{1,23}), answer ([a-z0-9_]{1,20})\)\s*$")
COMMANDS = ["remake", "reel", "refs", "audience", "reels"]


def reel_bot_id() -> str:
    """The reel profile's bot id (the part of its token before ':'), read from its .env; the token itself is never kept."""
    try:
        for line in (PROFILE / ".env").read_text(encoding="utf-8").splitlines():
            if line.startswith("TELEGRAM_BOT_TOKEN="):
                return line.split("=", 1)[1].strip().strip('"').strip("'").split(":", 1)[0]
    except OSError:
        pass
    return ""


async def ask_dtj(update_dict: dict, user) -> str:
    env = {**os.environ, "HERMES_SESSION_USER_ID": str(user.id), "HERMES_SESSION_PLATFORM": "telegram",
           "HERMES_SESSION_USER_NAME": " ".join(x for x in (user.first_name, user.last_name) if x) or (user.username or "")}
    proc = await asyncio.create_subprocess_exec(str(DTJ), "tg", json.dumps(update_dict, ensure_ascii=False, separators=(",", ":")),
                                                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, env=env)
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout=90)
    except asyncio.TimeoutError:
        proc.kill()
        return "That did not go through (no answer in 90 s). Please try again."
    try:
        return str(json.loads(out.decode("utf-8", "replace").strip().splitlines()[-1]).get("say") or "")
    except (ValueError, IndexError):
        log.warning("dtj tg gave no answer: %s", err.decode("utf-8", "replace")[-300:])
        return "That did not go through. Please try again in a minute."


def factory(app, adapter) -> None:
    from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler, filters

    mine = reel_bot_id()
    if not mine or str(getattr(app.bot, "token", "")).split(":", 1)[0] != mine:
        return  # not the reel bot: nothing is registered on this bot

    class ReelQuestionReply(filters.MessageFilter):
        def filter(self, message) -> bool:
            asked = message.reply_to_message
            return bool(asked and asked.from_user and asked.from_user.is_bot and message.text and not message.text.startswith("/")
                        and QUESTION.search(asked.text or ""))

    async def on_tap(update, context) -> None:
        q = update.callback_query
        try:
            await q.answer()
        except Exception:  # noqa: BLE001  the spinner only
            pass
        say = await ask_dtj(update.to_dict(), q.from_user)
        if say and q.message:
            await context.bot.send_message(q.message.chat_id, say)

    async def on_message(update, context) -> None:
        say = await ask_dtj(update.to_dict(), update.effective_user)
        if say:
            await context.bot.send_message(update.effective_chat.id, say)

    app.add_handler(CallbackQueryHandler(on_tap, pattern=TAP))
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & ReelQuestionReply(), on_message))
    app.add_handler(CommandHandler(COMMANDS, on_message, filters=filters.ChatType.PRIVATE))
    log.info("dtj-reels: reel buttons, question replies and /%s handled on the reel bot", " /".join(COMMANDS))


def register(ctx) -> None:
    ctx.register_telegram_handler(factory)
