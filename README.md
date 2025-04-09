# Waifu.exe Discord Bot

A Discord bot that responds to messages with voice replies using text-to-speech technology.

## Features

- Responds to text messages with voice replies
- Uses Google Text-to-Speech for voice generation
- Supports Vietnamese language
- Simple command interface

## Setup

1. Install the required dependencies:

```bash
pip install -r requirements.txt
```

2. Install FFmpeg:

   - Windows: Download from https://ffmpeg.org/download.html and add to PATH
   - Linux: `sudo apt-get install ffmpeg`
   - macOS: `brew install ffmpeg`

3. Create a Discord bot:

   - Go to https://discord.com/developers/applications
   - Create a new application
   - Go to the "Bot" section and create a bot
   - Copy the bot token

4. Create a `.env` file:

   - Copy `.env.example` to `.env`
   - Replace `your_discord_bot_token_here` with your actual bot token

5. Invite the bot to your server:
   - Go to OAuth2 > URL Generator
   - Select "bot" under scopes
   - Select required permissions (at minimum: Send Messages, Connect, Speak)
   - Use the generated URL to invite the bot

## Usage

1. Join a voice channel in your Discord server
2. Use the command `w-chat` followed by your message:

```
w-chat xin chào
```

The bot will join your voice channel and respond with a voice message.

## Requirements

- Python 3.8 or higher
- FFmpeg
- Internet connection
- Discord account and server
