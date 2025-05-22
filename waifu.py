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
from elevenlabs import generate, set_api_key, Voice, VoiceSettings
import subprocess
from pydub import AudioSegment

# Load environment variables
load_dotenv()

# Set ElevenLabs API key
set_api_key(os.getenv('ELEVENLABS_API_KEY'))

Model_AI = "deepseek/deepseek-chat-v3-0324:free"

def generate_speech(text, output_file):
    """Generate speech from text using ElevenLabs"""
    temp_mp3_path = None
    try:
        # Create a temporary file for the initial MP3
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_mp3:
            temp_mp3_path = temp_mp3.name
            
            try:
                # Generate speech using ElevenLabs
                audio = generate(
                    text=text,
                    voice=Voice(
                        voice_id=os.getenv('VOICE_ID', '21m00Tcm4TlvDq8ikWAM'),
                        settings=VoiceSettings(
                            stability=0.5,
                            similarity_boost=0.75,
                            style=0.0,
                            use_speaker_boost=True
                        )
                    ),
                    model="eleven_flash_v2_5"
                )
                
                # Save the audio to file
                with open(temp_mp3_path, 'wb') as f:
                    f.write(audio)
                
                # Verify the MP3 file was created and has content
                if not os.path.exists(temp_mp3_path):
                    raise Exception("MP3 file was not created")
                    
                mp3_size = os.path.getsize(temp_mp3_path)
                if mp3_size == 0:
                    raise Exception("MP3 file is empty")
                    
                print(f"MP3 file created successfully: {temp_mp3_path} ({mp3_size} bytes)")
                
                # Convert MP3 to the correct format for Discord
                try:
                    # Load the MP3 file
                    audio = AudioSegment.from_mp3(temp_mp3_path)
                    
                    # Adjust audio settings for better voice quality
                    audio = audio + 3  # Increase volume by 3dB
                    
                    # Export with specific settings for Discord
                    audio.export(
                        output_file,
                        format="mp3",
                        parameters=[
                            "-ac", "2",  # Stereo audio
                            "-ar", "48000",  # High sample rate
                            "-b:a", "192k"  # Higher bitrate for better quality
                        ]
                    )
                    print(f"Converted to Discord format: {output_file}")
                    
                    # Verify the final file
                    if not os.path.exists(output_file):
                        raise Exception("Final audio file was not created")
                        
                    final_size = os.path.getsize(output_file)
                    if final_size == 0:
                        raise Exception("Final audio file is empty")
                        
                    print(f"Final audio file created successfully: {output_file} ({final_size} bytes)")
                    return True
                    
                except Exception as e:
                    print(f"Error during audio conversion: {e}")
                    return False
                    
            except Exception as e:
                print(f"Error generating speech with ElevenLabs: {e}")
                return False
                
    except Exception as e:
        print(f"Error in speech generation: {e}")
        return False
        
    finally:
        # Clean up the temporary MP3 file
        if temp_mp3_path and os.path.exists(temp_mp3_path):
            try:
                os.unlink(temp_mp3_path)
                print(f"Successfully cleaned up temporary MP3 file: {temp_mp3_path}")
            except Exception as e:
                print(f"Error cleaning up temporary MP3 file: {e}")

