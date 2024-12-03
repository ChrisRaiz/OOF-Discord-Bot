from datetime import datetime, timedelta
from typing import Optional
from random import randint
from math import ceil

from discord import Member, Embed
from discord.ext.commands import Cog
from discord.ext.commands import command
from discord.ext.menus import MenuPages, ListPageSource

from ..db import db

class HelpMenu(ListPageSource):
  def __init__(self, ctx, data):
    self.ctx = ctx

    super().__init__(data, per_page=3)
  
  async def write_page(self, menu, fields=[]):
    offset = (menu.current_page*self.per_page) + 1
    len_data = len(self.entries)

    embed = Embed(title="XP Leaderboard",
                  color=self.ctx.author.color)
    embed.set_thumbnail(url=self.ctx.guild.icon)
    embed.set_footer(text=f"{offset:,} - {min(len_data, offset+self.per_page-1):,} of {len_data:,} members.")

    for name, value in fields:
      embed.add_field(name=name, value=value, inline=False)

    return embed
  
  async def format_page(self, menu, entries):
    offset = (menu.current_page*self.per_page) + 1
    fields = []
    table = ("\n".join(f"{idx+offset}. {self.ctx.bot.guild.get_member(entry[0]).display_name} (XP: {entry[1]} | Level: {entry[2]})"
            for idx, entry in enumerate(entries)))

    fields.append(("Ranks", table))

    return await self.write_page(menu, fields)

class Exp(Cog):
  def __init__(self, bot):
    self.bot = bot

  async def process_exp(self, message):
    xp, lvl, xplock = db.record("SELECT XP, Level, XPLock FROM exp WHERE UserID = ?", message.author.id)

    if datetime.utcnow() > datetime.fromisoformat(xplock):
      await self.add_xp(message, xp, lvl)

  async def add_xp(self, message, xp, lvl):
    xp_gain = int(ceil(randint(10, 20)))
    new_lvl = int(((xp+xp_gain)//42) ** 0.55)

    db.execute("UPDATE exp SET XP = XP + ?, Level = ?, XPLock = ? WHERE UserID = ?", 
               xp_gain, new_lvl, (datetime.utcnow()+timedelta(seconds=60)).isoformat(), message.author.id)
    
    if new_lvl > lvl:
      await self.level_channel.send(f"Congrats {message.author.mention} - you leveled up to {new_lvl:,}!")

  @command(name="level", aliases=["lvl"], description="Check a member's level.")
  async def display_level(self, ctx, target: Optional[Member]):
    target = target or ctx.author
    xp, lvl = db.record("SELECT XP, Level FROM exp WHERE UserID = ?", target.id) or (None, None)

    if lvl is not None:
      await ctx.send(f"{target.display_name} is level {lvl:,} with {xp:,} XP.")
    
    else:
      await ctx.send(f"{target.display_name} is not tracked by the experience system.")

  @command(name="rank", description="Check a member's rank.")
  async def display_rank(self, ctx, target: Optional[Member]):
    target = target or ctx.author

    ids = db.column("SELECT UserID FROM exp ORDER BY XP DESC")
    try:
      await ctx.send(f"{target.display_name} is rank {ids.index(target.id)+1} of {len(ids)}.")

    except ValueError:
      await ctx.send(f"{target.display_name} is not tracked by the experience system.")

  @command(name="leaderboard", aliases=["lb"], description="Display the guild's exp leaderboard.")
  async def display_leaderboard(self, ctx):
    records = db.records("SELECT UserID, XP, Level FROM exp ORDER BY XP DESC")

    menu = MenuPages(source=HelpMenu(ctx, records), delete_message_after=True, timeout=300.0)
    await menu.start(ctx)

  @Cog.listener()
  async def on_ready(self):
    if not self.bot.ready:
      self.level_channel = self.bot.get_channel(1313020049107325020)
      self.bot.cogs_ready.ready_up("exp")

  @Cog.listener()
  async def on_message(self, message):
    if not message.author.bot:
      await self.process_exp(message)


async def setup(bot):
  await bot.add_cog(Exp(bot))