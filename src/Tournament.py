import discord
from discord.ext import commands
import subprocess
import time
import random
import re
import math
import datetime

#import basic

## fucntions

def divideIntoGroup(membersIn, number, maxNumber):
    members = random.sample(membersIn, len(membersIn))
    group_nums = judgeGroup(len(members), number)
    #groupNum = (len(members)-1)//number+1
    return [members[sum(group_nums[0:grp_ind]):sum(group_nums[0:grp_ind+1])] for grp_ind in range(len(group_nums))]


async def cancelTour(ctx: commands.Context, tour_id):
    tour_now = ctx.tours.pop(tour_id)
    valid_channels = [
        chan for chan in ctx.guild.channels if chan.id in tour_now["channel_ids"].values()]
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
            "name": f"参加候補者#{tour_id}",
            "color": discord.Colour.blue(),
            "hoist": True}
    elif isinstance(key, int):
        process_now = tour_now["process"]
        mem_number = len(tour_now["members"][process_now]["all"])
        number = tour_now["number"]
        orderIn = judgeOrder(process_now, mem_number, number)
        order = "優勝" if orderIn == "表彰式" else orderIn
        color_dicts = {
            "決勝": discord.Color.red(), "準決勝": discord.Color.orange()}
        color = color_dicts[order] if order in color_dicts.keys(
        ) else discord.Color.green()
        return {
            "name": f"TOP{mem_number} - {order}#{tour_id}",
            "color": discord.Color.green(),
            "hoist": True}
    elif key == "victor":
        #process_now = tour_now["process"]
        #all_mem_num = len(tour_now["all_members"].keys())
        return {
            "name": f"TOP - 優勝#{tour_id}",
            "color": discord.Colour.gold(),
            "hoist": True}


async def add_role(ctx, member, role_id):
    role_sf = discord.Object(role_id)
    await member.add_roles(role_sf)

async def send2chan(ctx: commands.Context, msg_content: str, channel_id):
    channel_tmp = ctx.guild.get_channel(channel_id)
    return await channel_tmp.send(msg_content)


async def editMsg(ctx: commands.Context, msg_content: str, message_id, channel_id):
    channel_tmp = ctx.guild.get_channel(channel_id)
    message_tmp = await channel_tmp.fetch_message(message_id)
    await message_tmp.edit(content=msg_content)
    # return


def judgeOrder(process_now, num_members, number):
    if num_members > number ** 2:
        return f"{process_now}回戦"
    elif num_members > number:
        return "準決勝戦"
    elif num_members <= 1:
        return "表彰式"
    else:
        return "決勝戦"


def judgeGroup(num_members, numberIn):
    number = int(numberIn)
    num_ind = int(math.log(num_members, number))
    if num_ind == 0:
        return [num_members]
    elif num_members < (number - 1) * number ** num_ind:
        return [number for num in range(number**(num_ind-1))]
    else:
        res = num_members - (number - 1) * number ** num_ind
        return [number if num < res else number - 1 for num in range(number**(num_ind))]

async def addNewMembers(ctx, users):
    new_members_ids_tmp = list(
        set([f"{mem.id}\t{mem.name}" for mem in users]) -
        set([f"{k}\t{v.name}" for k, v in ctx.members.items()]))
    new_members_ids = [int(s.split("\t")[0]) for s in new_members_ids_tmp]
    ctx.members.update({
        mem_id: await ctx.guild.fetch_member(mem_id) for mem_id in new_members_ids
        })

## reload

