#! /usr/bin/env python3
import os

# tokenなどの変数を記録するファイル。

# heroku or not
IsHeroku = bool(os.getenv("DYNO", False))


DISCORD_TOKENS = {
    "alpha": 0,
    "beta": os.environ.get("discord_token_uma", os.environ.get["DISCORD_BOT_TOKEN"])}  # べーたのtoken


