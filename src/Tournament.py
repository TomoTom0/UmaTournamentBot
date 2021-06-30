import discord
from discord.ext import commands
import time
import random
import re
import math
import datetime
import warnings
import traceback

#import basic

# # fucntions


def divideIntoGroup(membersIn, number, maxNumber, forceAll=False):
    members = random.sample(membersIn, len(membersIn))
    group_nums = judgeGroup(len(members), number, forceAll)
    #groupNum = (len(members)-1)//number+1
    return [members[sum(group_nums[0:grp_ind]):sum(group_nums[0:grp_ind+1])] for grp_ind in range(len(group_nums))]


async def cancelTour(ctx: commands.Context, tour_id):
    tour_now = ctx.tours.pop(tour_id)
    valid_channels = [
        chan for chan in ctx.guild.channels
        if chan.id in tour_now["channel_ids"].values()
        and chan.category is not None
        and chan.category.name == f"Tour_{tour_id}"]
    for chan_tmp in valid_channels:
        await chan_tmp.delete()
    valid_categories = [
        cat for cat in ctx.guild.categories if cat.id in tour_now["category_ids"].values()]
    for cat_tmp in valid_categories:
        await cat_tmp.delete()
    for role in tour_now["roles"].values():
        await role.delete()


def obtainRoleArgs(key, tour_now):
    tour_id = tour_now["id"]
    if key == 0:
        return {
            "name": f"参加希望者#{tour_id}",
            "color": discord.Colour.blue(),
            "hoist": True}
    elif isinstance(key, int):
        process_now = tour_now["process"]
        mem_number = len(tour_now["members"][process_now]["all"])
        number = tour_now["number"]
        orderIn = judgeOrder(process_now, mem_number, number)
        order = "優勝" if orderIn == "表彰式" else orderIn
        color_dicts = {
            "優勝": discord.Colour.gold(),
            "決勝戦": discord.Color.red(),
            "準決勝戦": discord.Color.orange()}
        color_role = color_dicts.get(order, discord.Color.green())
        name_role = f"TOP{mem_number} - {order}#{tour_id}" if order != "優勝" else f"TOP - 優勝#{tour_id}"
        return {
            "name": name_role,
            "color": color_role,
            "hoist": True
        }


async def add_role(ctx, member, role_id):
    role_sf = discord.Object(role_id)
    await member.add_roles(role_sf)

# ### msg


async def send2chan(ctx: commands.Context, msg_content: str, channel_id):
    channel_tmp = ctx.guild.get_channel(channel_id)
    return await channel_tmp.send(msg_content)


async def editMsg(ctx: commands.Context, msg_content: str, message_id, channel_id):
    channel_tmp = ctx.guild.get_channel(channel_id)
    if channel_tmp is None:
        print(f"channel: {channel_id} is not found")
        return
    message_tmp = await channel_tmp.fetch_message(message_id)
    await message_tmp.edit(content=msg_content)
    # return

# ### judge


def judgeOrder(process_now, num_members, number):
    if num_members > number ** 2:
        return f"{process_now}回戦"
    elif num_members > number:
        return "準決勝戦"
    elif num_members <= 1:
        return "表彰式"
    else:
        return "決勝戦"


def judgeGroup(num_members, numberIn, forceAll=False):
    number = int(numberIn)
    num_ind = int(math.log(num_members-1, number)) if num_members > 1 else 0
    if num_ind == 0:
        return [num_members]
    elif forceAll is True:
        standard_num = num_members // number ** num_ind
        res = num_members - standard_num * number ** num_ind
        return [standard_num + 1 if num < res else standard_num for num in range(number**(num_ind))]
    elif num_members < max(2, number - 1) * number ** num_ind:
        return [number for num in range(number**(num_ind-1))]
    else:
        res = num_members - (number - 1) * number ** num_ind
        return [number if num < res else number - 1 for num in range(number**(num_ind))]


async def addNewMembers(ctx, users):
    new_members_ids_tmp = (set(f"{mem.id}\t{mem.name}" for mem in users)
                           - set(f"{k}\t{v.name}" for k, v in ctx.members.items()))
    new_members_ids = set(int(s.split("\t")[0]) for s in new_members_ids_tmp)
    ctx.members.update({
        mem_id: await ctx.guild.fetch_member(mem_id) for mem_id in new_members_ids
    })

# 時間がかかりがちな処理。使いどころは絞るべき


async def checkRoleMembers(ctx, tour_now, role):
    last_check = tour_now["last_check"]
    process_now = tour_now["process"]
    logs_role = await ctx.guild.audit_logs(
        action=discord.AuditLogAction.member_role_update,
        after=last_check,
        oldest_first=False,
        limit=None).flatten()
    tour_now["last_check"] = datetime.datetime.now() + \
        datetime.timedelta(hours=-9)
    changed_users = {
        "add": [log.target for log in logs_role
                if role in set(log.after.roles)-set(log.before.roles)
                and log.user.id != ctx.me.id
                and log.created_at > last_check],
        "remove": [log.target for log in logs_role
                   if role in set(log.before.roles)-set(log.after.roles)
                   and log.user.id != ctx.me.id
                   and log.created_at > last_check]
    }
    await addNewMembers(ctx, changed_users["add"]+changed_users["remove"])
    changed_members = {
        k: [ctx.members[user.id] for user in v] for k, v in changed_users.items()
    }
    #print({k:[mem.name for mem in v] for k,v in changed_members.items()})
    tour_now["members"][process_now]["all"] = list(
        set(tour_now["members"][process_now]["all"])
        | set(changed_members["add"]))
    tour_now["members"][process_now]["kick"] = list(
        set(tour_now["members"][process_now]["kick"])
        - set(changed_members["add"])
        | set(changed_members["remove"]))