async def reloadPresent(ctx: commands.Context, tour_now):
    tour_id = tour_now["id"]
    chan_id = tour_now["valid_ids"]["channel"]
    msg_id = tour_now["valid_ids"]["message"]
    process_now = tour_now["process"]

    async def obtainUsersWithReactions(ctx: commands.Context, message_id: int, channel_id: int):
        chan_tmp = ctx.guild.get_channel(channel_id)
        msg_tmp = await chan_tmp.fetch_message(message_id)
        reactions_tmp = msg_tmp.reactions
        users_s = [await react.users().flatten() for react in reactions_tmp]
        return list(set(sum(users_s, [])))

    async def obtainPresentContent(ctx: commands.Context, process_now: int, tour_now: dict, react_membersIn: list):
        await addNewMembers(ctx, react_membersIn)
        react_members = [ctx.members[mem.id] for mem in react_membersIn]
        ### process 0
        if process_now == 0:
            tour_now["members"][0] = {"all": react_members}
            members = tour_now["members"][0]["all"]
            if len(members) == 0:
                content = f"process {process_now}: 参加候補者一覧"
                return content
            cand_content =\
                f"process {process_now}: 参加候補者一覧\n" +\
                f"参加候補者は以下の{len(members)}名です (最大{tour_now['maxNumber']}名)\n" +\
                "-"*6 + "\n" +\
                "\n".join(
                    [f"{mem.name}#{mem.discriminator}" for mem in members]) + "\n"

            group_nums = judgeGroup(len(members), tour_now["number"])
            add_content = "候補者が最大人数を超過しているので、抽選が行われます。"\
                if len(members) > tour_now["maxNumber"] else \
                ("" if len(members) == sum(group_nums)
                 else f"調整のため、抽選で参加人数を{sum(group_nums)}人に絞ります。")
            tour_now["members"][1] = {"all": random.sample(
                members, min(tour_now["maxNumber"], sum(group_nums)))}
            return cand_content+"\n"+add_content
        ### process > 0
        elif process_now > 0:
            async def checkRoleMembers(ctx, tour_now, role):
                last_check = tour_now["last_check"]
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
                tour_now["members"][process_now]["all"] = list(
                    set(tour_now["members"][process_now]["all"]) |
                    set(changed_members["add"]))
                tour_now["members"][process_now]["kick"] = list(
                    set(tour_now["members"][process_now]["kick"]) -
                    set(changed_members["add"]) |
                    set(changed_members["remove"]))
            # avoid intents
            # member.get_role will be usable after version 2.0 (the latest version in pip is 1.7.3)
            # async def obtainValidReactMembers(ctx, tour_now, process_now, react_members):
                #role_now = tour_now["roles"][process_now]
                #print({mem.name:mem.roles for mem in react_members}, role_now)
                #react_members_withRole=[mem for mem in react_members if role_now in mem.roles]
                #members_all = tour_now["members"][process_now]["all"]
            #    return react_members_withRole #list(set(members_all) & set(react_members))
            await checkRoleMembers(ctx, tour_now, tour_now["roles"][process_now])
            members_all = tour_now["members"][process_now]["all"]
            members_kick = tour_now["members"][process_now]["kick"]
            valid_react_members = list(
                set(tour_now["members"][process_now]["all"])
                & set(react_members)
                - set(members_kick))
            group_now = tour_now["members"][process_now]["group"]
            winners_grps = {
                num: list(
                    set(group_now[num])
                    & set(valid_react_members))
                for num in range(len(group_now))}
            winners_adds = list(
                set(valid_react_members)
                - set(sum(group_now, [])))
            invalid_grps = {k: [] for k in range(4)}
            for k, v in winners_grps.items():
                invalid_grps[len(v)].append(str(k+1))

            order = judgeOrder(process_now, len(
                members_all), tour_now["number"])
            win_content_dict = {
                "head": f"process {process_now}: {order} 勝者一覧\n"+"-"*6,
                "main": "\n".join([f"{k+1}: "+", ".join([f"{mem.name}#{mem.discriminator}" for mem in v]) for k, v in winners_grps.items()]),
                "add": "追加: " + ", ".join([f"{mem.name}#{mem.discriminator}" for mem in winners_adds])
            }
            win_conditions = {
                "head": True,
                "main": True,
                "add": len(winners_adds) > 0
            }
            win_content = "\n".join(
                [win_content_dict[k]
                for k, v in win_conditions.items() if v is True]
            )
            invalid_content_dict = {
                "未報告": "-"*6+"\n" + f"未報告グループ\n" + "- "+", ".join(invalid_grps[0]),
                "複数人報告": "-"*6+"\n"+f"複数人報告グループ\n" + "- "+", ".join(invalid_grps[2]+invalid_grps[3])
            }
            invalid_conditions = {
                "未報告": len(invalid_grps[0]) > 0,
                "複数人報告": len(invalid_grps[2]+invalid_grps[3]) > 0
            }
            invalid_content = "\n".join(
                [invalid_content_dict[k] 
                for k, v in invalid_conditions.items() if v is True]
            )

            tour_now["members"][process_now]["valid_winners"] = sum(
                [winners_grps[int(num)-1] for num in invalid_grps[1]], [])
            tour_now["members"][process_now]["valid_winners_grps"] = {
                int(num)-1: winners_grps[int(num)-1] for num in invalid_grps[1]}
            tour_now["members"][process_now]["invalid_winners"] = sum(
                [winners_grps[int(num)-1] for num in invalid_grps[2]+invalid_grps[3]], [])
            tour_now["members"][process_now]["invalid_grps"] = sum(
                [invalid_grps[num] for num in [0, 2, 3]], [])
            return win_content+"\n\n"+invalid_content

    react_members = await obtainUsersWithReactions(ctx, msg_id, chan_id)
    presentContent = await obtainPresentContent(ctx, process_now, tour_now, react_members)
    msg_present = await editMsg(ctx, presentContent, tour_now["message_ids"]["present"], tour_now["channel_ids"]["present"])
    return tour_now


