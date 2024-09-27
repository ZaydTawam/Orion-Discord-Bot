import re
import datetime
import discord
from discord.ext import commands
import requests
import json
import math
import aiosqlite
import asyncio
import urllib.request
import yt_dlp

intents = discord.Intents().all()
client = commands.Bot(command_prefix = "!", help_command = None, intents = intents)
client.multiplier = 5

queue = []
previous_songs = []
YDL_OPTIONS = {'format': 'bestaudio', 'noplaylist':'True'}
FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}

def search(search):
  search = search.replace(" ", "+")
  html = urllib.request.urlopen(f"https://www.youtube.com/results?search_query={search}")
  video_ids = re.findall(r"watch\?v=(\S{11})", html.read().decode())
  return str(f"https://www.youtube.com/watch?v={video_ids[0]}")

def load_playlist(name):
  name = str(name) + " - "
  playlist = None
  with open("saved-queues.txt", "r") as file:
    for line in file:
      if line.startswith(name):
          playlist = line.replace(name, "").split(" -- ")

  if playlist:
    return [song.strip().split("---") for song in playlist]
  else:
    return False
  
async def send_log(ctx, member, reason, action, color):
  embed = discord.Embed(colour = color)
  embed.set_author(name=f"{action} | {member.mention}")
  embed.add_field(name="User", value = member.mention, inline = True)
  embed.add_field(name ="Moderator", value = ctx.author.mention, inline = True)
  if reason is not None:
    embed.add_field(name ="Reason", value = reason, inline = True)
  await client.get_channel("YOUR_LOG_CHANNEL_ID_HERE").send(embed = embed)

async def initialise_db():
    client.db = await aiosqlite.connect("expData.db")
    await client.db.execute("CREATE TABLE IF NOT EXISTS guildData (guild_id int, user_id int, exp int, PRIMARY KEY (guild_id, user_id))")

@client.event
async def on_ready():
  print("Logged in as {0.user}".format(client))
  await initialise_db()

@client.event
async def on_message(message):
  member = message.author
  if not message.author.bot:
    cursor = await client.db.execute("INSERT OR IGNORE INTO guildData (guild_id, user_id, exp) VALUES (?,?,?)", (message.guild.id, message.author.id, 1)) 

    if cursor.rowcount == 0:
      await client.db.execute("UPDATE guildData SET exp = exp + 1 WHERE guild_id = ? AND user_id = ?", (message.guild.id, message.author.id))
      cur = await client.db.execute("SELECT exp FROM guildData WHERE guild_id = ? AND user_id = ?", (message.guild.id, message.author.id))
      data = await cur.fetchone()
      exp = data[0]
      lvl = math.sqrt(exp) / client.multiplier

      if lvl.is_integer():
        await message.channel.send(f"{message.author.mention} has proceeded to {int(lvl)}.", delete_after = 3)
        if lvl == 5:
          role = discord.utils.get(member.guild.roles, name = "ROLE_1_NAME_HERE")
          await member.remove_roles(role)
          role = discord.utils.get(member.guild.roles, name = "ROLE_2_NAME_HERE")
          await member.add_roles(role)

    await client.db.commit()

  await client.process_commands(message)

@client.event
async def on_member_join(member):
  role = discord.utils.get(member.guild.roles, name = "1")
  await member.add_roles(role)

