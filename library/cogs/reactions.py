from datetime import datetime, timedelta

from discord import Embed, Poll
from discord.ext.commands import Cog
from discord.ext.commands import command, has_permissions

from ..db import db

numbers = ("1️⃣", "2⃣", "3⃣", "4⃣", "5⃣",
		   "6⃣", "7⃣", "8⃣", "9⃣", "🔟")

class Reactions(Cog):
  def __init__(self, bot):
    self.bot = bot
    self.polls = db.fetch_polls()

  @Cog.listener()
  async def on_ready(self):
    if not self.bot.ready:
      self.colors = {
        "❤️": self.bot.guild.get_role(1310015488885264404),
        "💙": self.bot.guild.get_role(1310015633978822697),
        "💛": self.bot.guild.get_role(1310015566479757382),
        "💚": self.bot.guild.get_role(1310015601653321852),
        "💜": self.bot.guild.get_role(1310015726517489774),
        "🖤": self.bot.guild.get_role(1310015666048204810),
      }
      self.reaction_message = await self.bot.get_channel(1310012816979263659).fetch_message(1310013080876617820)
      self.starboard_channel = self.bot.get_channel(1310032208173469756)
      self.bot.cogs_ready.ready_up("reactions")

      inactive_polls = []

      if len(self.polls) > 0:
        for question, ids in self.polls.items():
          channel = self.bot.get_channel(ids[1])
          message = await channel.fetch_message(ids[0])

          if message.poll.is_finalized():
            inactive_polls.append(question)
          else:
            self.bot.scheduler.add_job(self.poll_ended, "date", run_date=message.poll.expires_at,
                                      args=[question])

        for question in inactive_polls:
          del self.polls[question]
          db.execute("DELETE FROM polls WHERE Question = ?", question)

  @command(name="createpoll", aliases=["mkpoll"], description="Create a new poll")
  @has_permissions(manage_guild=True)
  async def create_poll(self, ctx, question: str, hours: int, multiple: str, *answers):
      if question.lower() in self.polls.keys():
        await ctx.send(f"A poll with the question '{question}' already exists.")

      else:
        if len(answers) > 10:
          await ctx.send("The amount of answers exceeded the limit of 10, please try again with fewer answers.")

        poll = Poll(question, timedelta(hours=hours), multiple=(multiple.title()))

        for idx, ans in enumerate(answers):
          poll.add_answer(text=ans, emoji=numbers[idx])

        await ctx.send(poll=poll)

        channel_id = poll.message.channel.id
        message_id = poll.message.id

        self.polls[poll.question.lower()] = (poll.message.id, poll.message.channel.id)

        db.execute("INSERT INTO polls VALUES (?, ?, ?)",
                  message_id, channel_id, poll.question.lower())
        
        self.bot.scheduler.add_job(self.poll_ended, "date", run_date=datetime.now()+timedelta(seconds=hours*3600),
                                  args=[question.lower()])
        
  async def poll_ended(self, question):
    del self.polls[question]
    db.execute("DELETE FROM polls WHERE Question = ?", question.lower())

  @command(name="endpoll", description="End an active poll")
  @has_permissions(manage_guild=True)
  async def end_poll(self, ctx, question):
    message_id, channel_id = self.polls[question.lower()] or None

    if channel_id is None or message_id is None:
      await ctx.send("I could not find an active poll with that question.")
    
    else:
      channel = self.bot.get_channel(channel_id)
      message = await channel.fetch_message(message_id)
      await message.poll.end()
      del self.polls[question.lower()]
      db.execute("DELETE FROM polls WHERE Question = ?", question.lower())

      await ctx.send(f"The *{question}* poll has been ended. The final results will be printed shortly.", delete_after=10)
 
  @command(name="activepolls", description="View all active polls")
  @has_permissions(manage_guild=True)
  async def active_polls(self, ctx):
    await ctx.send(self.polls)

  @Cog.listener()
  async def on_raw_reaction_add(self, payload):
    if self.bot.ready and payload.message_id == self.reaction_message.id:
      current_colors = filter(lambda r: r in self.colors.values(), payload.member.roles)
      await payload.member.remove_roles(*current_colors, reason="Color role reaction")
      await payload.member.add_roles(self.colors.get(payload.emoji.name), reason="Color role reaction")
      await self.reaction_message.remove_reaction(payload.emoji, payload.member)
    
    elif payload.message_id in (poll[1] for poll in self.polls):
      message = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)

      for reaction in message.reactions:
        users = [user async for user in reaction.users()]
        if (not payload.member.bot
            and payload.member in users
            and reaction.emoji != payload.emoji.name):
          await message.remove_reaction(reaction.emoji, payload.member)

    elif payload.emoji.name == "⭐":
      message = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)

      if not message.author.bot and payload.member.id != message.author.id:
        msg_id, stars = db.record("SELECT StarMessageID, Stars FROM starboard WHERE RootMessageID = ?",
                                  message.id) or (None, 0)

        embed = Embed(title="Starred message",
                      color=message.author.color,
                      timestamp=datetime.utcnow())
        
        fields = [("Author", message.author.mention, False),
                  ("Content", message.content or "See attachment", False),
                  ("Stars", stars + 1, False)]
        
        for name, value, inline in fields:
          embed.add_field(name=name, value=value, inline=inline)
          
        if len(message.attachments):
          embed.set_image(url=message.attachments[0].url)

        if not stars:
          star_message = await self.starboard_channel.send(embed=embed)
          db.execute("INSERT INTO starboard (RootMessageID, StarMessageID) VALUES (?, ?)",
                     message.id, star_message.id)
        
        else:
          star_message = await self.starboard_channel.fetch_message(msg_id) or "Message no longer exists"
          await star_message.edit(embed=embed)
          db.execute("UPDATE starboard SET Stars = Stars + 1 WHERE RootMessageID = ?", message.id)

      else:
        await message.remove_reaction(payload.emoji, payload.member)

async def setup(bot):
  await bot.add_cog(Reactions(bot))