#! /usr/bin/env python3
import os
import shutil
import subprocess
import discord
from discord.ext import commands
import math
import random

# tokenなどの変数を記録するファイル。

DISCORD_TOKENS = {
    "alpha": 0,
    "beta": os.environ["discord_token_uma_alpha"]}  # べーたのtoken

ids = {
    "channel": {"test": 507977757083303952, "mcs_bot": 697690942903287808, "test2": 673203971988652062,
                "rename_test": 507977757083303952, "beta": 748469860689903656, "alpha": 673250216975269888},
    "account": {"alpha": 857220750549450782, "beta": 857220750549450782, "tomo": 349102495114592258},
    "guild": {"experiment": 505977333182758913}
}


