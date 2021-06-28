#! /usr/bin/env python3
import os

# tokenなどの変数を記録するファイル。

# heroku or not
IsHeroku = bool(os.getenv("DYNO", False))


DISCORD_TOKENS = {
    "alpha": 0,
    "beta": os.environ["discord_token_uma_alpha"]}  # べーたのtoken

ids = {
    "account": {"alpha": 857220750549450782, "beta": 857220750549450782}
}