## class
class Basic(commands.Cog):
    "基本的なコマンド"

    def __init__(self, bot):
        self.bot = bot

    ## only admin
    @commands.command(description="", pass_context=True)
    async def onlyAdmin(self, ctx: commands.Context, isLimited=True):
        "bot操作を管理者に限定するかどうか切り替えます。"
        ctx.onlyAdmin = not ctx.onlyAdmin
        sendContent = "管理者のみがbotを操作できます。" if ctx.onlyAdmin is True else "すべてのユーザーがbotを操作できます。"
        await ctx.channel.send(sendContent)

    @commands.command(description="`num`: 1試合の人数, `maxNum`: 最大参加人数", pass_context=True)
    async def open(self, ctx: commands.Context, num=3, maxNum=81):
        "トーナメントを開催します。"
        ## open
        if ctx.tours != {} and [1 for tour in ctx.tours.values() if ctx.author.id in tour["host_ids"] and not "victor" in tour.keys()] != []:
            tour_ids_old = [tour["id"] for tour in ctx.tours.values(
            ) if ctx.author.id in tour["host_ids"]]
            stop_content = f"{ctx.author.name}さんはすでにトーナメントを開催しています。\n" +\
                f"先にそれらを終了しますか？ (`!yes`/`!no`): "+", ".join(tour_ids_old)
            await ctx.channel.send(stop_content)

            def check_msg(msg):
                return msg.author.id == ctx.author.id and (msg.content in ["!yes", "!no"])

            msg_input = await ctx.bot.wait_for("message", check=check_msg, timeout=None)
            input_content = msg_input.content
            if input_content == "!yes":
                for tour_id in tour_ids_old:
                    await cancelTour(ctx, tour_id)
                content = "以下のトーナメントを終了しました。: "+", ".join(tour_ids_old)+"\n" +\
                    "操作を続行します。\n\n"
                await ctx.channel.send(content)
            else:
                content = "トーナメントをキャンセルしました。"
                await ctx.channel.send(content)
                return

        number = num if isinstance(num, int) and num >= 2 else 2
        maxNumber = maxNum if isinstance(
            num, int) and maxNum >= 2 else 81
        time_now = time.time()
        tour_id_tmp = hex(int(time_now) % 10**6)[2:]
        tour_id = format(tour_id_tmp[:5], "0>5").upper()
        open_message =\
            f"Tournament: {tour_id}\n" +\
            f"1試合人数: {number} 人\n" +\
            f"最大参加人数: {maxNumber} 人\n" +\
            "-"*6

        tour_now = {"number": number,
                    "id": tour_id,
                    "maxNumber": maxNumber,
                    "members": {},
                    "all_members": {},
                    "last_check": datetime.datetime.now()+datetime.timedelta(hours=-9),
                    "process": 0,
                    "roles": {},
                    "valid_ids": {},
                    "host_ids": [ctx.author.id],
                    "channel_ids": {},
                    "category_ids": {},
                    "message_ids": {}}
        ctx.tours[tour_id] = tour_now

        join_message = f"Tournament {tour_id}に参加したい人は、**このメッセージにスタンプ(リアクション)を押してください。**\n\n" +\
            f"`!next`: 募集を締め切ります。\n" +\
            f"`!adjust <num> <maxNum>`: 1試合の対戦人数を<num>人、最大参加人数を<maxNum>人に変更します。\n" +\
            f"`!cancel`: トーナメントを中止します。"

        msg_open = await ctx.channel.send(open_message+"\n"+join_message)

        ## make
        ### category
        category_name = f"Tour_{tour_id}"
        category_tour = await ctx.guild.create_category(category_name)
        tour_now["category_ids"] = {category_tour.name: category_tour.id}
        ### chan
        channel_names = ["present", "results"]
        channels = [await ctx.guild.create_text_channel(channel_name, category=category_tour) for channel_name in channel_names] +\
            [await ctx.guild.create_voice_channel("voice", category=category_tour)]
        tour_now["channel_ids"] = {chan.name: chan.id for chan in channels}

        ### process 0
        present_content = "process 0: 参加候補者一覧"
        msg_present = await send2chan(ctx, present_content, tour_now["channel_ids"]["present"])
        tour_now["message_ids"] = {
            "present": msg_present.id,
            "open": msg_open.id}

        # role
        # tour_now["roles"][0]=await ctx.guild.create_role(**obtainRoleArgs(0, tour_now))

        tour_now["valid_ids"] = {"channel": ctx.channel.id,
                                 "message": tour_now["message_ids"]["open"]}

        def check_msg(msg):
            isValidAuthor = msg.author.id in tour_now["host_ids"]
            isValidContent = msg.content in ["!next", "!cancel"] or re.findall(
                "^!adjust \d+ \d+", msg.content) != []
            return isValidAuthor and isValidContent

        while True:
            msg_input = await ctx.bot.wait_for("message", check=check_msg, timeout=None)
            input_content = msg_input.content
            if input_content == "!cancel":
                cancelContent = f"Tournament {tour_id}は中止されました。"
                await ctx.channel.send(cancelContent)
                await cancelTour(ctx, tour_now)
                return
            if input_content.startswith("!adjust"):
                numAdj = int(input_content.split()[1])
                maxNumAdj = int(input_content.split()[2])
                number = numAdj if numAdj >= 2 else number
                maxNumber = maxNumAdj if maxNumAdj >= 2 else maxNumber
                editContent = "以下の通りに変更されました。\n"+"-"*6+"\n"\
                    f"1試合人数: {numAdj} 人\n" +\
                    f"最大参加人数: {maxNumAdj} 人\n"
                tour_now["number"] = number
                tour_now["maxNumber"] = maxNumber
                await ctx.channel.send(editContent)
                continue

            elif input_content == "!next":
                tour_now = await reloadPresent(ctx, tour_now)
                if len(tour_now["members"][0]["all"]) > 1:
                    break
                else:
                    warningContent = f"参加人数が2名未満です。\n" +\
                        "参加希望者は該当メッセージにスタンプを押してください。"
                    await ctx.channel.send(warningContent)
                    continue

        # ## process >0
        while True:
            tour_now["process"] += 1
            process_now = tour_now["process"]
            print(process_now)

            def obtainMembersAll(tour_now, process_now):
                winners_last = tour_now["members"][process_now]["all"]
                return random.sample(winners_last, len(winners_last))

            members_now = {"all": obtainMembersAll(tour_now, process_now)}
            tour_now["all_members"].update(
                {mem.id: mem for mem in members_now["all"]})
            if len(members_now["all"]) == 1:
                tour_now["victor"] = members_now["all"][0]
                break  # finish

            tour_now["roles"][process_now] = await ctx.guild.create_role(**obtainRoleArgs(process_now, tour_now))
            for member in members_now["all"]:
                role_sf = discord.Object(tour_now["roles"][process_now].id)
                await member.add_roles(role_sf)
                if process_now > 1:
                    role_sf = discord.Object(
                        tour_now["roles"][process_now-1].id)
                    await member.remove_roles(role_sf)

            ### show Group
            async def showGroup(ctx, tour_now, process_now):
                group_now = tour_now["members"][process_now]["group"]
                order = judgeOrder(process_now, len(
                    tour_now["members"][process_now]["all"]), tour_now["number"])
                head_content = "="*6+"\n" + \
                    f"{order} グループ分け (全{len(group_now)}グループ)"
                group_content = ("-"*6+"\n").join([""]+[
                    f"- グループ{num+1}\n" +
                    "\n".join(
                        [f"{mem.name}#{mem.discriminator}" for mem in gr])
                    for num, gr in enumerate(group_now)
                ])
                content = head_content+"\n"+group_content
                await send2chan(ctx, content, tour_now["channel_ids"]["results"])

            members_now["group"] = divideIntoGroup(members_now["all"], number, maxNumber)
            members_now["kick"] = []
            tour_now["members"][process_now] = members_now
            await showGroup(ctx, tour_now, process_now)
            if process_now == 1:
                channel_names = [f"グループ{grp_num+1}" for grp_num in range(len(tour_now["members"][process_now]["group"]))]
                channels = [await ctx.guild.create_text_channel(channel_name, category=category_tour) for channel_name in channel_names]
                tour_now["channel_ids"].update({chan.name: chan.id for chan in channels})

            ### recieve msg
            async def recieveReport(ctx, tour_now, process):
                order = judgeOrder(process, len(
                    tour_now["members"][process]["all"]), tour_now["number"])
                order2 = judgeOrder(
                    process+1, len(tour_now["members"][process]["all"])//tour_now["number"], tour_now["number"])
                content = f"{order}の勝者は、**このメッセージにスタンプ(リアクション)を押してください。**\n\n" +\
                    f"`!next`: 全グループから勝者が適切に選出されている場合に限り、{order2}に進みます。\n" +\
                    f"`!nextForce`: 適切に選出されている勝者のみで、{order2}に進みます。\n" +\
                    "`!kick <name>#<4桁の数字>`: 指定されたユーザーを本トーナメントから除名します。\n" +\
                    f"`!add <name>#<4桁の数字>`: 指定されたユーザーを本トーナメントに追加します。\n" +\
                    "`!regroup`: 再度グループ分けを行います。\n" +\
                    "`!cancel`: トーナメントを中止します。\n\n" +\
                    f"参加者から`{order}#{tour_id}`の役職を取り除くことや、serverからkickすることも有効です。"
                chan_tmp = ctx.guild.get_channel(
                    tour_now["valid_ids"]["channel"])
                msg_tmp = await chan_tmp.send(content)
                tour_now["valid_ids"]["message"] = msg_tmp.id
                try:
                    await reloadPresent(ctx, tour_now)
                except Exception as e:
                    print(e)

            # tour_now["members"][tour_now]["all"]=[]
            await recieveReport(ctx, tour_now, process_now)

            def check_msg2(msg):
                isValidAuthor = msg.author.id in tour_now["host_ids"]
                isValidContent = msg.content in ["!next", "!nextForce", "!cancel", "!regroup"] or re.findall(
                    "^!(kick|add) .+#\d{4}", msg.content) != []
                return isValidAuthor and isValidContent
            while True:
                msg_input2 = await ctx.bot.wait_for("message", check=check_msg2, timeout=None)
                input_content = msg_input2.content
                if re.findall(r"^!(kick|add)", input_content):
                    isKick=input_content.startswith("!kick")
                    if len(input_content.split()) < 2:
                        err_content = f"引数にエラーがあります。"
                        await ctx.channel.send(err_content)
                        continue
                    args_combined = " ".join(input_content.split()[1:])
                    argsIn = args_combined.split("#") if "#" in args_combined else [
                        args_combined, ""]
                    args_name = {
                        "name":argsIn[0],
                        "discri":argsIn[1] if re.findall(r"^\d{4}$", argsIn[1]) != [] else ""
                    }
                    async def obtainMemCands(ctx, isKick: bool, tour_now, process_now, args_name):
                        if isKick:
                            return [mem for mem in tour_now["members"][process_now]["all"]
                                      if args_name["discri"] == mem.discriminator and args_name["name"] == mem.name]
                        else:
                            mem_cands_tmp = [user for user in await ctx.guild.query_members(args_name["name"]) if user.discriminator == args_name["discri"]]
                            await addNewMembers(ctx, mem_cands_tmp)
                            return [ctx.members[user.id] for user in mem_cands_tmp]

                    mem_cands = await obtainMemCands(ctx, isKick, tour_now, process_now, args_name)
                    if mem_cands == []:
                        err_content = f"該当するユーザーが見つかりません。"
                        await ctx.channel.send(err_content)
                    elif isKick is True:
                        tour_now["members"][process_now]["kick"]=list(set(tour_now["members"][process_now]["kick"]) | set(mem_cands))
                        await reloadPresent(ctx, tour_now)
                        kick_content = ", ".join(
                            [f"{mem.name}#{mem.discriminator}" for mem in mem_cands])+f"をトーナメント{tour_id}から除名しました。"
                        await ctx.channel.send(kick_content)
                        for member in mem_cands:
                            role_sf = discord.Object(tour_now["roles"][process_now].id)
                            await member.remove_roles(role_sf)
                    else: # add
                        tour_now["members"][process_now]["all"]=list(set(tour_now["members"][process_now]["all"]) | set(mem_cands))
                        await reloadPresent(ctx, tour_now)
                        add_content = ", ".join(
                            [f"{mem.name}#{mem.discriminator}" for mem in mem_cands])+f"をトーナメント{tour_id}に追加しました。"
                        await ctx.channel.send(add_content)
                        for member in mem_cands:
                            role_sf = discord.Object(tour_now["roles"][process_now].id)
                            await member.add_roles(role_sf)
                    continue

                elif input_content == "!cancel":
                    cancelContent = f"Tournament {tour_id}は中止されました。"
                    await ctx.channel.send(cancelContent)
                    await cancelTour(ctx, tour_now)
                    return
                elif input_content == "!regroup":
                    members_all = list(set(tour_now["members"][process_now]["all"]) - set(tour_now["members"][process_now]["kick"]))
                    tour_now["members"][process_now]["group"] = divideIntoGroup(members_all, number, maxNumber)
                    await showGroup(ctx, tour_now, process_now)
                    continue
                elif input_content == "!next":
                    tour_now = await reloadPresent(ctx, tour_now)
                    if len(tour_now["members"][process_now]["valid_winners"]) != len(tour_now["members"][process_now]["group"]):
                        content = f"次のグループの勝者報告が不適切です。\n" +\
                            "- "+", ".join(tour_now["members"]
                                           [process_now]["invalid_grps"])
                        await ctx.channel.send(content)
                        continue
                    else:
                        tour_now["members"][process_now +
                                            1] = {"all": tour_now["members"][process_now]["valid_winners"]}
                        break
                elif input_content == "!nextForce":
                    tour_now = await reloadPresent(ctx, tour_now)
                    if len(tour_now["members"][process_now]["valid_winners"]) == 0:
                        content = f"適切な勝者が1名も存在していません。"
                        await ctx.channel.send(content)
                        continue
                    else:
                        tour_now["members"][process_now +
                                            1] = {"all": tour_now["members"][process_now]["valid_winners"]}
                        break
            ### show winner
            async def showWinners(tour_now, process_now):
                winners_grps = tour_now["members"][process_now]["valid_winners_grps"]
                order = judgeOrder(process_now, len(
                    tour_now["members"][process_now]["all"]), tour_now["number"])
                win_content = "="*6+"\n"+f"{order} 勝者一覧\n"+"-"*6+"\n" +\
                    "\n".join([f"{k+1}: "+", ".join([s.name for s in v])
                               for k, v in winners_grps.items()]) + "\n\n"
                await send2chan(ctx, win_content, tour_now["channel_ids"]["results"])
            await showWinners(tour_now, process_now)

        victor = tour_now["victor"]
        tour_now["roles"]["victor"] = await ctx.guild.create_role(**obtainRoleArgs("victor", tour_now))
        await add_role(ctx, victor, tour_now["roles"]["victor"].id)
        role_sf = discord.Object(tour_now["roles"][process_now-1].id)
        await victor.remove_roles(role_sf)

        vict_content = f"Tournament {tour_id}が終了しました。\n" +\
            f"優勝は{victor.name}さんです。\n\n" +\
            f"`?delete {tour_id}`: このトーナメントに関するチャンネル・役職を削除します。\n" +\
            "`?deleteRes`: 終了しているトーナメントに関するチャンネル・役職をすべて削除します。"
        await ctx.channel.send(vict_content)


## Delete

async def deleteResFunc(ctx: commands.Context):
    sendContent = "終了しているトーナメントに関するチャンネル・役職を削除します。"
    await ctx.channel.send(sendContent)
    channels = [chan for chan in ctx.guild.channels
                if chan.category is not None
                and chan.category.name.startswith("Tour_")
                and chan.category.name not in ["Tour_"+tour["id"] for tour in ctx.tours.values() if "victor" not in tour.keys()]]
    for chan in channels:
        await chan.delete()
    cats = [cat for cat in ctx.guild.categories
            if cat.name.startswith("Tour_")
            and cat.name not in ["Tour_"+tour["id"] for tour in ctx.tours.values() if "victor" not in tour.keys()]]
    for cat in cats:
        await cat.delete()
    for role in [s for s in ctx.guild.roles
                    if re.findall(r"#\w{5}$", s.name) != []
                    and all([not s.name.endswith(f"#{tour_id}") for tour_id, tour in ctx.tours.items() if "victor" not in tour.keys()])]:
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


def setup(bot):
    bot.add_cog(Basic(bot))
    bot.add_cog(Delete(bot))
    bot.add_cog(Tmp(bot))
