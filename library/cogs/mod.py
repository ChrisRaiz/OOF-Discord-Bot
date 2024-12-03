import asyncio
from typing import Optional
from datetime import datetime, timedelta, timezone
from better_profanity import profanity
from re import search

from discord import Member, Embed
from discord.ext.commands import Cog, Greedy
from discord.ext.commands import CheckFailure
from discord.ext.commands import command, has_permissions, bot_has_permissions

from ..db import db

profanity.load_censor_words_from_file("./data/profanity.txt")

class Mod(Cog):
  def __init__(self, bot):
    self.bot = bot

    self.url_regex = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
    self.links_forbidden = (1305735331055669318, 1305735405601165403)
    self.images_forbidden = (1305735331055669318, 1305735405601165403)

  async def kick_members(self, message, targets, reason):
    for target in targets:
      if (message.guild.me.top_role.position > target.top_role.position
          and not target.guild_permissions.administrator):
        await target.kick(reason=reason)

        embed = Embed(title="Member kicked",
                      color=0xDD2222,
                      timestamp=datetime.utcnow())
        
        embed.set_thumbnail(url=target.display_avatar)
        
        fields = [("Member", target.display_name, False),
                  ("Actioned by", message.author.display_name, False),
                  ("Reason", reason, False)]
        
        for name, value, inline in fields:
          embed.add_field(name=name, value=value, inline=inline)

        await self.log_channel.send(embed=embed)


  @command(name="kick", description="Kick members out of the server")
  @has_permissions(kick_members=True)
  @bot_has_permissions(kick_members=True)
  async def kick_command(self, ctx, targets: Greedy[Member], *, reason: Optional[str] = "No reason provided."):
    if not len(targets):
      await ctx.send("One or more required arguments are missing.")

    else:
      await self.kick_members(ctx.message, targets, reason)
      await ctx.send("Action complete.")

  @kick_command.error
  async def kick_command_error(self, ctx, exc):
    if isinstance(exc, CheckFailure):
      await ctx.send("Insufficient permissions to perform that task.")

  async def ban_members(self, message, targets, reason):
     for target in targets:
        if (message.guild.me.top_role.position > target.top_role.position
        and not target.guild_permissions.administrator):
          await target.ban(reason=reason)

          embed = Embed(title="Member banned",
                        color=0xDD2222,
                        timestamp=datetime.utcnow())
          
          embed.set_thumbnail(url=target.display_avatar)
          
          fields = [("Member", target.display_name, False),
                    ("Actioned by", message.author.display_name, False),
                    ("Reason", reason, False)]
          
          for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)

          await self.log_channel.send(embed=embed)

  @command(name="ban")
  @has_permissions(ban_members=True)
  @bot_has_permissions(ban_members=True)
  async def ban_command(self, ctx, targets: Greedy[Member], *, reason: Optional[str] = "No reason provided."):
    if not len(targets):
      await ctx.send("One or more required arguments are missing.")

    else:
      await self.ban_members(ctx.message, targets, reason)
      await ctx.send("Action complete.")

  @ban_command.error
  async def ban_command_error(self, ctx, exc):
    if isinstance(exc, CheckFailure):
      await ctx.send("Insufficient permissions to perform that task.")

  @command(name="clear", aliases=["purge"], description="Delete 'x' amount of messages in a channel")
  @has_permissions(manage_messages=True)
  @bot_has_permissions(manage_messages=True)
  async def clear_messages(self, ctx, targets: Greedy[Member], limit: Optional[int] = 10):
    def _check(message):
      return not len(targets) or message.author in targets
    
    if 0 < limit <= 500:
     async with ctx.typing():
        await ctx.message.delete()
        deleted = await ctx.channel.purge(limit=limit, check=_check)
        await ctx.send(f"Deleted {len(deleted):,} messages.", delete_after=5)

    else:
      ctx.send("The limit provided is not within acceptable bounds.")

  @clear_messages.error
  async def clear_messages_error(self, ctx, exc):
    if isinstance(exc, CheckFailure):
      await ctx.send("Insufficient permissions to perform that task.")  

  async def mute_members(self, message, targets, minutes, reason):
    unmutes = []

    for target in targets:
      if self.mute_role not in target.roles:
        if message.guild.me.top_role.position > target.top_role.position:
          role_ids = ".".join([str(r.id) for r in target.roles])
          end_time = datetime.utcnow() + timedelta(seconds=minutes*60) if minutes else None

          db.execute("INSERT INTO mutes VALUES (?, ?, ?)",
                      target.id, role_ids, getattr(end_time, "isoformat", lambda: None)())
          
          await target.edit(roles=[self.mute_role])

          embed = Embed(title="Member muted",
                        color=0xDD2222,
                        timestamp=datetime.utcnow())
          
          embed.set_thumbnail(url=target.display_avatar)
          
          fields = [("Member", target.display_name, False),
                    ("Actioned by", message.author.display_name, False),
                    ("Duration", f"{minutes:,} minute(s)" if minutes else "Indefinite", False),
                    ("Reason", reason, False)]
          
          for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)

          await self.log_channel.send(embed=embed)

          if minutes:
            unmutes.append(target)

    return unmutes

  @command(name="mute", description="Mute a member")
  @has_permissions(manage_guild=True, manage_roles=True)
  @bot_has_permissions(manage_roles=True)
  async def mute_command(self, ctx, targets: Greedy[Member], minutes: Optional[int], *,
                         reason: Optional[str] = "No reason provided."):
    if not len(targets):
      await ctx.send("One or more required arguments are missing.")

    else:
      unmutes = await self.mute_members(ctx.message, targets, minutes, reason)
      await ctx.send("Action complete.")

      if len(unmutes):
        await asyncio.sleep(minutes)
        await self.unmute_members(ctx, targets)

  @mute_command.error
  async def mute_command_error(self, ctx, exc):
    if isinstance(exc, CheckFailure):
      await ctx.send("Insufficient permissions to perform that task.")  

  async def unmute_members(self, guild, targets, *, reason = "Mute time expired."):
    for target in targets:
      if self.mute_role in target.roles:
        role_ids = db.field("SELECT RoleIDs FROM mutes WHERE UserID = ?", target.id)
        roles = [guild.get_role(int(id_)) for id_ in role_ids.split(".") if len(id_)]

        db.execute("DELETE FROM mutes WHERE UserID = ?", target.id)

        await target.edit(roles=roles)

        embed = Embed(title="Member unmuted",
                        color=0xDD2222,
                        timestamp=datetime.utcnow())
          
        embed.set_thumbnail(url=target.display_avatar)
          
        fields = [("Member", target.display_name, False),
                  ("Reason", reason, False)]
          
        for name, value, inline in fields:
          embed.add_field(name=name, value=value, inline=inline)

        await self.log_channel.send(embed=embed)

  @command(name="unmute")
  @has_permissions(manage_guild=True, manage_roles=True)
  @bot_has_permissions(manage_roles=True)
  async def unmute_command(self, ctx, targets: Greedy[Member], *, reason: Optional[str] = "No reason provided."):
    if not len(targets):
      await ctx.send("One or more required arguments is missing.")

    else:
      await self.unmute_members(ctx.guild, targets, reason=reason)

  @unmute_command.error
  async def unmute_members_error(self, ctx, exc):
    if isinstance(exc, CheckFailure):
      await ctx.send("Insufficient permissions to perform that task.")  

  @command(name="addprofanity", aliases=["ap"])
  @has_permissions(manage_guild=True)
  async def add_profanity(self, ctx, *words):
    with open("./data/profanity.txt", "a", encoding="utf-8") as f:
      f.write("\n".join([f"{w}\n" for w in words]))

    profanity.load_censor_words_from_file("./data/profanity.txt")
    await ctx.send("Action complete.")

  @add_profanity.error
  async def add_profanity_error(self, ctx, exc):
    if isinstance(exc, CheckFailure):
      await ctx.send("Insufficient permissions to perform that task.")  

  @command(name="delprofanity", aliases=["dp"])
  @has_permissions(manage_guild=True)
  async def remove_profanity(self, ctx, *words):
    with open("./data/profanity.txt", "r", encoding="utf-8") as f:
      stored = [w.strip() for w in f.readlines()]

    with open("./data/profanity.txt", "w", encoding="utf-8") as f:
      f.write("".join([f"{w}\n" for w in stored if w not in words]))

    profanity.load_censor_words_from_file("./data/profanity.txt")
    await ctx.send("Action complete.")

  @remove_profanity.error
  async def remove_profanity_error(self, ctx, exc):
    if isinstance(exc, CheckFailure):
      await ctx.send("Insufficient permissions to perform that tasks.")

  @Cog.listener()
  async def on_ready(self):
    if not self.bot.ready:
      self.log_channel = self.bot.get_channel(1305747656320090123)
      self.mute_role = self.bot.guild.get_role(1307645692323430420)
      self.profanity_aliases = ["!addprofanity", "!ap", "!delprofanity", "!dp"]
      self.bot.cogs_ready.ready_up("mod")

  @Cog.listener()
  async def on_message(self, message):
    def _check(m):
      return(m.author == message.author
             and len(m.mentions)
             and (datetime.now(timezone.utc)-m.created_at).seconds < 60)
    
    if not message.author.bot:
      if len(list(filter(lambda m: _check(m), self.bot.cached_messages))) >= 3:
          await message.channel.send("Don't spam mentions!", delete_after=10)
          unmutes = await self.mute_members(message, [message.author], 5, reason="Mention spam")

          if len(unmutes):
            await asyncio.sleep(5)
            await self.unmute_members(message.guild, [message.author])

      elif profanity.contains_profanity(message.content):
        if not any(cmd in message.content[0:13] for cmd in self.profanity_aliases):
          await message.delete()
          await message.channel.send("That word is not allowed here.", delete_after=10)

      elif message.channel.id in self.links_forbidden and search(self.url_regex, message.content):
        await message.delete()
        await message.channel.send("You can't send links in this channel.", delete_after=10)

      elif message.channel.id in self.images_forbidden and any([hasattr(a, "width") for a in message.attachments]):
        await message.delete()
        await message.channel.send("You can't send images in this channel.", delete_after=10)
    
async def setup(bot):
  await bot.add_cog(Mod(bot))