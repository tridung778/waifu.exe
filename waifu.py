import os
import discord
from discord.ext import commands
from gtts import gTTS
import tempfile
from dotenv import load_dotenv
import openai
from openai import OpenAI
import time
import asyncio

# Load environment variables
load_dotenv()

# Initialize OpenAI client with OpenRouter configuration
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv('OPENAI_API_KEY'),
    default_headers={
        "HTTP-Referer": "http://localhost", # Replace with your actual site URL or app name if deployed
        "X-Title": "Waifu.exe", # Replace with your app name
    },
)

# Bot setup with all intents
intents = discord.Intents.all()  # Enable all intents

bot = commands.Bot(command_prefix='w-', intents=intents)

# Store conversation history
conversation_history = {}

def get_ai_response(message, user_id):
    # Initialize conversation history for new users
    if user_id not in conversation_history:
        conversation_history[user_id] = [
            {"role": "system", "content": "You are a friendly and helpful AI assistant named Waifu. You should respond in a natural, conversational way. Keep your responses concise and engaging. If the user speaks Vietnamese, respond in Vietnamese."}
        ]
    
    # Add user message to history
    conversation_history[user_id].append({"role": "user", "content": message})
    
    try:
        # Get response from OpenAI
        response = client.chat.completions.create(
            model="openrouter/quasar-alpha",
            messages=conversation_history[user_id],
            max_tokens=150,
            temperature=0.7
        )
        
        # Get the response text
        ai_response = response.choices[0].message.content
        
        # Add AI response to history
        conversation_history[user_id].append({"role": "assistant", "content": ai_response})
        
        # Keep conversation history manageable (last 10 messages)
        if len(conversation_history[user_id]) > 11:  # 1 system message + 10 conversation messages
            conversation_history[user_id] = [conversation_history[user_id][0]] + conversation_history[user_id][-10:]
        
        return ai_response
    except openai.APIError as e:
        error_message = str(e)
        print(f"OpenAI API Error: {error_message}")
        
        if "insufficient_quota" in error_message:
            return "I'm sorry, but I've run out of credits. Please check your OpenAI account billing details."
        elif "rate_limit" in error_message:
            return "I'm receiving too many requests right now. Please try again in a moment."
        else:
            return "I'm having trouble connecting to my brain right now. Please check your OpenAI API key and try again."
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return "An unexpected error occurred. Please try again later."

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print('Make sure you have enabled the following in Discord Developer Portal:')
    print('1. MESSAGE CONTENT INTENT')
    print('2. SERVER MEMBERS INTENT')
    print('3. PRESENCE INTENT')

@bot.command(name='chat')
async def chat(ctx, *, message: str):
    temp_file_path = None
    try:
        # Get AI response
        ai_response = get_ai_response(message, ctx.author.id)

        # Check if ctx.author is still in a voice channel
        if not ctx.author.voice:
            await ctx.send("You need to be in a voice channel to use this command!")
            return

        # Connect to voice channel if not already connected
        voice_channel = ctx.author.voice.channel
        if not ctx.voice_client:
            vc = await voice_channel.connect()
        else:
            vc = ctx.voice_client
            # Ensure the bot is in the same channel as the user
            if vc.channel != voice_channel:
                await vc.move_to(voice_channel)
        
        # Create a temporary file for the audio
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
            temp_file_path = temp_file.name
            # Generate speech from the AI response
            try:
                tts = gTTS(text=ai_response, lang='ja')
                tts.save(temp_file_path)
            except Exception as tts_error:
                print(f"gTTS Error: {tts_error}")
                await ctx.send(f"🤖 {ai_response}\n*(Could not generate voice: {tts_error})*" )
                # Clean up if TTS failed
                if temp_file_path and os.path.exists(temp_file_path):
                    try: os.unlink(temp_file_path) 
                    except Exception: pass
                return # Stop processing if TTS fails

        # Define the after-play callback to delete the file
        def after_playing(error):
            if error:
                print(f'Error playing audio: {error}')
            # Use asyncio.run_coroutine_threadsafe for thread safety
            coro = delete_temp_file(temp_file_path)
            future = asyncio.run_coroutine_threadsafe(coro, bot.loop)
            try:
                future.result() # Wait for completion, optional
            except Exception as e:
                print(f"Error in after_playing callback: {e}")
        
        # Play the audio with the callback
        audio_source = discord.FFmpegPCMAudio(temp_file_path)
        vc.stop()
        vc.play(audio_source, after=after_playing)
        
        # Send text response as well
        await ctx.send(f"🤖 {ai_response}")
            
    except discord.errors.PrivilegedIntentsRequired:
        await ctx.send("Error: Please enable privileged intents in the Discord Developer Portal!")
        print("Error: Please enable privileged intents in the Discord Developer Portal!")
    except openai.APIError as e: # Catch API errors specifically
        error_message = str(e)
        print(f"API Error during chat command: {error_message}")
        await ctx.send(f"🤖 Error contacting AI: {error_message}")
        # Clean up if API failed but TTS file might exist
        if temp_file_path and os.path.exists(temp_file_path):
            try: os.unlink(temp_file_path)
            except Exception: pass
    except Exception as e:
        await ctx.send(f"An error occurred: {str(e)}")
        print(f"Error in chat command: {str(e)}")
        # Generic cleanup
        if temp_file_path and os.path.exists(temp_file_path):
            try: os.unlink(temp_file_path)
            except Exception: pass

# Separate async function for deletion to be called by the callback
async def delete_temp_file(file_path):
    try:
        # Add a small delay just in case
        await asyncio.sleep(1)
        if file_path and os.path.exists(file_path):
            os.unlink(file_path)
            # print(f"Successfully deleted temp file: {file_path}") # Optional debug print
    except Exception as e:
        print(f"Error deleting temp file in callback: {str(e)}")

@bot.command(name='clear')
async def clear_history(ctx):
    """Clear the conversation history for the user"""
    if ctx.author.id in conversation_history:
        conversation_history[ctx.author.id] = [
            {"role": "system", "content": "You are a friendly and helpful AI assistant named Waifu. You should respond in a natural, conversational way. Keep your responses concise and engaging. If the user speaks Vietnamese, respond in Vietnamese."}
        ]
        await ctx.send("Conversation history cleared! Let's start fresh! 😊")
    else:
        await ctx.send("No conversation history to clear!")

# Run the bot
token = os.getenv('DISCORD_TOKEN')
if not token:
    print("Error: DISCORD_TOKEN not found in .env file!")
    exit(1)

try:
    bot.run(token)
except discord.errors.LoginFailure:
    print("Error: Invalid token. Please check your DISCORD_TOKEN in .env file!")
except Exception as e:
    print(f"Error: {str(e)}") 