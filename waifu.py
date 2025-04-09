import os
import discord
from discord.ext import commands
import tempfile
from dotenv import load_dotenv
import openai
from openai import OpenAI
import time
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import pyttsx3
import subprocess

# Load environment variables
load_dotenv()

# Initialize text-to-speech engine
def init_tts():
    engine = pyttsx3.init()
    # Set voice properties
    voices = engine.getProperty('voices')
    # Try to find a female voice
    for voice in voices:
        if 'female' in voice.name.lower():
            engine.setProperty('voice', voice.id)
            break
    # Set speech rate
    engine.setProperty('rate', 150)  # Speed of speech
    return engine

# Simple HTTP server for Render
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b'Waifu.exe Discord bot is running!')

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server_address = ('', port)
    httpd = HTTPServer(server_address, SimpleHTTPRequestHandler)
    print(f"Starting web server on port {port}...")
    httpd.serve_forever()

# Start the web server in a separate thread
threading.Thread(target=run_web_server, daemon=True).start()

# Initialize OpenAI client with OpenRouter configuration
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv('OPENAI_API_KEY'),
    default_headers={
        "HTTP-Referer": "https://waifu-bot.onrender.com", # Update with your Render URL
        "X-Title": "Waifu.exe", # Your app name
    }
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
            model="openrouter/quasar-alpha", # Using OpenRouter model
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

@bot.event
async def on_voice_state_update(member, before, after):
    # Handle when the bot is disconnected from voice
    if member.id == bot.user.id and before.channel and not after.channel:
        print(f"Bot was disconnected from voice channel {before.channel.name}")

@bot.command(name='chat')
async def chat(ctx, *, message: str):
    temp_file_path = None
    try:
        # Get AI response
        ai_response = get_ai_response(message, ctx.author.id)

        # First send the text response
        await ctx.send(f"🤖 {ai_response}")

        # Check if ctx.author is in a voice channel
        if not ctx.author.voice:
            # If user is not in voice, just return after sending text response
            return

        # Try to connect to voice channel
        try:
            voice_channel = ctx.author.voice.channel
            if not ctx.voice_client:
                vc = await voice_channel.connect(timeout=15, reconnect=True)
            else:
                vc = ctx.voice_client
                # If voice client exists but is not connected
                if not vc.is_connected():
                    await vc.disconnect(force=True)
                    vc = await voice_channel.connect(timeout=15, reconnect=True)
                # Ensure the bot is in the same channel as the user
                elif vc.channel != voice_channel:
                    await vc.move_to(voice_channel)
            
            # Create a temporary file for the audio
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_file_path = temp_file.name
                # Generate speech from the AI response
                try:
                    # Initialize TTS engine
                    engine = init_tts()
                    # Save speech to file
                    engine.save_to_file(ai_response, temp_file_path)
                    engine.runAndWait()
                except Exception as tts_error:
                    print(f"TTS Error: {tts_error}")
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
                    future.result(timeout=5) # Wait for completion with timeout
                except Exception as e:
                    print(f"Error in after_playing callback: {e}")
            
            # Make sure we're still connected before playing
            if vc.is_connected():
                # Play the audio with the callback
                audio_source = discord.FFmpegPCMAudio(temp_file_path)
                if vc.is_playing():
                    vc.stop()
                vc.play(audio_source, after=after_playing)
            else:
                # Not connected, clean up the file
                print("Voice client disconnected before playing audio")
                await delete_temp_file(temp_file_path)
                
        except discord.errors.ClientException as ce:
            print(f"Discord client error in voice handling: {ce}")
            # If voice connection fails, just use text-only response
            # Clean up any temporary file that might have been created
            if temp_file_path and os.path.exists(temp_file_path):
                try: os.unlink(temp_file_path)
                except Exception: pass
        except asyncio.TimeoutError:
            print("Timeout while connecting to voice channel")
            if temp_file_path and os.path.exists(temp_file_path):
                try: os.unlink(temp_file_path)
                except Exception: pass
        except discord.errors.ConnectionClosed as cc:
            print(f"Voice connection closed: {cc}")
            if temp_file_path and os.path.exists(temp_file_path):
                try: os.unlink(temp_file_path)
                except Exception: pass
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

@bot.command(name='disconnect', aliases=['dc', 'leave'])
async def disconnect_voice(ctx):
    """Disconnect the bot from the voice channel"""
    if ctx.voice_client:
        await ctx.voice_client.disconnect(force=True)
        await ctx.send("Disconnected from voice channel! 👋")
    else:
        await ctx.send("I'm not connected to any voice channel!")

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