@client.command()
async def stats(ctx, member: discord.Member=None):
  if member is None: member = ctx.author

  # get user exp
  async with client.db.execute("SELECT exp FROM guildData WHERE guild_id = ? AND user_id = ?", (ctx.guild.id, member.id)) as cursor:
    data = await cursor.fetchone()
    exp = data[0]

  # calculate rank
  async with client.db.execute("SELECT exp FROM guildData WHERE guild_id = ?", (ctx.guild.id,)) as cursor:
    rank = 1
    async for value in cursor:
      if exp < value[0]:
        rank += 1

  lvl = int(math.sqrt(exp)//client.multiplier)

  current_lvl_exp = (client.multiplier*(lvl))**2
  next_lvl_exp = (client.multiplier*((lvl+1)))**2

  lvl_percentage = ((exp-current_lvl_exp) / (next_lvl_exp-current_lvl_exp)) * 100

  embed = discord.Embed(title=f"Stats for {member.name}", colour = 0xFFFFFF)
  embed.add_field(name="Level", value = f"`{str(lvl)}`", inline = False)
  embed.add_field(name="Exp", value = f"`{exp}/{next_lvl_exp}`", inline = False)
  embed.add_field(name="Rank", value = f"`{rank}/{ctx.guild.member_count}`", inline = False)
  embed.add_field(name="Level Progress", value = f"`{round(lvl_percentage, 2)}%`", inline = False)
  await ctx.send(embed = embed)

@client.command()
async def leaderboard(ctx):
  async with client.db.execute(f"SELECT user_id, exp FROM guildData WHERE guild_id = ? ORDER BY exp DESC", (ctx.guild.id,)) as cursor:
    embed = discord.Embed(title="Leaderboard")
    index = 0
    
    async for entry in cursor:
        member = ctx.guild.get_member(entry[0])

        if member is not None and not member.bot:
            index += 1
            embed.add_field(name=f"{index}. {member.display_name}", value=f"Exp: {entry[1]}", inline=False)
    
    if index == 0:
        embed.description = "No valid users found on the leaderboard."

    await ctx.send(embed=embed)

@client.command()
async def join(ctx):
    if ctx.author.voice is None:
        await ctx.send("You are not connected to a voice channel.", delete_after = 3)
    else:
        channel = ctx.author.voice.channel
        if ctx.voice_client is None:
            await channel.connect()
        elif ctx.voice_client.channel != channel:
            await ctx.voice_client.move_to(channel)
        else:
            await ctx.send("I am already connected to your voice channel.", delete_after = 3)

@client.command()
async def leave(ctx):
  if ctx.voice_client is None:
    await ctx.send("I am not connected to a voice channel.", delete_after = 3)
  else:
    await ctx.voice_client.disconnect()

@client.command()
async def play(ctx, *, args = None):
  global queue, previous_songs

  if args is None:
    return await ctx.send("You must include a song to play.", delete_after = 3)

  if ctx.author.voice is None:
    return await ctx.send("You are not in a voice channel.", delete_after = 3)

  voice_channel = ctx.author.voice.channel
  if ctx.voice_client is None:
    await voice_channel.connect()
  else:
    await ctx.voice_client.move_to(voice_channel)

  if "queue: " in args:
    playlist_name = args.replace("queue: ", "")
    if load_playlist(playlist_name):
      queue.clear()
      previous_songs.clear()
      queue = load_playlist(playlist_name)
      url = queue.pop(0)[1]
    else:
      return await ctx.send("Playlist does not exist.", delete_after = 3)
  elif args == "q":
    if queue:
      url = queue.pop(0)[1]
    else:
      return await ctx.send("Queue is empty.", delete_after = 3)
  else:
    url = search(args) if "youtube.com/watch?" not in args else args
  
  ctx.voice_client.stop()

  with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
    info = ydl.extract_info(url, download=False)
    source = await discord.FFmpegOpusAudio.from_probe(info['url'], **FFMPEG_OPTIONS)
    ctx.voice_client.play(source)
  
  embed = discord.Embed(title = "Currently Playing", colour = 0xFFFFFF)
  embed.add_field(name = "Song", value = info.get('title', None), inline = False)
  embed.add_field(name = "Length", value = str(datetime.timedelta(seconds = info['duration'])), inline = False)
  embed.add_field(name = "Link", value = url, inline = False)
  msg = await ctx.send(embed=embed)

  await msg.add_reaction("\u23F8")
  await asyncio.sleep(0.5)
  await msg.add_reaction("\u25B6")
  await asyncio.sleep(0.5)
  await msg.add_reaction("\u23F9")
  await asyncio.sleep(0.5)
  await msg.add_reaction("\U0001F504")
  if previous_songs:
    await asyncio.sleep(0.5)
    await msg.add_reaction("\u23EE")
  if queue:
    await asyncio.sleep(0.5)
    await msg.add_reaction("\u23ED")

  current_song = [info.get('title', None), url]

  async def process_reaction(reaction, user):
    if queue:
      await msg.add_reaction("\u23ED")

    if reaction.emoji == "\u23F8":
      await msg.remove_reaction(reaction.emoji, user)
      ctx.voice_client.pause()
    elif reaction.emoji == "\u25B6":
      await msg.remove_reaction(reaction.emoji, user)
      ctx.voice_client.resume()
    elif reaction.emoji == "\u23F9":
      await msg.remove_reaction(reaction.emoji, user)
      ctx.voice_client.stop()
      queue.clear()
      previous_songs.clear()
      await ctx.send("Music has stopped.", delete_after = 3)
      return
    elif reaction.emoji == "\U0001F504":
      await msg.remove_reaction(reaction.emoji, user)
      ctx.voice_client.stop()
      with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
        info = ydl.extract_info(url, download=False)
        new_source = await discord.FFmpegOpusAudio.from_probe(info['url'], **FFMPEG_OPTIONS)
      ctx.voice_client.play(new_source)
    elif reaction.emoji == "\u23EE":
      await msg.remove_reaction(reaction.emoji, user)
      queue.insert(0, current_song)
      queue.insert(0, previous_songs.pop())
      ctx.voice_client.stop()
    elif reaction.emoji == "\u23ED":
      await msg.remove_reaction(reaction.emoji, user)
      ctx.voice_client.stop()
    
  while ctx.voice_client.is_playing() or ctx.voice_client.is_paused():
    try:
      reaction, user = await client.wait_for(
        "reaction_add",
        check=lambda reaction, user: not user.bot and reaction.message.id == msg.id and reaction.emoji in ["\u23F8", "\u25B6", "\u23F9","\U0001F504", "\u23EE", "\u23ED"], 
        timeout = info['duration']
      )
    except asyncio.TimeoutError:
      break

    await process_reaction(reaction, user)

  await msg.clear_reactions()
  previous_songs.append(current_song)
  if queue:
    await play(ctx, args = queue.pop(0)[1])

@client.command(aliases = ['queue'])
async def q(ctx):
  if not queue:
    return await ctx.send("The queue is empty.", delete_after = 3)
  if previous_songs:
    embed = discord.Embed(title = "History", colour = 0xFFFFFF)
    for i in range(len(previous_songs)):
      embed.add_field(name = f"{i + 1}.", value = f"> {previous_songs[i][0]}\n> {previous_songs[i][1]}", inline = False)
    await ctx.send(embed=embed)
  embed = discord.Embed(title = "Playing Next", colour = 0xFFFFFF)
  for i in range(len(queue)):
    embed.add_field(name = f"{i + 1}.", value = f"> {queue[i][0]}\n> {queue[i][1]}", inline = False)
  await ctx.send(embed=embed)

@client.command()
async def add(ctx, *, args = None):
  if args is None:
    return await ctx.send("You must include a song to add.", delete_after = 3)
  
  url = search(args) if "youtube.com/watch?" not in args else args
  ydl = yt_dlp.YoutubeDL({'outtmpl': '%(id)s.%(ext)s'})
  with ydl:
    info = ydl.extract_info(url, download=False)
    title = info['title']
  queue.append([title, url])
  await ctx.send(f"Song: {title} added.", delete_after = 3)

@client.command()
async def save(ctx, *, name = None):
  if name is None:
    return await ctx.send("You must provide a name for the playlist.", delete_after = 3)
  if queue == []:
    return await ctx.send("Queue is empty.", delete_after = 3)
  file = open("saved-queues.txt", "w")
  file.write(str(name + " - "))
  for i in range(len(queue)):
      file.write(f"{queue[i][0]}---{queue[i][1]} -- ")
  file.write("\n")
  file.close()
  await ctx.send("Playlist saved.", delete_after = 3)

@client.command(aliases = ['clear-queue'])
async def clearq(ctx):
  queue.clear()
  previous_songs.clear()
  await ctx.send("Queue cleared.", delete_after = 3)

@client.command()
async def resume(ctx):
  await ctx.voice_client.resume()

@client.command()
async def pause(ctx):
  await ctx.voice_client.pause()

@client.command()
async def stop(ctx):
  ctx.voice_client.stop()
  queue.clear()
  previous_songs.clear()
  await ctx.send("Music has stopped.", delete_after = 3)

@client.command()
async def next(ctx):
  await ctx.voice_client.stop()

@client.command()
@commands.has_permissions(manage_messages = True)
async def clear(ctx, amount = 5):
  await ctx.channel.purge(limit = amount + 1)
  await ctx.send(f"Cleared {amount} messages as requested by {ctx.message.author.mention}.", delete_after = 3)

@client.command()
async def ping(ctx):
  await ctx.send(f"`{round(client.latency * 1000)}ms`")

@client.command()
async def inspire(ctx):
  response = requests.get("https://zenquotes.io/api/random")
  json_data = json.loads(response.text)
  quote = json_data[0]['q'] + "\n-" + json_data[0]['a']
  await ctx.channel.send(quote)

#$kick
@client.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason = None):
  await member.kick(reason = reason)
  await ctx.send(f"Kicked {member} as requested by {ctx.message.author.mention}.", delete_after = 3)
  await send_log(ctx, member, reason, "Kick", discord.Colour.red())

