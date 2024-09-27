# ORION Discord Bot

A versatile Discord bot built using Python and `discord.py`, featuring music playback, user leveling, and moderation commands.

## Features

- 🎵 **Music Playback**: Play, pause, skip, and queue songs from YouTube in voice channels.
- 📋 **Playlist Management**: Save and load song queues for future playback.
- 🏆 **Leveling System**: Track user activity and assign levels/roles based on experience points.
- 📈 **Leaderboard**: Display a leaderboard showing top users based on XP.
- 🛠 **Moderation Tools**: Kick, ban, unban, mute, and unmute members with custom moderation logs.
  
## Installation

1. Download `Orion.py`
2. Replace `ROLE_1_NAME_HERE` `ROLE_2_NAME_HERE` `YOUR_LOG_CHANNEL_ID_HERE` `YOUR_BOT_TOKEN_HERE`
- ROLE_1_NAME_HERE: The name of the role that will be assigned at level 1.
- ROLE_2_NAME_HERE: The name of the role that will be assigned at level 5.
- YOUR_LOG_CHANNEL_ID_HERE: The channel ID where the bot will send logs (for kicks, bans, etc.).
- YOUR_BOT_TOKEN_HERE: Your Discord bot token from the Discord Developer Portal.
3. Run the bot

## Usage

### Bot Commands
- **Music Commands**:
  - `!play [song]`: Plays a song from YouTube.
    -  Can use either search query or video link for [song]
    -  Sends an embed that includes song information and playback control (pause, resume, stop, skip, restart, and play last) via message reactions.
    -  `!play q` will play the current queue.
    -  `!play queue: [playlist name]` can be used to play a saved playlist.
  - `!pause`: Pauses the currently playing song.
  - `!resume`: Resumes the currently playing song.
  - `!stop`: Stops the music and clears the queue.
  - `!add [song]`: Adds a song to the queue.
    -  Can use either search query or video link for [song]
  - `!queue` or `!q`: Shows the current song queue and history.
    -  Songs in the queue will play once the current song finishes or once skip is pressed.
  - `!clear-queue` or `!clearq`: Clears the current song queue.
  - `!save [name]`: Saves the current song queue as a playlist.
- **Moderation Commands**:
  - `!kick [@user] [reason]`: Kicks a user from the server and sends log to specified channel.
  - `!ban [@user] [reason]`: Bans a user from the server and sends log to specified channel.
  - `!unban [username#discriminator]`: Unbans a user and sends log to specified channel.
  - `!mute [@user] [reason]`: Mutes a user and sends log to specified channel.
  - `!unmute [@user]`: Unmutes a user and sends log to specified channel.
  - `!clear [number]`: Clears a specified number of messages from the chat, by default 5.

- **Leveling and XP Commands**:
  - `!stats [@user]`: Displays the level, exp, rank, and progress of a user.
  - `!leaderboard`: Shows the XP leaderboard for the server.
