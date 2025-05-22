# Waifu.exe Discord Bot

A Discord AI bot that replies to your messages with both text and high-quality voice using ElevenLabs TTS and OpenAI/OpenRouter for chat. Supports Vietnamese and English, and is designed to be cute, friendly, and easy to use.

## Features

- AI chat with context memory (OpenAI/OpenRouter)
- High-quality voice replies using ElevenLabs TTS
- Supports Vietnamese and English (auto-detect)
- Replies in a quote block for easy reading
- Simple command interface
- Voice channel auto-join and auto-disconnect
- Conversation history per user (can be cleared)
- Test voice and disconnect commands

## Setup

1. **Install the required dependencies:**

```bash
pip install -r requirements.txt
```

2. **Install FFmpeg:**

   - Windows: Download from https://ffmpeg.org/download.html and add to PATH
   - Linux: `sudo apt-get install ffmpeg`
   - macOS: `brew install ffmpeg`

3. **Create a Discord bot:**

   - Go to https://discord.com/developers/applications
   - Create a new application
   - Go to the "Bot" section and create a bot
   - Copy the bot token

4. **Get API keys:**

   - [OpenAI/OpenRouter API key](https://openrouter.ai/)
   - [ElevenLabs API key](https://elevenlabs.io/)
   - (Optional) ElevenLabs Voice ID (default is provided)

5. **Create a `.env` file:**

   - Copy `.env.example` to `.env`
   - Fill in the following variables:
     - `DISCORD_TOKEN=your_discord_bot_token_here`
     - `OPENAI_API_KEY=your_openai_or_openrouter_api_key_here`
     - `ELEVENLABS_API_KEY=your_elevenlabs_api_key_here`
     - `VOICE_ID=your_elevenlabs_voice_id_here` (optional)

6. **Invite the bot to your server:**
   - Go to OAuth2 > URL Generator
   - Select "bot" under scopes
   - Select required permissions (at minimum: Send Messages, Connect, Speak)
   - Use the generated URL to invite the bot

## Usage

- **Join a voice channel** in your Discord server.
- Use the following commands:

### Main Commands

- `w-chat <message>`: Chat with the bot. The bot will reply in text (in a quote block) and join your voice channel to speak the reply.
- `w-clear`: Clear your conversation history with the bot.
- `w-disconnect`, `w-dc`, or `w-leave`: Disconnect the bot from the voice channel.
- `w-testvoice`: Test the bot's voice functionality in your current voice channel.

**Note:** The bot's text replies are displayed in a quote block with a colored bar on the left for better readability, similar to professional Discord bots.

## Requirements

- Python 3.8 or higher
- FFmpeg
- Discord account and server
- OpenAI/OpenRouter API key
- ElevenLabs API key

## Environment Variables (.env)

```
DISCORD_TOKEN=your_discord_bot_token_here
OPENAI_API_KEY=your_openai_or_openrouter_api_key_here
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
VOICE_ID=your_elevenlabs_voice_id_here  # Optional
```

## Notes

- The bot uses ElevenLabs for TTS, not Google TTS.
- All voice and text features are available in both English and Vietnamese.
- Make sure to enable the required intents in the Discord Developer Portal: MESSAGE CONTENT, SERVER MEMBERS, and PRESENCE.
- For deployment on Render or Docker, see `render.yaml` and `Dockerfile`.