#$ban
@client.command()
@commands.has_permissions(ban_members = True)
async def ban(ctx, member : discord.Member, *, reason = None):
  await member.ban(reason = reason)
  await ctx.send(f"Banned {member} as requested by {ctx.message.author.mention}.", delete_after = 3)
  await send_log(ctx, member, reason, "Ban", discord.Colour.red())
  
#$unban
@client.command()
@commands.has_permissions(ban_members = True)
async def unban(ctx, *, member):
    banned_users = await ctx.guild.bans()
    member_name, member_discriminator = member.split("#")
    for ban_entry in banned_users:
      user = ban_entry.user
      if (user.name, user.discriminator) == (member_name, member_discriminator):
        await ctx.guild.unban(user)
        await ctx.send(f"Unbanned {user.mention} as requested by {ctx.message.author.mention}.", delete_after = 3)
        await send_log(ctx, member, None, "Unban", discord.Colour.green())
        return

@client.command()
@commands.has_permissions(kick_members = True)
async def mute(ctx, member : discord.Member, *, reason =  None):
  guild = ctx.guild
  muted_role = discord.utils.get(guild.roles, name = "Muted")
  await member.add_roles(muted_role, reason = reason)
  await ctx.send(f"Muted {member} as requested by {ctx.message.author.mention}.", delete_after = 3)
  await member.send(f"You were muted in the server {guild.name} for {reason}.")
  await send_log(ctx, member, reason, "Mute", discord.Colour.red())

@client.command()
@commands.has_permissions(kick_members = True)
async def unmute(ctx, member : discord.Member):
  muted_role = discord.utils.get(ctx.guild.roles, name = "Muted")
  await member.remove_roles(muted_role)
  await ctx.send(f"Unmuted {member} as requested by {ctx.message.author.mention}.", delete_after = 3)
  await send_log(ctx, member, None, "Unmute", discord.Colour.green())

@client.event
async def on_command_error(ctx, error):
  if isinstance(error, commands.MissingPermissions):
    await ctx.send("Sorry, you can't do that.")

client.run('YOUR_BOT_TOKEN_HERE')