def judgeGroupMark(grp_num, winners_grps):
    win_num = len(winners_grps.get(grp_num, []))
    if win_num == 0:
        return "未"
    elif win_num == 1:
        return "済"
    else:
        return "複"

# ## show Group


async def showGroup(ctx, tour_now, process_now, forEdit=False, category_tour=None):
    if process_now == 0:
        return
    group_now = tour_now["members"][process_now]["group"]
    group_members = sum(group_now, [])
    add_members = list(
        set(tour_now["members"][process_now]["all"]) - set(group_members))
    order = judgeOrder(process_now, len(
        tour_now["members"][process_now]["all"]), tour_now["number"])
    winners_now = tour_now["members"][process_now]["winners"]
    winners_grps = winners_now.get("grps", {})
    winners_all = sum(winners_grps.values(), [])
    head_content = "\n" + \
        "□■━━━━━━━━━━━━■□\n" +\
        f"\t\t\t\t**{order} グループ分け**\n\t\t\t\t\t\t全{len(group_now)}グループ\n" +\
        "□■━━━━━━━━━━━━■□"
    # width: O = \s*3, \t = \s*4
    group_content = "\n".join([""]+[
        f"**`グループ{num+1}`\t{judgeGroupMark(num, winners_grps)}**\n" +
        "\n".join(
            [(" O\t" if mem in winners_all else "\t\t")+f"{mem.name}#{mem.discriminator}" for mem in gr])
        for num, gr in enumerate(group_now)
    ])

    winners_adds = winners_now.get("add", [])
    grps_withWin = winners_now.get("grps_withWin", [[] for num in range(4)])
    add_content_dict = {
        "add": "\n`追加`\n" +
        "\n".join([(" O\t" if mem in winners_adds else "\t\t") +
                   f"{mem.name}#{mem.discriminator}" for mem in add_members]),
        "未報告": "\n`未報告グループ`\n" + "\t\t"+", ".join(grps_withWin[0]),
        "複数人報告": "\n`複数人報告グループ`\n" + "\t\t"+", ".join(grps_withWin[2]+grps_withWin[3])
    }
    add_conditions = {
        "add": len(add_members) > 0,
        "未報告": len(grps_withWin[0]) > 0,
        "複数人報告": len(grps_withWin[2]+grps_withWin[3]) > 0
    }
    add_content = "\n".join(
        [add_content_dict[k]
            for k, v in add_conditions.items() if v is True]
    )
    stamp_content = "" if ctx.gatherHere is True else "□■━━━━━━━━━━━━■□\n" +\
        "\t\t\t\t\t**決勝戦勝利報告**\n" +\
        "\t\t\t━━━━━━━━━━\n" +\
        f"{order}の勝者は、\n**このメッセージに\nリアクションを追加してください。**" +\
        "□■━━━━━━━━━━━━■□\n"

    content = head_content+"\n"+group_content + \
        "\n"+add_content+"\n"+stamp_content+"\n"
    if forEdit is True and tour_now.get("group_msgInfo") is not None:
        await editMsg(ctx, content, tour_now["group_msgInfo"], tour_now["channel_ids"]["announce"])
    else:
        group_msg = await send2chan(ctx, content, tour_now["channel_ids"]["announce"])
        tour_now["group_msgInfo"] = group_msg.id
        if ctx.gatherHere is False:
            tour_now["valid_ids"]["message"] = group_msg.id
            # await group_msg.pin()
            tour_now["pin_msg"].append(group_msg)

    if category_tour is not None:
        old_groups = [chan for chan in ctx.guild.channels
                      if chan.category is not None
                      and chan.category == category_tour
                      and re.findall(r"グループ\d+", chan.name) != []]
        channel_names = [f"グループ{grp_num+1}" for grp_num in range(
            len(old_groups), len(tour_now["members"][process_now]["group"]))]
        channels = [await ctx.guild.create_text_channel(channel_name, category=category_tour) for channel_name in channel_names]
        tour_now["channel_ids"].update(
            {chan.name: chan.id for chan in channels})

# # reloadPresent