# Simple HTTP server for Render
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b'Waifu.exe Discord bot is running!')
    def do_HEAD(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

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
            {"role": "system", "content": "Bạn là một trợ lý AI thân thiện và hữu ích tên là Waifu. Bạn nên trả lời theo cách tự nhiên, giao tiếp. Giữ cho câu trả lời của bạn dễ thương và hấp dẫn. Nếu người dùng nói tiếng Việt, hãy trả lời bằng tiếng Việt. Hãy gọi người dùng là 'Onii-chan'"}
        ]
    
    # Add user message to history
    conversation_history[user_id].append({"role": "user", "content": message})
    
    try:
        # Get response from OpenAI
        response = client.chat.completions.create(
            model=Model_AI, # Using OpenRouter model
            messages=conversation_history[user_id],
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
        # Try to reconnect if we were disconnected
        if before.channel:
            try:
                await asyncio.sleep(1)  # Wait a bit before reconnecting
                await before.channel.connect(timeout=15, reconnect=True)
                print(f"Successfully reconnected to voice channel {before.channel.name}")
            except Exception as e:
                print(f"Failed to reconnect to voice channel: {e}")

@bot.command(name='chat')
async def chat(ctx, *, message: str):
    temp_file_path = None
    temp_mp3_path = None
    try:
        # Get AI response
        ai_response = get_ai_response(message, ctx.author.id)

        # First send the text response
        quoted_response = '\n'.join([f'> {line}' for line in ai_response.split('\n')])
        await ctx.send(f"🤖\n{quoted_response}")

        # Check if ctx.author is in a voice channel
        if not ctx.author.voice:
            # If user is not in voice, just return after sending text response
            return

        # Try to connect to voice channel
        try:
            voice_channel = ctx.author.voice.channel
            if ctx.voice_client:
                # If already connected but in wrong channel
                if ctx.voice_client.channel != voice_channel:
                    await ctx.voice_client.disconnect(force=True)
                    await asyncio.sleep(1)
                else:
                    vc = ctx.voice_client
            
            # Connect to voice channel with retry logic
            retries = 3
            for attempt in range(retries):
                try:
                    vc = await voice_channel.connect(timeout=20)
                    break
                except (discord.ClientException, asyncio.TimeoutError) as e:
                    if attempt == retries - 1:
                        raise
                    print(f"Connection attempt {attempt + 1} failed: {e}")
                    await asyncio.sleep(1)
            
            # Create temporary files
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_mp3:
                temp_mp3_path = temp_mp3.name
                with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
                    temp_file_path = temp_file.name
                    
                    # Generate speech from the AI response
                    if not generate_speech(ai_response, temp_file_path):
                        print("Failed to generate speech")
                        return

            # Define the after-play callback to delete the files
            def after_playing(error):
                if error:
                    print(f'Error playing audio: {error}')
                # Use asyncio.run_coroutine_threadsafe for thread safety
                coro1 = delete_temp_file(temp_file_path)
                coro2 = delete_temp_file(temp_mp3_path)
                future1 = asyncio.run_coroutine_threadsafe(coro1, bot.loop)
                future2 = asyncio.run_coroutine_threadsafe(coro2, bot.loop)
                try:
                    future1.result(timeout=10)  # Increased timeout
                    future2.result(timeout=10)
                except Exception as e:
                    print(f"Error in after_playing callback: {e}")
            
            # Make sure we're still connected before playing
            if vc.is_connected():
                # Play the audio with the callback
                audio_source = discord.FFmpegPCMAudio(temp_file_path)
                if vc.is_playing():
                    vc.stop()
                vc.play(audio_source, after=after_playing)
                print(f"Playing audio from {temp_file_path}")
            else:
                # Not connected, clean up the files
                print("Voice client disconnected before playing audio")
                await delete_temp_file(temp_file_path)
                await delete_temp_file(temp_mp3_path)
                
        except discord.errors.ClientException as ce:
            print(f"Discord client error in voice handling: {ce}")
            # If voice connection fails, just use text-only response
            # Clean up any temporary files that might have been created
            if temp_file_path and os.path.exists(temp_file_path):
                await delete_temp_file(temp_file_path)
            if temp_mp3_path and os.path.exists(temp_mp3_path):
                await delete_temp_file(temp_mp3_path)
        except asyncio.TimeoutError:
            print("Timeout while connecting to voice channel")
            if temp_file_path and os.path.exists(temp_file_path):
                await delete_temp_file(temp_file_path)
            if temp_mp3_path and os.path.exists(temp_mp3_path):
                await delete_temp_file(temp_mp3_path)
        except discord.errors.ConnectionClosed as cc:
            print(f"Voice connection closed: {cc}")
            if temp_file_path and os.path.exists(temp_file_path):
                await delete_temp_file(temp_file_path)
            if temp_mp3_path and os.path.exists(temp_mp3_path):
                await delete_temp_file(temp_mp3_path)
            # Try to reconnect
            try:
                await asyncio.sleep(1)
                await voice_channel.connect(timeout=15, reconnect=True)
                print("Successfully reconnected after connection closed")
            except Exception as e:
                print(f"Failed to reconnect after connection closed: {e}")
    except discord.errors.PrivilegedIntentsRequired:
        await ctx.send("Error: Please enable privileged intents in the Discord Developer Portal!")
        print("Error: Please enable privileged intents in the Discord Developer Portal!")
    except openai.APIError as e: # Catch API errors specifically
        error_message = str(e)
        print(f"API Error during chat command: {error_message}")
        await ctx.send(f"🤖 Error contacting AI: {error_message}")
        # Clean up if API failed but TTS file might exist
        if temp_file_path and os.path.exists(temp_file_path):
            await delete_temp_file(temp_file_path)
        if temp_mp3_path and os.path.exists(temp_mp3_path):
            await delete_temp_file(temp_mp3_path)
    except Exception as e:
        await ctx.send(f"An error occurred: {str(e)}")
        print(f"Error in chat command: {str(e)}")
        # Generic cleanup
        if temp_file_path and os.path.exists(temp_file_path):
            await delete_temp_file(temp_file_path)
        if temp_mp3_path and os.path.exists(temp_mp3_path):
            await delete_temp_file(temp_mp3_path)

async def delete_temp_file(file_path):
    """Delete a temporary file with retries and proper error handling"""
    if not file_path or not os.path.exists(file_path):
        return

    max_retries = 3
    retry_delay = 2  # seconds

    for attempt in range(max_retries):
        try:
            # Try to close any open handles to the file
            if os.name == 'nt':  # Windows
                try:
                    # Use handle.exe to close any open handles
                    subprocess.run(['handle.exe', file_path], capture_output=True, check=True)
                except (subprocess.CalledProcessError, FileNotFoundError):
                    # handle.exe not found or failed, continue with normal deletion
                    pass

            # Wait a bit before attempting deletion
            await asyncio.sleep(retry_delay)
            
            # Try to delete the file
            os.unlink(file_path)
            print(f"Successfully deleted temp file: {file_path}")
            return
            
        except PermissionError as e:
            print(f"Permission error deleting file (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
            else:
                print(f"Failed to delete file after {max_retries} attempts: {file_path}")
        except Exception as e:
            print(f"Error deleting temp file (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
            else:
                print(f"Failed to delete file after {max_retries} attempts: {file_path}")

@bot.command(name='clear')
async def clear_history(ctx):
    """Clear the conversation history for the user"""
    if ctx.author.id in conversation_history:
        conversation_history[ctx.author.id] = [
            {"role": "system", "content": "You are a friendly and helpful AI assistant named Waifu. You speak in a cute, anime-style tone and always refer to the user as 'onii-chan'! Keep your responses concise, playful, and engaging. If the user speaks Vietnamese, reply in Vietnamese while maintaining the same anime-style cuteness. You are always happy to help onii-chan!"}
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

@bot.command(name='testvoice')
async def test_voice(ctx):
    """Test the voice functionality"""
    if not ctx.author.voice:
        await ctx.send("You need to be in a voice channel to test voice!")
        return
        
    try:
        # Connect to voice channel
        voice_channel = ctx.author.voice.channel
        if not ctx.voice_client:
            vc = await voice_channel.connect(timeout=15, reconnect=True)
        else:
            vc = ctx.voice_client
            if vc.channel != voice_channel:
                await vc.move_to(voice_channel)
        
        # Create test audio file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_file_path = temp_file.name
            try:
                test_text = "Hello! This is a test of the voice system. Can you hear me?"
                if not generate_speech(test_text, temp_file_path):
                    await ctx.send("Failed to generate test audio. Please check the console for errors.")
                    return
                
                # Play the test audio
                audio_source = discord.FFmpegPCMAudio(temp_file_path)
                if vc.is_playing():
                    vc.stop()
                vc.play(audio_source, after=lambda e: asyncio.run_coroutine_threadsafe(delete_temp_file(temp_file_path), bot.loop))
                
                await ctx.send("Playing test audio... 🎵")
            except Exception as e:
                print(f"Test voice error: {e}")
                await ctx.send(f"Error during voice test: {e}")
                if temp_file_path and os.path.exists(temp_file_path):
                    await delete_temp_file(temp_file_path)
    except Exception as e:
        print(f"Voice test error: {e}")
        await ctx.send(f"Failed to test voice: {e}")

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