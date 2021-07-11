#! /usr/bin/env python3
import discord
from discord.ext import commands
import os
import traceback
import basic
from Tournament import reloadPresent

TOKEN = basic.DISCORD_TOKENS["beta"]  # beta
startup_extensions = ["Tournament"]  # cogの導入

description = ("`?open <1試合の人数> <最大参加人数>`でトーナメントを開催することができます。")

bot = commands.Bot(command_prefix='?', description=description)
commands.Context.tours = {}
commands.Context.onlyAdmin = (os.environ.get("bot_onlyAdmin", "true").lower() == "true")
commands.Context.gatherHere = (os.environ.get("bot_gatherHere", "true").lower() == "true")
commands.Context.roleIsValid = (os.environ.get("bot_roleIsValid", "false").lower() == "true")

commands.Context.members = {}



# # 起動時に動作する処理


@bot.event
async def on_ready():
    print(f"Logged in as\n{bot.user.name}\n{bot.user.id}\n------")


## メッセージ受信時に動作する処理
@bot.event
async def on_message(message):
    # メッセージ送信者がこのBotだった場合は無視する
    if message.author.id == bot.user.id:
        return
    # 管理者に制限されている場合、権限なしなら反応しない
    ctx = await bot.get_context(message)
    if ctx.onlyAdmin is True and not ctx.author.guild_permissions.administrator:
        return

    # bot.commandにmessageを流す
    try:
        await bot.process_commands(message)
    except (discord.ext.commands.errors.CommandNotFound, discord.ext.commands.errors.BadArgument) as e:
        pass
    except Exception as e:
        print(traceback.format_exc())
        #print(e)

async def react_reactions(payload):
    chan_tmp=await bot.fetch_channel(payload.channel_id)
    message_now=await chan_tmp.fetch_message(payload.message_id)
    ctx = await bot.get_context(message_now)
    valid_msg_ids = {tour["valid_ids"]["message"]: tour for tour in ctx.tours.values()}
    if message_now.id in [k for k in valid_msg_ids.keys()]:
        tour_now = valid_msg_ids[message_now.id]
        await reloadPresent(ctx, tour_now)

## reaction event
@bot.event
async def on_raw_reaction_add(payload):
    await react_reactions(payload)

@bot.event
async def on_raw_reaction_remove(payload):
    await react_reactions(payload)

## error時にprint
#@bot.event
#async def on_command_error(args, kwargs):
    #exc = sys.exc_info()
    #print(exc)



## cogを導入
if __name__ == "__main__":
    for extension in startup_extensions:
        try:
            bot.load_extension(extension)
        except Exception as e:
            exc = f'{e}: {e.args}'
            print(f'Failed to load extension {extension}\n{exc}')


## Botの起動とDiscordサーバーへの接続
bot.run(TOKEN)
