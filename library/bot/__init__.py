# from datetime import datetime
import asyncio
from glob import glob
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from discord import Intents, Embed, File, DMChannel
from discord.errors import HTTPException, Forbidden
from discord.ext.commands import Bot as BotBase
from discord.ext.commands import Context, when_mentioned_or
from discord.ext.commands import (CommandNotFound, CommandOnCooldown, BadArgument, MissingRequiredArgument)

from ..db import db

INTENTS = Intents.all()
OWNER_IDS = [410939480397053973]
COGS = [path.split("/")[-1][:-3] for path in glob("library/cogs/*.py")]
IGNORE_EXCEPTIONS = (CommandNotFound, BadArgument)

def get_prefix(bot, message):
  prefix = db.field("SELECT Prefix FROM guilds WHERE GuildID = ?", message.guild.id)

  return when_mentioned_or(prefix)(bot, message)

class Ready(object):
  def __init__(self):
    for cog in COGS:
      setattr(self, cog, False)

  def ready_up(self, cog):
    setattr(self, cog, True)
    print(f"{cog} cog ready!")

  def all_ready(self):
    return all([getattr(self, cog) for cog in COGS])

class Bot(BotBase):
  def __init__(self):
    self.INTENTS = INTENTS
    self.ready = False
    self.cogs_ready = Ready()
    self.guild = None
    self.scheduler = AsyncIOScheduler()

    db.autosave(self.scheduler)

    super().__init__(
      command_prefix=get_prefix,
      owner_ids=OWNER_IDS,
      intents=INTENTS
    )
  
  async def setup(self):
      for cog in COGS:
          await self.load_extension(f"library.cogs.{cog}")
          print(f"{cog} cog loaded!")
      print("Setup complete!!")

  def update_db(self):
    db.multi_execute("INSERT OR IGNORE INTO guilds (GuildID) VALUES (?)", 
                    ((guild.id,) for guild in self.guilds))
    
    db.multi_execute("INSERT OR IGNORE INTO exp (UserID) VALUES (?)",
                     ((member.id,) for member in self.guild.members if not member.bot))
    
    to_remove = []
    stored_members = db.column("SELECT UserID from exp")

    for _id in stored_members:
      if not self.guild.get_member(_id):
        to_remove.append(_id)

    db.multi_execute("DELETE FROM exp WHERE UserID = ?", 
                     ((_id,) for _id in to_remove))
    
    db.commit()
  
  def run(self, version):
    self.VERSION = version

    print("Running setup ... ...")
    asyncio.run(self.setup())

    with open('./library/bot/token.0', 'r', encoding='utf-8') as token_file:
      self.TOKEN = token_file.read()

    print("Running bot...")
    super().run(self.TOKEN, reconnect=True)

  async def process_commands(self, message):
    ctx = await self.get_context(message, cls=Context)

    if ctx.command is not None and ctx.guild is not None:
      if self.ready:
        await self.invoke(ctx)
      else:
        await ctx.send("Bot is still initializing, failed to execute command.")

  async def rules_reminder(self):
    await self.stdout.send("Remember to adhere to the rules!")

  async def on_connect(self):
    print("bot connected.")

  async def on_disconnect(self):
    print("bot disconnected.")
  
  async def on_error(self, err, *args, **kwargs):
    if err == "on_command_error":
      await args[0].send(f"A {err} has occurred.")
    else:
      await self.err_channel.send(f"A {err} has occurred.")
    raise 

  async def on_command_error(self, ctx, exc):
    if any([isinstance(exc, error) for error in IGNORE_EXCEPTIONS]):
      pass

    elif isinstance(exc, MissingRequiredArgument):
      await ctx.send("Missing one or more required arguments.")

    elif isinstance(exc, CommandOnCooldown):
      await ctx.send(f"That command is on {str(exc.type).split('.')[-1]} cooldown. Try again is {exc.retry_after:,.2f} seconds.")

    elif hasattr(exc, "original"):
    # elif isinstance(exc.original, HTTPException):
    #   await ctx.send("Unable to send message.")
      if isinstance(exc.original, Forbidden):
        await ctx.send("I do not have valid permissions.")
      else:
        raise exc.original
      
    else:
      raise exc

  async def on_ready(self):
    if not self.ready:
      self.guild = self.get_guild(1280030530250735677) # ONLY FOR Single Server Bot Testing
      self.stdout = self.get_channel(1280030530879885345)
      self.err_channel = self.get_channel(1308474152356810752)
      self.scheduler.add_job(self.rules_reminder, CronTrigger(day_of_week = 0, hour = 12, minute = 0, second = 0)) # Send timed message
      self.scheduler.start()

      self.update_db()

      # icon = self.get_user(1267992877615681536).display_avatar

      # embed = Embed(title="Now Online!", description="WoWFinder is now live!", color=0xFF0000, timestamp=datetime.utcnow())
      # fields = [("Name", "Value", True),
      #           ("Another Field", "This field is next to the other one.", True),
      #           ("A non-inline field", "This field will appear on it's own row.", False)]
      
      # Generate embed
      # for name, value, inline in fields:
      #   embed.add_field(name=name, value=value, inline=inline)
      # embed.set_author(name="WoWFinder", icon_url=icon)
      # embed.set_footer(text="This is a footer!")
      # thumbnail_img = File('./data/images/profile.png')
      # embed.set_thumbnail(url="attachment://profile.png")
      # embed.set_image(url=self.guild.icon)

      # Send Embed
      # await channel.send(file=thumbnail_img, embed=embed)

      # Send a file
      # await channel.send(file=File("./data/images/profile.png"))

      while not self.cogs_ready.all_ready():
        await asyncio.sleep(0.5)

      # await self.stdout.send("Now Online!")
      self.ready = True
      print('bot ready')

      meta = self.get_cog("Meta")
      await meta.set()
      
    else:
      print('bot reconnected')

  async def on_message(self, message):
    if not message.author.bot:
      if isinstance(message.channel, DMChannel):
        if len(message.content) < 10:
          await message.channel.send("Your message must be at least 10 characters in length.")
        
        else:
          member = self.guild.get_member(message.author.id)
          embed = Embed(title="Modmail",
                        color=member.color,
                        timestamp=datetime.utcnow())
          
          embed.set_thumbnail(url=member.display_avatar)
          
          fields = [("Member", member.display_name, False),
                    ("Message", message.content, False)]
            
          for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)

          mod = self.get_cog("Mod")
          await mod.log_channel.send(embed=embed)
          await message.channel.send("Message relayed to moderators.")

      else:
        await self.process_commands(message)

bot = Bot()
  