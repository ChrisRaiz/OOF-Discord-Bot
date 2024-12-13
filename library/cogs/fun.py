from aiohttp import request
from asyncio import sleep
from datetime import datetime
from math import ceil
from random import choice, randint
from typing import Optional

from discord import Member, Embed, File
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

        
  @command(name="gamble", description="Hosts a gambling session.")
  async def host_gamble(self, ctx, rounds: int, increments: int, start_time: Optional[int] = 30):
    
    if self.gamble_channel is not None:
      active_channel = await self.bot.guild.fetch_channel(self.gamble_channel)
      await ctx.send(f"I was unable to start gambling session due to there already being an active gambling session in {active_channel.mention}.")

    elif rounds > 20:
      await ctx.send(":stop_sign: Too many rounds set, please try again with 20 rounds or less.")

    elif increments > 1000000:
      await ctx.send(":stop_sign: The increment is too high, please try again with a number less than 1,000,000.")

    else:
      gold_owed = []
      gamble_cap = int(increments)
      self.gamble_channel = ctx.message.channel.id

      session_embed = Embed(title=":game_die: Crit or Quit", 
                            description=f"{ctx.message.author.display_name} is starting a new gambling session!", 
                            color=0xB03060)
      session_embed.set_thumbnail(url=ctx.message.author.display_avatar)

      if increments <= 9999:
        field_spacer = "‏‏‎   ‎"
      elif increments <= 999999:
        field_spacer = "‏‏‎  ‎"
      else:
        field_spacer = "‏‏‎ ‎"

      session_fields = [(":stopwatch: Total Rounds", f"‏‏‎  ‎{rounds} rounds" if rounds > 1 else f"‏‏‎  ‎{rounds} round", True),
                        (":moneybag: Increments by", f"{field_spacer}{increments:,} gold", True)]
            
      for name, value, inline in session_fields:
        session_embed.add_field(name=name, value=value, inline=inline)

      sign_up_embed = Embed(title=":bellhop: Sign up", 
                            description=f"Gambling cmds only work in the active gambling channel - {ctx.message.channel.mention}", 
                            color=0xB03060)
      
      sign_up_fields = [("**Round cmds**", "> **Join:** `jr` | `1`\n> **Exit:** `lr` | `0`", True),
                        ("**Session cmds**", "> **Join:** `js` | `3`\n> **Exit:** `ls` | `2`", True)]
                        # ('\u200b', "‏‏‎              ‎", True)]
      
      for name, value, inline in sign_up_fields:
        sign_up_embed.add_field(name=name, value=value, inline=inline)

      await ctx.send(embed=session_embed,) #delete_after=start_time+5)

      while rounds:
        self.signup_active = True
        await ctx.send(embed=sign_up_embed,) #delete_after=start_time+5)
        await sleep(start_time)
        await ctx.send(embed=Embed(title=":loudspeaker: Last call to enter!", color=0xB03060), delete_after=8)
        await sleep(8)
        self.signup_active = False
        await ctx.send(embed=Embed(title=f":loudspeaker: Signups for the {gamble_cap:,}g gamble session has closed!", color=0xB03060), delete_after=8)
        await sleep(8)

        gamble_embed = Embed(title=f":game_die: {gamble_cap:,}g Gamble rolls",
                            color=0x35654D,
                            timestamp=datetime.now())
        
        i = 0
        while i < 8:
          self.gamble_users.append(f"Fake User {i}")
          i += 1

        if len(self.gamble_users) <= 1:
          await ctx.send(embed=Embed(title=":stop_sign: Not enough members to gamble! Shutting down gambling session.", color=0xB03060), delete_after=10)
          break

        self.gamble_users = sorted(self.gamble_users, key=str.lower)
        winner, loser = ("", -1), ("", 1000001)

        for user in self.gamble_users:
          gambler = (user, int(ceil(randint(0, gamble_cap))))
          winner = winner if winner[1] > gambler[1] else gambler
          loser = loser if loser[1] < gambler[1] else gambler
          gamble_embed.add_field(name=gambler[0], value=f"{gambler[1]:,}", inline=True)

        res_diff = winner[1] - loser[1]
        gold_owed.append(f"{loser[0]} owes {winner[0]} {res_diff:,}g")

        res_embed = Embed(title=f"\🎰 {gamble_cap:,}g Round results",
                          color=0x35654D,
                          timestamp=datetime.now())
        

        # winner_avatar = self.bot.guild.get_member_named(winner[0]).display_avatar
        # res_embed.set_thumbnail(url=winner_avatar)
        res_embed.set_footer(text=f"{rounds-1} rounds remaining" if rounds != 2 else f"{rounds-1} round remaining")

        res_fields = [("Winner", winner[0], True),
                      ("Winning roll", winner[1], True),
                      ("", "", True),
                      ("Loser", loser[0], True),
                      ("Losing roll", loser[1], True),
                      ("", "", True),
                      (f"{loser[0]} owes {winner[0]}", f"{res_diff:,} gold", True)]
        
        for name, value, inline in res_fields:
          res_embed.add_field(name=name, value=value, inline=inline)

        await ctx.send(embed=gamble_embed, delete_after=60)
        await ctx.send(embed=Embed(title=f"\📢 and the winner of the {gamble_cap} gold round is...", color=0xB03060), delete_after=5)
        # await sleep(5)
        await ctx.send(embed=Embed(title=f"\📢 and the winner of the {gamble_cap} gold round is {winner[0]}!", color=0xB03060), delete_after=8)
        await ctx.send(embed=res_embed)
        # await sleep(8)
        await ctx.send(embed=Embed(title="\📢 The next round signup will start in 5 seconds!", color=0xB03060), delete_after=5) if rounds-1 > 0 else None
        # await sleep(5)
        print(f'BEFORE\nGamble_users: {self.gamble_users} | session_users: {self.session_users}')
        self.gamble_users = []

        for user in self.session_users:
          self.gamble_users.append(user)

        print(f'AFTER\nGamble_users: {self.gamble_users} | session_users: {self.session_users}')
        gamble_cap = gamble_cap + increments
        rounds -= 1

      owed_embed = Embed(title='Gold payouts', color=0xFFEB80)
      owed_thumbnail = File('./data/images/gold-icon.jpg')
      owed_embed.set_thumbnail(url='attachment://gold-icon.jpg')

      for payout in gold_owed:
        owed_embed.add_field(name=payout, value="", inline=False)

      await ctx.send(file=owed_thumbnail, embed=owed_embed)

      self.gamble_users, self.session_users, self.gamble_channel = [], [], None

  @Cog.listener()
  async def on_message(self, message):
    if not message.author.bot:
      if (message.channel.id == self.gamble_channel 
          and self.signup_active is True
          and len(self.gamble_users) <= 25):
        
        cmd = message.content.lower()

        if cmd in self.gamble_cmds[0] and message.author.display_name not in self.gamble_users:
          if cmd in self.gamble_cmds[0][2:4] and message.author.display_name not in self.session_users:
            self.session_users.append(message.author.display_name)
          self.gamble_users.append(message.author.display_name)

        elif cmd in self.gamble_cmds[1] and message.author.display_name in self.gamble_users:
          if cmd in self.gamble_cmds[1][2:4] and message.author.display_name in self.session_users:
            self.session_users.remove(message.author.display_name)
          self.gamble_users.remove(message.author.display_name)

      elif len(self.gamble_users) == 25:
        await message.channel.send(f"Sorry {message.author.mention}, the current round has hit the maximum capacity of 25 gamblers.", delete_after=10)

      await message.delete()

  @Cog.listener()
  async def on_ready(self):
    if not self.bot.ready:
      self.signup_active = False
      self.gamble_users = []
      self.session_users = []
      self.gamble_channel = None
      self.gamble_cmds = [["1", "jr", "3", "js"],["0", "lr", "2", "ls"]]
      self.bot.cogs_ready.ready_up("fun")
  
async def setup(bot):
  await bot.add_cog(Fun(bot))