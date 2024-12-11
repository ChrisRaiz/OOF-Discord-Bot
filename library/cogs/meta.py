from platform import python_version
from datetime import datetime, timedelta
from time import time

from apscheduler.triggers.cron import CronTrigger
from discord import Activity, ActivityType, Embed
from discord import __version__ as discord_version
from discord.ext.commands import Cog
from discord.ext.commands import command, has_permissions
from psutil import Process, virtual_memory

from ..db import db

class Meta(Cog):
  def __init__(self, bot):
    self.bot = bot
    
    self._message = "watching !help | {users:,} users in {guilds:,} servers"

    bot.scheduler.add_job(self.set, CronTrigger(second=0))

  @property
  def message(self):
    return self._message.format(users=len(self.bot.users), guilds=len(self.bot.guilds))
  
  @message.setter
  def message(self, value):
    if value.split(" ")[0] not in ("playing", "watching", "listening", "streaming"):
      raise ValueError("Invalid activity type")
    
    self._message = value
  
  async def set(self):
    _type, _name = self.message.split(" ", maxsplit=1)

    await self.bot.change_presence(activity=Activity(
      name=_name, type=getattr(ActivityType, _type, ActivityType.playing)
    ))

  @command(name="setactivity", description="Set the bot's activity status")
  @has_permissions(manage_guild=True)
  async def set_activity_message(self, ctx, *, activity: str):
    self.message = activity
    await self.set()

  @command(name="ping", description="Get DWSP latency and response time")
  async def ping(self, ctx):
    start = time()
    message = await ctx.send(f"DWSP latency: {self.bot.latency * 1000:,.0f} ms")
    end = time()

    await message.edit(content=f"DWSP latency: {self.bot.latency * 1000:,.0f} ms.\nResponse time: {(end-start)*1000:,.0f} ms.")

  @command(name="stats", description="Provides information about the bot.")
  async def show_bot_stats(self, ctx):
    embed = Embed(title="Bot stats",
                  color=ctx.author.color,
                  timestamp=datetime.utcnow())
    
    embed.set_thumbnail(url=ctx.guild.me.avatar)
    
    proc = Process()
    with proc.oneshot():
      uptime = timedelta(seconds=time()-proc.create_time())
      cpu_time = timedelta(seconds=(cpu := proc.cpu_times()).system + cpu.user)
      mem_total = virtual_memory().total / (1024 ** 3)
      mem_of_total = proc.memory_percent()
      mem_usage = mem_total * (mem_of_total / 100)
    
    fields = [
      ("Bot version", self.bot.VERSION, True),
      ("Python version", python_version(), True),
      ("discord.py version", discord_version, True),
      ("Uptime", f"{uptime}"[0:10], True),
      ("CPU time", f"{cpu_time}"[0:10], True),
      ("Memory usage", f"{mem_usage:,.3f} GB / {mem_total:,.0f} GB ({mem_of_total:.0f}%)", True),
    ]

    for name, value, inline in fields:
      embed.add_field(name=name, value=value, inline=inline)

    await ctx.send(embed=embed)

  @command(name="shutdown", description="Shutdown the discord bot")
  async def shutdown(self, ctx):
    await ctx.send("Shutting down...")

    db.commit()
    self.bot.scheduler.shutdown()
    await self.bot.close()

  @Cog.listener()
  async def on_ready(self):
    if not self.bot.ready:
      self.bot.cogs_ready.ready_up("meta")

async def setup(bot):
  await bot.add_cog(Meta(bot))