async def reloadPresent(ctx: commands.Context, tour_now: dict, check_role=False, atFirst=False):

    async def obtainUsersWithReactions(ctx: commands.Context, message_id: int, channel_id: int):
        chan_tmp = ctx.guild.get_channel(channel_id)
        msg_tmp = await chan_tmp.fetch_message(message_id)
        reactions_tmp = msg_tmp.reactions
        users_s = [await react.users().flatten() for react in reactions_tmp]
        return list(set(sum(users_s, [])))

    async def obtainPresentContent(ctx: commands.Context, process_now: int, tour_now: dict, react_membersIn: list):
        await addNewMembers(ctx, react_membersIn)
        react_members = [ctx.members[mem.id] for mem in set(react_membersIn)]
        # ## process 0
        if process_now == 0:
            tour_now["members"][0] = {"all": react_members}
            members = tour_now["members"][0]["all"]
            maxNum = tour_now["maxNumber"]
            join_content = "" if ctx.gatherHere is True else "\n\n□■━━━━━━━━━━━━■□\n" +\
                f"トーナメント{tour_id}の参加希望者は\n" +\
                "**このメッセージに\nリアクションを追加してください。**\n" +\
                "□■━━━━━━━━━━━━■□\n"

            if len(members) == 0:
                content = \
                    "□■━━━━━━━━━━━━■□\n" +\
                    f"\t\t\t\t**参加希望者一覧**\n" +\
                    "□■━━━━━━━━━━━━■□"
                return content+join_content
            cand_content =\
                "□■━━━━━━━━━━━━■□\n" +\
                f"\t\t\t\t**参加希望者一覧**\n" +\
                "□■━━━━━━━━━━━━■□\n"+"\n" +\
                f"参加希望者は以下の**{len(members)}名です**(最大{maxNum}名)。\n" +\
                "\n\t\t" +\
                "\n\t\t".join(
                    [f"{mem.name}#{mem.discriminator}" for mem in members]) + "\n"

            group_nums = judgeGroup(len(members), tour_now["number"])
            add_content_dict = {
                "overMax": "希望者が最大人数を超過しているので、**抽選が行われます**。",
                "selection": f"調整のため、**抽選で参加人数を{sum(group_nums)}人に絞ります**。"
            }
            add_content_conditions = {
                "overMax": len(members) > tour_now["maxNumber"],
                "selection": len(members) <= tour_now["maxNumber"] and len(members) != sum(group_nums)
            }
            add_content = "\n".join(
                [add_content_dict[k] for k, v in add_content_conditions.items() if v is True])
            tour_now["members"][1] = {"all": random.sample(
                members, min(tour_now["maxNumber"], sum(group_nums)))}
            return cand_content+"\n"+add_content+"\n"+join_content
        # ## process > 0
        elif process_now > 0:
            if check_role is True:
                await checkRoleMembers(ctx, tour_now, tour_now["roles"][process_now])
            members_all = tour_now["members"][process_now]["all"]
            members_kick = tour_now["members"][process_now]["kick"]
            valid_react_members = list(
                set(tour_now["members"][process_now]["all"])
                & (set(react_members)
                   | set(tour_now["members"][process_now].get("win_add", [])))
                - set(members_kick))
            group_now = tour_now["members"][process_now]["group"]
            winners_grps = {
                num: list(set(group_now[num])
                          & set(valid_react_members))
                for num in range(len(group_now))}
            winners_adds = list(
                set(valid_react_members)
                - set(sum(group_now, [])))
            grps_withWin = {k: [] for k in range(4)}
            for k, v in winners_grps.items():
                grps_withWin[len(v)].append(str(k+1))

            winners_now = {
                "grps": winners_grps,
                "add": winners_adds,
                "valid": sum([winners_grps[int(num)-1]
                              for num in grps_withWin[1]], [])+winners_adds,
                "valid_grps": {
                    int(num)-1: winners_grps[int(num)-1]
                    for num in grps_withWin[1]},
                "grps_withWin": grps_withWin
            }
            tour_now["members"][process_now]["winners"] = winners_now
            return "\t"

    async def obtainReactMembers(ctx, tour_now):
        if "channel" not in tour_now.get("valid_ids", {}).keys():
            return []
        chan_id = tour_now["valid_ids"]["channel"]
        msg_id = tour_now["valid_ids"]["message"]
        return await obtainUsersWithReactions(ctx, msg_id, chan_id)

    tour_id = tour_now["id"]
    process_now = tour_now["process"]

    react_members = await obtainReactMembers(ctx, tour_now)
    presentContent = await obtainPresentContent(ctx, process_now, tour_now, react_members)
    if process_now > 0:
        pass
    elif atFirst is False:
        await editMsg(ctx, presentContent,
                      tour_now["message_ids"]["announce"],
                      tour_now["channel_ids"]["announce"])
    else:
        msg_tmp = await send2chan(ctx, presentContent, tour_now["channel_ids"]["announce"])
        tour_now["message_ids"]["announce"] = msg_tmp.id
        if ctx.gatherHere is False:
            tour_now["valid_ids"]["message"] = msg_tmp.id
            # await msg_tmp.pin()
    await showGroup(ctx, tour_now, process_now, forEdit=True, category_tour=None)
    return tour_now


