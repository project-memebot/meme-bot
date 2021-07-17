import datetime
import sqlite3 as sql
from itertools import cycle
from os import listdir
from os.path import isfile
from pickle import load
import aiosqlite
import discord
import koreanbots
from discord.ext import commands, tasks
from tool import (
    errorcolor,
    get_prefix,
    CommandOnCooldown,
    MaxConcurrencyReached,
    UserOnBlacklist,
)


with open("token.bin", "rb") as tokenfile:
    token = load(tokenfile)
mentions = discord.AllowedMentions.all()
mentions.replied_user = False
bot = commands.Bot(
    command_prefix=get_prefix,
    allowed_mentions=mentions,
    owner_ids=(745848200195473490,),
    intents=discord.Intents.all(),
)
cooldown = {}
using_cmd = []
with open("koreanbots_token.bin", "rb") as f:
    koreanbots_token = load(f)
BOT = koreanbots.Koreanbots(bot, koreanbots_token, run_task=True)

presences = []


@bot.event
async def on_ready():
    global presences
    presences = cycle(
        [
            discord.Activity(
                name="짤",
                type=discord.ActivityType.watching,
                large_image_url=bot.user.avatar_url,
            ),
            discord.Activity(
                name="ㅉhelp",
                type=discord.ActivityType.listening,
                large_image_url=bot.user.avatar_url,
            ),
            discord.Activity(
                name=f"{len(bot.guilds)}서버",
                type=discord.ActivityType.playing,
                large_image_url=bot.user.avatar_url,
            ),
            discord.Activity(
                name="http://invite.memebot.kro.kr",
                type=discord.ActivityType.watching,
                large_image_url=bot.user.avatar_url,
            ),
            discord.Activity(
                name="http://support.memebot.kro.kr",
                type=discord.ActivityType.watching,
                large_image_url=bot.user.avatar_url,
            ),
            discord.Activity(
                name="http://koreanbots.memebot.kro.kr",
                type=discord.ActivityType.watching,
                large_image_url=bot.user.avatar_url,
            ),
        ]
    )
    conn = sql.connect("memebot.db", isolation_level=None)
    cur = conn.cursor()
    cur.execute(
        "CREATE TABLE IF NOT EXISTS usermeme (id INTEGER PRIMARY KEY, uploader_id INTEGER, title text, url text)"
    )
    # 유저가 업로드한 밈들 id/설명 등 매칭
    cur.execute(
        "CREATE TABLE IF NOT EXISTS blacklist (id INTEGER PRIMARY KEY, reason text)"
    )
    cur.execute(
        "CREATE TABLE IF NOT EXISTS webhooks (url text PRIMARY KEY, guild_id INTEGER)"
    )
    cur.execute(
        "CREATE TABLE IF NOT EXISTS customprefix (guild_id INTEGER PRIMARY KEY, prefix text)"
    )
    # 유저가 업로드한 밈들 보낼 웹훅
    with conn:
        with open("backup.sql", "w", encoding="UTF-8") as backupfile:
            for line in conn.iterdump():
                backupfile.write(f"{line}\n")
    conn.close()
    await (bot.get_channel(852767243360403497)).send(
        str(datetime.datetime.utcnow() + datetime.timedelta(hours=9)),
        file=discord.File("backup.sql"),
    )
    print("ready")
    cogs = [j if isfile("Cogs/" + j) else "" for j in listdir("Cogs")]
    cogs.sort()
    for file in cogs:
        if file != "":
            bot.load_extension(f"Cogs.{file[:-3]}")
            print(f"Cogs.{file[:-3]}")
    bot.load_extension("jishaku")
    print("jishaku")
    change_presence.start()
    await bot.get_channel(852767242704650290).send("켜짐")


@tasks.loop(seconds=5)
async def change_presence():
    await bot.change_presence(activity=next(presences))


@bot.before_invoke
async def before_invoke(ctx):
    if ctx.author.id in bot.owner_ids:
        return
    async with aiosqlite.connect("memebot.db", isolation_level=None) as cur:
        async with cur.execute(
            "SELECT * FROM blacklist WHERE id=?", (ctx.author.id,)
        ) as result:
            result = await result.fetchall()
            if result:
                await ctx.reply(f"{ctx.author} 님은 `{result[0][1]}`의 사유로 차단되셨습니다.")
                raise UserOnBlacklist
    if ctx.author.id in using_cmd:
        await ctx.reply("현재 실행중인 명령어를 먼저 끝내 주세요")
        raise MaxConcurrencyReached
    if (
        ctx.author.id in cooldown
        and (datetime.datetime.utcnow() - cooldown[ctx.author.id]).seconds < 3
    ):
        retry_after = datetime.datetime.utcnow() - cooldown[ctx.author.id]
        await ctx.reply(f"현재 쿨타임에 있습니다.\n{retry_after.seconds}초 후 다시 시도해 주세요")
        raise CommandOnCooldown
    using_cmd.append(ctx.author.id)
    cooldown[ctx.author.id] = datetime.datetime.utcnow()


@bot.after_invoke
async def after_invoke(ctx):
    try:
        using_cmd.remove(ctx.author.id)
    except ValueError:
        pass


@bot.event
async def on_command_error(ctx, error):
    if type(error) in [
        commands.CommandNotFound,
        commands.NotOwner,
        commands.DisabledCommand,
        commands.MissingPermissions,
        commands.CheckFailure,
        commands.MissingRequiredArgument,
    ]:
        return

    embed = discord.Embed(
        title="오류", description=f"`{ctx.message.content}`", color=errorcolor
    )
    embed.add_field(
        name="오류 발생자", value=f"{ctx.author} ({ctx.author.id})\n{ctx.author.mention}"
    )
    embed.add_field(
        name="오류 발생지",
        value=f"{ctx.guild.name} ({ctx.guild.id})\n{ctx.channel.name} ({ctx.channel.id})",
    )
    embed.add_field(name="오류 내용", value=f"```py\n{error}```")
    await (bot.get_channel(852767242704650290)).send(embed=embed)


bot.remove_command("help")
bot.run(token)
