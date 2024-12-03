from discord.ext.commands import Cog
from discord.errors import Forbidden

from ..db import db

class Welcome(Cog):
  def __init__(self, bot):
    self.bot = bot

  @Cog.listener()
  async def on_ready(self):
    if not self.bot.ready:
      self.welcome_channel = self.bot.get_channel(1305735331055669318)
      self.goodbye_channel = self.bot.get_channel(1305735405601165403)
      self.bot.cogs_ready.ready_up("welcome")
  
  @Cog.listener()
  async def on_member_join(self, member):
    db.execute("INSERT INTO exp (UserID) VALUES (?)", member.id)
    await self.welcome_channel.send(f"Welcome {member.mention} to **{member.guild.name}**! Head over to <#1280030530879885345> to say hi!")

    try:
      await member.send(f"Welcome to **{member.guild.name}**! Enjoy your stay!")

    except Forbidden:
      pass

    await member.add_roles(*(member.guild.get_role(id_) for id_ in (1305737867288514663, 1305739200225607721)))

  @Cog.listener()
  async def on_member_remove(self, member):
    db.execute("DELETE FROM exp WHERE UserID = ?", member.id)
    await self.goodbye_channel.send(f"{member.display_name} has left **{member.guild.name}**.")


async def setup(bot):
  await bot.add_cog(Welcome(bot))