# # class
class Basic(commands.Cog):
    "基本的なコマンド"

    def __init__(self, bot):
        self.bot = bot

    # # only admin
    @commands.command(description="", pass_context=True)
    async def onlyAdmin(self, ctx: commands.Context, isLimited=True):
        "bot操作を管理者に限定するかどうか切り替えます。"
        ctx.onlyAdmin = not ctx.onlyAdmin
        sendContent = "管理者のみがbotを操作できます。" if ctx.onlyAdmin is True else "すべてのユーザーがbotを操作できます。"
        await ctx.channel.send(sendContent)

    @commands.command(description="", pass_context=True)
    async def l(self, ctx: commands.Context):
        self.bot.reload_extension("Tournament")
        print("loaded")

    @commands.command(description="`num`: 1試合の人数, `maxNum`: 最大参加人数", pass_context=True)
    async def open(self, ctx: commands.Context, num=3, maxNum=81):
        "トーナメントを開催します。"
        # # open
        tour_ids_old = [tour["id"] for tour in ctx.tours.values(
        ) if ctx.author.id in tour["host_ids"] and not "victor" in tour.keys()]
        if len(tour_ids_old) > 0:
            stop_content = f"{ctx.author.name}さんはすでにトーナメントを開催しています。\n" +\
                f"**先にそれらを終了しますか？** (`!yes`/`!no`)\n\t\t" + \
                "\n\t\t".join(tour_ids_old)
            await ctx.channel.send(stop_content)

            def check_msg(msg):
                return msg.author.id == ctx.author.id and (msg.content in ["!yes", "!no"])

            msg_input = await ctx.bot.wait_for("message", check=check_msg, timeout=None)
            input_content = msg_input.content
            if input_content == "!yes":
                for tour_id in tour_ids_old:
                    try:
                        await cancelTour(ctx, tour_id)
                    except Exception as e:
                        print(e)
                content = "以下のトーナメントを終了しました。\n\t\t"+"\n\t\t".join(tour_ids_old)+"\n" +\
                    "操作を続行します。\n\n"
                await ctx.channel.send(content)
            else:
                content = f"トーナメント{tour_id}を**キャンセルしました。**"
                await ctx.channel.send(content)
                return

        number = num if isinstance(num, int) and num >= 2 else 2
        maxNumber = maxNum if isinstance(
            num, int) and maxNum >= 2 else 81
        time_now = time.time()
        tour_id_tmp = hex(int(time_now) % 10**6)[2:]
        tour_id = format(tour_id_tmp[:5], "0>5").upper()

        tour_now = {"number": number,
                    "id": tour_id,
                    "maxNumber": maxNumber,
                    "members": {},
                    "all_members": {},
                    "last_check": datetime.datetime.now()+datetime.timedelta(hours=-9),
                    "process": 0,
                    "forAll": False,
                    "roles": {},
                    "valid_ids": {},
                    "pin_msg": [],
                    "lead_ids": {},
                    "host_ids": [ctx.author.id],
                    "channel_ids": {},
                    "category_ids": {},
                    "message_ids": {}}
        ctx.tours[tour_id] = tour_now

        commands_dict = {
            "next": {
                "re": r"^!next$",
                "expl": "`!next`\n\t\t募集を締め切ります。"},
            "adj": {
                "re": r"^!adj\s+\d+\s+\d+",
                "expl": "`!adj <num> <maxNum>`\n\t\t1試合の対戦人数を`num`人、最大参加人数を`maxNum`人に変更します。"},
            "all": {
                "re": r"^!all$",
                "expl": "`!all`\n\t\t最大参加人数以下の場合に、トーナメント用の人数調整を行うかどうか切り替えます。"},
            "cancel": {
                "re": r"^!cancel$",
                "expl": "`!cancel`\n\t\tトーナメントを終了します。"},
        }

        # ## make
        # ### category
        category_name = f"Tour_{tour_id}"
        category_tour = await ctx.guild.create_category(category_name)
        tour_now["category_ids"] = {category_tour.name: category_tour.id}
        # ### chan
        channel_names = ["announce", "commands"]  # , "otherCommands"
        channels = [await ctx.guild.create_text_channel(channel_name, category=category_tour)
                    for channel_name in channel_names] +\
            [await ctx.guild.create_voice_channel("voice", category=category_tour)]
        tour_now["channel_ids"] = {chan.name: chan.id for chan in channels}

        # ## process 0
        await reloadPresent(ctx, tour_now, check_role=False, atFirst=True)

        lead_content_dict = {
            True: "□■━━━━━━━━━━━━■□\n" +
            "\t\t**トーナメント参加者募集中**\n" +
            "\t\t\t━━━━━━━━━━\n" +
            f"トーナメント{tour_id}の参加希望者は\n" +
            "**このメッセージに\nリアクションを追加してください。**\n" +
            "□■━━━━━━━━━━━━■□\n",
            False: "□■━━━━━━━━━━━━■□\n" +
            f"トーナメント{tour_id}の参加希望者は\n"
            "**<#{}>の該当メッセージに**\n".format(tour_now["channel_ids"]["announce"]) +
            "**リアクションを追加してください。**\n" +
            "□■━━━━━━━━━━━━■□\n"
        }
        content_dict = {
            "lead": lead_content_dict[ctx.gatherHere],
            "open": f"\t\t`1試合の人数`    {number}人\n" +
            f"\t\t`最大参加人数`  {maxNumber}人\n",
            "commands": "\n".join([commands_dict[k]["expl"] for k in ["next", "cancel"]])+"\n\n" +
            "その他のコマンドは<#{}>を確認してください。".format(
                    tour_now["channel_ids"]["commands"])
        }
        content = "\n".join(content_dict.values())
        msg_open = await ctx.channel.send(content)

        commands_content = "□■━━━━━━━━━━━━■□\n" +\
            f"\t\tCommands for **参加募集中**\n" +\
            "□■━━━━━━━━━━━━■□\n" +\
            "\n".join([s["expl"] for s in commands_dict.values()])
        msg_commands = await send2chan(ctx, commands_content, tour_now["channel_ids"]["commands"])
        tour_now["message_ids"]["commands"] = msg_commands.id
        if ctx.gatherHere is True:
            # await msg_open.pin()
            tour_now["pin_msg"].append(msg_open)

        # role
        # tour_now["roles"][0]=await ctx.guild.create_role(**obtainRoleArgs(0, tour_now))

        tour_now["lead_ids"] = {"channel": ctx.channel.id, "message": msg_open.id}
        valid_ids_dict = {
            True: {k: v for k, v in tour_now["lead_ids"].items()},
            False: {"channel": tour_now["channel_ids"]["announce"],
                    "message": tour_now["message_ids"]["announce"]}}
        tour_now["valid_ids"] = valid_ids_dict[ctx.gatherHere]

        # ## check msg
        def check_msg(msg):
            isValidAuthor = msg.author.id in tour_now["host_ids"]
            commands_re = re.compile(
                "("+"|".join([s["re"] for s in commands_dict.values()])+")")
            isValidContent = re.findall(commands_re, msg.content) != []
            return isValidAuthor and isValidContent

        # ## initial_roles
        for num_tmp in range(2):
            role_tmp = await ctx.guild.create_role(name=f"トーナメントBot{num_tmp}#{tour_id}", hoist=False)
            tour_now["roles"][f"bot-{num_tmp}"] = role_tmp
            await ctx.guild.me.add_roles(discord.Object(role_tmp.id))

        while True:
            msg_input = await ctx.bot.wait_for("message", check=check_msg, timeout=None)
            input_content = msg_input.content
            if re.findall(commands_dict["cancel"]["re"], input_content) != []:
                cancelContent = f"`cancel`\n\tトーナメント{tour_id}は終了しました。"
                await ctx.channel.send(cancelContent)
                await cancelTour(ctx, tour_id)
                return
            elif re.findall(commands_dict["all"]["re"], input_content) != []:
                tour_now["forAll"] = not tour_now["forAll"]
                content_dict = {
                    False: "最大参加人数以外のトーナメント調整は行われません。",
                    True: "最大参加人数以外にもトーナメント調整が行われます。"
                }
                content = "`all`\n\t"+content_dict[tour_now["forAll"]]
                await ctx.channel.send(content)
                await cancelTour(ctx, tour_id)
                continue
            elif re.findall(commands_dict["adj"]["re"], input_content) != []:
                numAdj = int(input_content.split()[1])
                maxNumAdj = int(input_content.split()[2])
                number = numAdj if numAdj >= 2 else number
                maxNumber = maxNumAdj if maxNumAdj >= 2 else maxNumber
                editContent = "`adj`\n\t以下の通りに変更されました。\n"+"\n"\
                    f"`1試合の人数`: {numAdj} 人\n" +\
                    f"`最大参加人数`: {maxNumAdj} 人\n"
                tour_now["number"] = number
                tour_now["maxNumber"] = maxNumber
                await ctx.channel.send(editContent)
                continue
            elif re.findall(commands_dict["next"]["re"], input_content) != []:
                tour_now = await reloadPresent(ctx, tour_now, check_role=False)
                if len(tour_now["members"][0]["all"]) > 1:
                    # msg_tmp = await ctx.channel.send(content)
                    break
                else:
                    warningContent = f"`next`\n\t**参加希望者が2名未満です**。\n" +\
                        "参加希望者は" +\
                        ("該当の" if ctx.gatherHere else "<#{}>の該当".format(tour_now["channel_ids"]["announce"])) +\
                        "メッセージに\n" +\
                        "リアクションを追加してください。\n"
                    await ctx.channel.send(warningContent)
                    continue

        # ## process >0
        while True:
            tour_now["process"] += 1
            process_now = tour_now["process"]
            print(f"Tournament {tour_id}: {process_now}")

            def obtainMembersAll(tour_now, process_now):
                winners_last = tour_now["members"][process_now]["all"]
                return random.sample(winners_last, len(winners_last))

            members_now = {"all": obtainMembersAll(tour_now, process_now)}
            tour_now["all_members"].update(
                {mem.id: mem for mem in members_now["all"]})

            # ## renew role

            async def renewRole(ctx, tour_now, process_now):
                old_role = tour_now["roles"].get(process_now)
                role_tmp = await ctx.guild.create_role(**obtainRoleArgs(process_now, tour_now))
                if old_role is None or old_role.name != role_tmp.name:
                    tour_now["roles"][process_now] = role_tmp
                    tour_now["last_check"] = datetime.datetime.now() + \
                        datetime.timedelta(hours=-9)
                else:
                    old_role = None
                role_sf_now = discord.Object(tour_now["roles"][process_now].id)
                role_sf_old = discord.Object(
                    old_role.id) if old_role is not None else None
                for member in members_now["all"]:
                    await member.add_roles(role_sf_now)
                for member in members_now["all"]:
                    if old_role is not None:
                        await member.remove_roles(role_sf_old)
                if process_now > 1:
                    #offset=ctx.guild.me.top_role.position - process_now - 1
                    # offset=0
                    positions={tour_now["roles"][pro_num]: pro_num for pro_num in range(1, process_now+1)}
                    try:
                        await ctx.guild.edit_role_positions(positions)
                    except Exception as e:
                        error_content = traceback.format_exc()+"\n\n" +\
                            "position arguments: \n\t" +\
                            "\n\t".join([f"{role.name}: {pos}" for role, pos in positions.items()])+"\n\n" +\
                            "guild role positions: \n\t" +\
                            "\n\t".join(
                                [f"{role.name}_{role.id}: {role.position}" for role in ctx.guild.roles])
                        print(error_content)
                    await tour_now["roles"][process_now - 1].edit(color=discord.Color.from_hsv(226/360, 47/100, 85/100))
            await renewRole(ctx, tour_now, process_now)  # await

            if len(members_now["all"]) == 1:
                tour_now["victor"] = members_now["all"][0]
                break  # finish

            members_now["group"] = divideIntoGroup(
                members_now["all"], number, maxNumber)
            members_now["kick"] = []
            members_now["winners"] = {}
            members_now["win_add"] = []
            tour_now["members"][process_now] = members_now
            await showGroup(ctx, tour_now, process_now, forEdit=False, category_tour=category_tour)

            async def mention2group(ctx, tour_now, process_now):
                group_now = tour_now["members"][process_now]["group"]
                order = judgeOrder(process_now, len(
                    tour_now["members"][process_now]["all"]), tour_now["number"])
                channelGrps_tmp = [{
                    "group_id": tour_now["channel_ids"][f"グループ{grp_num+1}"],
                    "group_mem":grp,
                } for grp_num, grp in enumerate(group_now)]
                for info in channelGrps_tmp:
                    content = f"{order}\n\t\t" + \
                        "\n\t\t".join(
                            [f"<@{mem.id}>" for mem in info["group_mem"]])
                    await send2chan(ctx, content, info["group_id"])

            await mention2group(ctx, tour_now, process_now)

            def obtainCommandsDict2(ctx, tour_now, process_now, addExpl=False):
                order = judgeOrder(process_now, len(
                    tour_now["members"][process_now]["all"]), tour_now["number"])
                order2 = judgeOrder(
                    process_now+1, len(tour_now["members"][process_now]["all"])//tour_now["number"], tour_now["number"])
                commands_dicts = [{
                    "next": {
                        "re": r"^!next$",
                        "expl": f"`!next`\n\t\t全グループから勝者が適切に選出されている場合に限り、{order2}に進みます。"},
                    "cancel": {
                        "re": r"^!cancel$",
                        "expl": "`!cancel`\n\t\tトーナメントを終了します。"}
                }, {
                    "nextForce": {
                        "re": r"^!nextForce$",
                        "expl": f"`!nextForce`\n\t\t適切に選出されている勝者のみで、{order2}に進みます。"},
                    "add": {
                        "re": r"^!add[\s+\S(?:(?!#\d{4}).)*?#\d{4}]+",
                        "expl": "`!add <name>#<4桁の数字>`\n\t\t指定されたユーザー達を本トーナメントに追加します。"},
                    "kick": {
                        "re": r"^!kick[\s+\S(?:(?!#\d{4}).)*?#\d{4}]+",
                        "expl": "`!kick <name>#<4桁の数字>`\n\t\t指定されたユーザー達を本トーナメントから除名します。"},
                    "win": {
                        "re": r"^!win[\s+\S(?:(?!#\d{4}).)*?#\d{4}]+",
                        "expl": f"`!win <name>#<4桁の数字>`\n\t\tスタンプが押せないユーザー達を{order}の勝者に加えます。"},
                    "role": {
                        "re": r"!role$",
                        "expl": "`!role`\n\t\t役職の変更をトーナメントに反映します。"
                    },
                    "regroup": {
                        "re": r"^!regroup$",
                        "expl": "`!regroup`\n\t\t再度グループ分けを行います。"}
                }]
                if addExpl is False:
                    return commands_dicts[0]
                else:
                    return {**commands_dicts[0], **commands_dicts[1]}

            # ## recieve msg

            async def recieveReport(ctx, tour_now, process_now, forEdit=False):
                order = judgeOrder(process_now, len(
                    tour_now["members"][process_now]["all"]), tour_now["number"])
                commands_dict2 = obtainCommandsDict2(
                    ctx, tour_now, process_now, addExpl=False)
                commands_dict2_comp = obtainCommandsDict2(
                    ctx, tour_now, process_now, addExpl=True)
                lead_content_dict = {
                    True: "□■━━━━━━━━━━━━■□\n" +
                    f"\t\t\t\t**{order}勝利報告待ち**\n" +
                    "\t\t\t━━━━━━━━━━\n" +
                    f"{order}の勝者は\n" +
                    "**このメッセージに\nリアクションを追加してください。**\n" +
                    "□■━━━━━━━━━━━━■□\n",
                    False: "□■━━━━━━━━━━━━■□\n" +
                    f"{order}の勝者は\n" +
                    "**<#{}>の該当メッセージに**\n".format(tour_now["channel_ids"]["announce"]) +
                    "**リアクションを追加してください。**\n" +
                    "□■━━━━━━━━━━━━■□\n"
                }
                content = lead_content_dict[ctx.gatherHere] +\
                    "\n".join([s["expl"] for s in commands_dict2.values()])+"\n\n" +\
                    "その他のコマンドは<#{}>を確認してください。".format(
                        tour_now["channel_ids"]["commands"])

                if forEdit is False:
                    msg_tmp=await send2chan(ctx, content, tour_now["lead_ids"]["channel"])
                    #msg_tmp = await ctx.channel.send(content)
                    #tour_now["lead_ids"]["channel"] = ctx.channel.id
                    tour_now["lead_ids"]["message"] = msg_tmp.id
                    if ctx.gatherHere is True:
                        tour_now["valid_ids"]["message"] = msg_tmp.id
                        # await msg_tmp.pin()
                else:
                    chan_tmp = ctx.guild.get_channel(
                        tour_now["lead_ids"]["channel"])
                    await editMsg(ctx, content, tour_now["lead_ids"]["message"],
                                  tour_now["lead_ids"]["channel"])

                commands_content = "□■━━━━━━━━━━━━■□\n" +\
                    f"\tCommands for **{order}勝利報告待ち**\n" +\
                    "□■━━━━━━━━━━━━■□\n\n" +\
                    "\n".join([s["expl"]
                               for s in commands_dict2_comp.values()])
                await editMsg(ctx, commands_content, tour_now["message_ids"]["commands"], tour_now["channel_ids"]["commands"])

                await reloadPresent(ctx, tour_now, check_role=False, atFirst=True)

            # tour_now["members"][tour_now]["all"]=[]
            await recieveReport(ctx, tour_now, process_now)

            # # check msg2
            commands_dict2=obtainCommandsDict2(
                ctx, tour_now, process_now, True)

            def check_msg2(msg):
                isValidAuthor = msg.author.id in tour_now["host_ids"]
                commands_re = re.compile(
                    "("+"|".join([s["re"] for s in commands_dict2.values()])+")")
                isValidContent = re.findall(commands_re, msg.content) != []
                return isValidAuthor and isValidContent
            while True:
                msg_input2 = await ctx.bot.wait_for("message", check=check_msg2, timeout=None)
                input_content = msg_input2.content
                commands_re = re.compile(
                    "("+"|".join([commands_dict2[key]["re"] for key in ["win", "add", "kick"]])+")")

                if re.findall(commands_re, input_content):
                    input_content2 = "".join(input_content.splitlines())
                    command = re.sub(r"^!", "", input_content2.split()[0])
                    args_input = re.sub(
                        r"^!(kick|add|win)\s+", "", input_content2)
                    args_tmp = re.findall(
                        r"\S(?:(?!#\d{4}).)*?#\d{4}", args_input)
                    args_name = [{"name": s[:-5], "discri":s[-4:]}
                                 for s in args_tmp]

                    async def obtainMemCands(ctx, command: str, tour_now, process_now, args_name):
                        if command in ["kick", "win"]:
                            return [mem for mem in tour_now["members"][process_now]["all"]
                                    if {"name": mem.name, "discri": mem.discriminator} in args_name]
                        elif command == "add":
                            mem_cands_tmp = [user for arg in args_name
                                             for user in await ctx.guild.query_members(arg["name"])
                                             if user.discriminator == arg["discri"]]
                            await addNewMembers(ctx, mem_cands_tmp)
                            return [ctx.members[user.id] for user in mem_cands_tmp]
                        else:
                            return []

                    mem_cands = await obtainMemCands(ctx, command, tour_now, process_now, args_name)
                    if mem_cands == []:
                        err_content = f"`{command}`\n\t該当するユーザーが見つかりません。"
                        await send2chan(ctx, err_content, tour_now["lead_ids"]["channel"])
                    elif command == "kick":
                        tour_now["members"][process_now]["kick"] = list(
                            set(tour_now["members"][process_now].get("kick", [])) | set(mem_cands))
                        await reloadPresent(ctx, tour_now, check_role=False, atFirst=False)
                        kick_content = f"`{command}`\n\t次の{len(mem_cands)}名をトーナメント{tour_id}から除名しました。\n" +\
                            "\t\t"+"\n\t\t".join(
                                [f"{mem.name}#{mem.discriminator}" for mem in mem_cands])
                        await send2chan(ctx, kick_content, tour_now["lead_ids"]["channel"])
                        for member in mem_cands:
                            role_sf = discord.Object(
                                tour_now["roles"][process_now].id)
                            await member.remove_roles(role_sf)
                    elif command == "add":  # add
                        tour_now["members"][process_now]["all"] = list(
                            set(tour_now["members"][process_now].get("all", [])) | set(mem_cands))
                        await reloadPresent(ctx, tour_now, check_role=False, atFirst=False)
                        add_content = f"`{command}`\n\t次の{len(mem_cands)}名をトーナメント{tour_id}に追加しました。\n" +\
                            "\t\t"+"\n\t\t".join(
                                [f"{mem.name}#{mem.discriminator}" for mem in mem_cands])
                        await send2chan(ctx, add_content, tour_now["lead_ids"]["channel"])
                        for member in mem_cands:
                            role_sf = discord.Object(
                                tour_now["roles"][process_now].id)
                            await member.add_roles(role_sf)
                    elif command == "win":
                        order = judgeOrder(process_now, len(
                            tour_now["members"][process_now]["all"]), tour_now["number"])
                        tour_now["members"][process_now]["win_add"] = list(
                            set(tour_now["members"][process_now].get("win_add", [])) | set(mem_cands))
                        await reloadPresent(ctx, tour_now, check_role=False, atFirst=False)
                        add_content = f"`{command}`\n\t次の{len(mem_cands)}名を{order}の勝者に追加しました。\n" +\
                            "\t\t"+"\n\t\t".join(
                                [f"{mem.name}#{mem.discriminator}" for mem in mem_cands])
                        await send2chan(ctx, add_content, tour_now["lead_ids"]["channel"])
                    continue
                # ### cancel
                elif re.findall(commands_dict2["cancel"]["re"], input_content) != []:
                    cancel_content = f"`cancel`\n\tトーナメント{tour_id}は終了しました。"
                    await send2chan(ctx, cancel_content, tour_now["lead_ids"]["channel"])
                    await cancelTour(ctx, tour_id)
                    return
                elif re.findall(commands_dict2["regroup"]["re"], input_content) != []:
                    tour_now["members"][process_now]["winners"] = {}
                    tour_now["members"][process_now]["win_add"] = []
                    content="`regroup`\n\t再グループ分けを行います。\n\t少し時間がかかります。"
                    await send2chan(ctx, content, tour_now["lead_ids"]["channel"])
                    await checkRoleMembers(ctx, tour_now, tour_now["roles"][process_now])
                    members_all = list(
                        set(tour_now["members"][process_now]["all"])
                        - set(tour_now["members"][process_now]["kick"]))
                    tour_now["members"][process_now]["group"] = divideIntoGroup(
                        members_all, number, maxNumber, forceAll=True)
                    await showGroup(ctx, tour_now, process_now, forEdit=True, category_tour=category_tour)
                    await mention2group(ctx, tour_now, process_now)

                    # clear reaction
                    chan_tmp = ctx.guild.get_channel(
                        tour_now["valid_ids"]["channel"])
                    msg_tmp = await chan_tmp.fetch_message(tour_now["valid_ids"]["message"])
                    await msg_tmp.clear_reactions()

                    await recieveReport(ctx, tour_now, process_now, forEdit=True)
                    content = "<#{}>を確認してください。\n".format(tour_now["channel_ids"]["announce"]) +\
                        "役職の更新は遅れる場合があります。"
                    await send2chan(ctx, content, tour_now["lead_ids"]["channel"])
                    # with warnings.catch_warnings():
                    #warnings.simplefilter("ignore", RuntimeWarning)
                    await renewRole(ctx, tour_now, process_now)  # await
                    continue
                elif re.findall(commands_dict2["role"]["re"], input_content) != []:
                    await reloadPresent(ctx, tour_now, check_role=True, atFirst=False)
                    content = "`role`\n\t役職の変更を反映しました。"
                    await send2chan(ctx, content, tour_now["lead_ids"]["channel"])
                    continue
                # ### next
                elif re.findall(commands_dict2["next"]["re"], input_content) != []:
                    tour_now = await reloadPresent(ctx, tour_now, check_role=False, atFirst=False)
                    winners_now = tour_now["members"][process_now]["winners"]
                    valid_winners = winners_now.get("valid", [])
                    grps_withWin = winners_now.get(
                        "grps_withWin", [[] for num in range(4)])
                    invalid_grps = sum([grps_withWin[num]
                                        for num in [0, 2, 3]], [])
                    if len(valid_winners) == 0:
                        content = f"`next`\n\t適切な勝者が1名も存在していません。"
                        await send2chan(ctx, content, tour_now["lead_ids"]["channel"])
                        continue
                    elif len(invalid_grps) > 0:
                        content = f"`next`\n\t次のグループの勝者報告が**不適切**です。\n" +\
                            "\t\t"+", ".join(invalid_grps)
                        await send2chan(ctx, content, tour_now["lead_ids"]["channel"])
                        continue
                    else:
                        tour_now["members"][process_now +
                                            1] = {"all": tour_now["members"][process_now]["winners"].get("valid", [])}
                        break
                elif re.findall(commands_dict2["nextForce"]["re"], input_content) != []:
                    tour_now = await reloadPresent(ctx, tour_now, check_role=False, atFirst=False)
                    winners_now = tour_now["members"][process_now]["winners"]
                    if len(winners_now.get("valid", [])) == 0:
                        content = f"`nextForce`\n\t適切な勝者が1名も存在していません。"
                        await send2chan(ctx, content, tour_now["lead_ids"]["channel"])
                        continue
                    else:
                        tour_now["members"][process_now +
                                            1] = {"all": winners_now.get("valid", [])}
                        break
            # ## show winner

            async def showWinners(tour_now, process_now):
                winners_grps = tour_now["members"][process_now]["winners"].get(
                    "valid_grps", {})
                order = judgeOrder(process_now, len(
                    tour_now["members"][process_now]["all"]), tour_now["number"])
                win_content = "\n"+"□■━━━━━━━━━━━━■□\n" +\
                    f"\t\t\t\t\t**{order} 勝者一覧**\n" +\
                    "□■━━━━━━━━━━━━■□\n\n" +\
                    "\n".join([f"**`グループ{k+1}`**\n\t\t"+"\n\t\t".join([
                        f"{s.name}#{s.discriminator}" for s in v])
                        for k, v in winners_grps.items()]) + "\n"
                await send2chan(ctx, win_content, tour_now["channel_ids"]["announce"])

            await showWinners(tour_now, process_now)

        victor = tour_now["victor"]

        vict_content = f"\tトーナメント{tour_id}が終了しました。\n" +\
            f"**優勝は{victor.name}#{victor.discriminator}さんです**。\n\n" +\
            f"`?delete {tour_id}`\n\t\tこのトーナメントに関するチャンネル・役職を削除します。\n" +\
            "`?deleteRes`\n\t\t終了しているトーナメントに関するチャンネル・役職をすべて削除します。"
        await send2chan(ctx, vict_content, tour_now["lead_ids"]["channel"])


# # Delete

async def deleteResFunc(ctx: commands.Context):
    send_content = "終了しているトーナメントに関するチャンネル・役職を削除します。"
    await ctx.channel.send(send_content)
    old_tours = {tour["id"]: tour for tour in ctx.tours.values()
                 if "victor" in tour.keys()}
    ctx.tours = {tour["id"]: tour for tour in ctx.tours.values()
                 if "victor" not in tour.keys()}

    channels = [chan for chan in ctx.guild.channels
                if chan.category is not None
                and chan.category.name.startswith("Tour_")
                and chan.category.name not in [f"Tour_{tour_id}"
                                               for tour_id in ctx.tours.keys()]]
    for chan in channels:
        await chan.delete()
    cats = [cat for cat in ctx.guild.categories
            if cat.name.startswith("Tour_")
            and cat.name not in [f"Tour_{tour_id}" for tour_id in ctx.tours.keys()]]
    for cat in cats:
        await cat.delete()
    for role in [s for s in ctx.guild.roles
                 if re.findall(r"#\w{5}$", s.name) != []
                 and all([not s.name.endswith(f"#{tour_id}") for tour_id in ctx.tours.keys()])]:
        await role.delete()


class Delete(commands.Cog):
    "トーナメントや関連するチャンネル・役職の削除"

    def __init__(self, bot):
        self.bot = bot

    @commands.command(description="", pass_context=True)
    async def delete(self, ctx: commands.Context, tour_id: str):
        "指定されたトーナメントを削除します。"
        clearContent = f"Tournament {tour_id}に関するチャンネル・役職を削除します。"
        await ctx.channel.send(clearContent)
        await cancelTour(ctx, tour_id)

    @commands.command(description="", pass_context=True)
    async def deleteRes(self, ctx: commands.Context):
        "終了しているトーナメントを削除します。"
        await deleteResFunc(ctx)

    @commands.command(description="", pass_context=True)
    async def deleteAll(self, ctx: commands.Context):
        sendContent = "開催中のトーナメントも含めて、紐づいているすべてのチャンネル・役職を削除します。"
        await ctx.channel.send(sendContent)

        channels = [
            chan for chan in ctx.guild.channels if chan.category is not None and chan.category.name.startswith("Tour_")]
        for chan in channels:
            await chan.delete()
        cats = [
            cat for cat in ctx.guild.categories if cat.name.startswith("Tour_")]
        for cat in cats:
            await cat.delete()
        for role in [s for s in ctx.guild.roles if re.findall(r"#\w{5}$", s.name) != []]:
            await role.delete()
        ctx.tours = {}

    @commands.command(description="", pass_context=True)
    async def tmp8(self, ctx: commands.Context):
        content = "□■━━━━━━━━━━━━■□\n" +\
            "\t\t\t\t\t**決勝戦勝利報告**\n" +\
            "\t\t\t━━━━━━━━━━\n" +\
            "決勝戦勝者は\n**このメッセージに\nリアクションを追加してください。**\n" +\
            "□■━━━━━━━━━━━━■□\n"
        await ctx.send(content)
        print(ctx.guild.me.top_role.position)


def setup(bot):
    bot.add_cog(Basic(bot))
    bot.add_cog(Delete(bot))
    # bot.add_cog(Tmp(bot))
