from typing import Optional
from datetime import datetime

from discord import Embed, Member
from discord.ext.commands import Cog
from discord.ext.commands import command, BadArgument

class Info(Cog):
  def __init__(self, bot):
    self.bot = bot

  @command(name="userinfo", aliases=["memberinfo", "ui", "mi"], description="Provides information about a member.")
  async def user_info(self, ctx, target: Optional[Member]):
    target = target or ctx.author
    embed = Embed(title="User information",
                  color=target.color,
                  timestamp=datetime.utcnow())
    embed.set_thumbnail(url=target.display_avatar)

    fields = [("Name", str(target), True),
              ("ID", target.id, True),
              ("Bot", target.bot, True),
              ("Top role", target.top_role.mention, True),
              ("Status", str(target.status).title(), True),
              ("Activity", target.activity, True),
              ("Created at", target.created_at.strftime("%m/%d/%Y %H:%M:%S"), True),
              ("Joined at", target.joined_at.strftime("%m/%d/%Y %H:%M:%S"), True),
              ("Boosted", bool(target.premium_since), True)]
    
    for name, value, inline in fields:
      embed.add_field(name=name, value=value, inline=inline)

    await ctx.send(embed=embed)

  @user_info.error
  async def user_info_error(self, ctx, exc):
    if isinstance(exc, BadArgument):
      await ctx.send("I can't find that member.")

  @command(name="serverinfo", aliases=["guildinfo", "si", "gi"], description="Provides information about the server.")
  async def server_info(self, ctx):
    ban_count = 0

    embed = Embed(title="Server information",
                  color=ctx.guild.owner.color,
                  timestamp=datetime.utcnow())
    
    embed.set_thumbnail(url=ctx.guild.icon)

    statuses = [len(list(filter(lambda m: str(m.status) == "online", ctx.guild.members))),
                len(list(filter(lambda m: str(m.status) == "idle", ctx.guild.members))),
                len(list(filter(lambda m: str(m.status) == "dnd", ctx.guild.members))),
                len(list(filter(lambda m: str(m.status) == "offline", ctx.guild.members)))]

    async for entry in ctx.guild.bans():
      if entry:
        ban_count += 1

    fields = [("ID", ctx.guild.id, True),
              ("Owner", ctx.guild.owner, True),
              ("Locale", ctx.guild.preferred_locale, True),
              ("Created at", ctx.guild.created_at.strftime("%m/%d/%Y %H:%M:%S"), True),
              ("Members", len(ctx.guild.members), True),
              ("Humans", len(list(filter(lambda m: not m.bot, ctx.guild.members))), True),
              ("Bots", len(list(filter(lambda m: m.bot, ctx.guild.members))), True),
              ("Banned members", ban_count, True),
              ("Statuses", f"🟢 {statuses[0]} 🟠 {statuses[1]} 🔴 {statuses[2]} ⚪ {statuses[3]}", True),
              ("Text channels", len(ctx.guild.text_channels), True),
              ("Voice channels", len(ctx.guild.voice_channels), True),
              ("Categories", len(ctx.guild.categories), True),
              ("Roles", len(ctx.guild.roles), True),
              ("Invites", len(await ctx.guild.invites()), True),
              ("\u200b", "\u200b", True)]
    
    for name, value, inline in fields:
      embed.add_field(name=name, value=value, inline=inline)

    await ctx.send(embed=embed)
  
  @Cog.listener()
  async def on_ready(self):
    if not self.bot.ready:
      self.bot.cogs_ready.ready_up("info")

async def setup(bot):
  await bot.add_cog(Info(bot))