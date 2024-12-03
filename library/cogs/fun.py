from random import choice, randint
from typing import Optional

from aiohttp import request
from discord import Member, Embed
from discord.ext.commands import Cog
from discord.ext.commands import command, cooldown, BadArgument, BucketType

class Fun(Cog):
  def __init__(self, bot):
    self.bot = bot
  
  @command(name="hello", aliases=["hi"], description="Greets the author of the command.")
  async def say_hello(self, ctx):
    await ctx.send(f"{choice(('Hello', 'Howdy', 'Well met', 'Greetings'))} {ctx.author.mention}!")
  
  @command(name="dice", aliases=["roll"], description="Rolls 'x' amount of 'y' sided die.")
  @cooldown(1, 60, BucketType.user)
  async def roll_dice(self, ctx, die_string: str):
    dice, value = (int(num) for num in die_string.split("d"))

    if dice <= 25:
      rolls = [randint(1, value) for i in range(dice)]

      await ctx.send(" + ".join([str(r) for r in rolls]) + f" = {sum(rolls)}")
    else :
      await ctx.send("I can't roll that many dice. Please try a lower number.")

  @roll_dice.error
  async def roll_dice_error(self, ctx, exc):
    if isinstance(exc, BadArgument):
      await ctx.send("I didn't understand how many dice to roll or how many sides each die has.")

  @command(name="slap", aliases=["hit"], description="Slaps a guild member for 'x' reason.")
  async def slap_member(self, ctx, member: Member, *, reason: Optional[str] = "no reason"):
    await ctx.send(f"{ctx.author.display_name} slapped {member.mention} for {reason}!")
  
  @slap_member.error
  async def slap_member_error(self, ctx, exc):
    if isinstance(exc, BadArgument):
      await ctx.send("I can't find that member.")
  
  @command(name="echo", aliases=["say"], description="Repeats the author's message.")
  @cooldown(1, 15, BucketType.guild)
  async def echo_message(self, ctx, *, message):
    await ctx.message.delete()
    await ctx.send(message)

  @command(name="fact", aliases=["animal", "fa"], description="Generates a random animal fact.")
  @cooldown(3, 60, BucketType.guild)
  async def animal_fact(self, ctx, animal: Optional[str]):
    if animal is None :
      animal = choice(("dog", "cat", "bird", "fox"))

    if animal.lower() in ("dog", "cat", "bird", "fox"):
      URL = f"https://some-random-api.com/animal/{animal.lower()}"

      async with request("GET", URL, headers={}) as response:
        if response.status == 200:
          data = await response.json()
          
          embed = Embed(title=f"{animal.title()} fact",
                        description=data["fact"],
                        color=ctx.author.color)
          
          if data["image"] is not None:
            embed.set_image(url=data["image"])

          await ctx.send(embed=embed)

        else:
          await ctx.send(f"API returned a {response.status} status.")

    else:
      await ctx.send("No facts are available for that animal.")


  @Cog.listener()
  async def on_ready(self):
    if not self.bot.ready:
      self.bot.cogs_ready.ready_up("fun")
  
async def setup(bot):
  await bot.add_cog(Fun(bot))