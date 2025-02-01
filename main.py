import asyncio
import os
import subprocess
import logging
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import Message
from pytgcalls import PyTgCalls, idle
from pytgcalls.types import Update
from pytgcalls.types.input_stream import AudioPiped
from pytgcalls.exceptions import NoActiveGroupCall

# Replace these with your actual API details
API_ID = 24602058  # Replace with your API ID
API_HASH = "b976a44ccb8962b20113113f84aeebf6"  # Replace with your API Hash
BOT_TOKEN = "7548127733:AAGBfpSBajzoy0VS1fLJD0OX1d3X037tC8k"  # Replace with your Bot Token
SESSION_STRING = "BQF3ZcoAsX0yc18HrzrBGcI8rNpM02CXtzn5YPHRhTs725h-OjM3KPGwv_yckjVNlFy7M6jT9u2NbAu1z2eOZzRMTg2FVPoBZ7LmPrCksegO3yK1irJjWh0f8yk3LlU1uGqRLC0ZlrJSGIzuqiF9vj7S_K8AU25Pw5IXaTuubXwPET65a6HfGtxmi6gbAQ-ayjiVcavTamd_Wc_QWS17Am4fQoLF_8fwP59sWcTY5PrXVdLfmke5xLODmxVHqBpoVkpccnxWDOskJwZXYFwoysclMcZ2V9xRiKlUpfVmgxUmSRX1GbCzHSBXCUUgBpZILJw576l7KOByjXyly1y-gVRvvrciggAAAAHWFal6AA"

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create clients
app = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
user_client = Client("user", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

# Create PyTgCalls instance
pytgcalls = PyTgCalls(user_client)

# Dictionary to store file paths for each chat
file_paths = {}

@pytgcalls.on_stream_end()
async def on_stream_end(_, update: Update):
    chat_id = update.chat_id
    await pytgcalls.leave_group_call(chat_id)
    # Remove the audio file after the voice chat ends
    if chat_id in file_paths and os.path.exists(file_paths[chat_id]):
        os.remove(file_paths[chat_id])
        del file_paths[chat_id]
        logger.info(f"Removed audio file for chat {chat_id}")

@app.on_message(filters.command("joinvc") & filters.group)
async def join_vc(client: Client, message: Message):
    chat_id = message.chat.id
    await user_client.join_chat(chat_id)
    await message.reply_text("Joined the voice chat", parse_mode=ParseMode.MARKDOWN)
    logger.info(f"Joined voice chat in group {chat_id}")

@app.on_message(filters.command("play") & filters.group)
async def play_song(client: Client, message: Message):
    chat_id = message.chat.id

    if not message.reply_to_message or not (message.reply_to_message.audio or message.reply_to_message.document):
        await message.reply_text("Please reply to a valid .mp3 or .m4a file with the /play command.", parse_mode=ParseMode.MARKDOWN)
        return

    # Check if the file is an audio file (mp3 or m4a)
    if message.reply_to_message.audio:
        audio = message.reply_to_message.audio
    elif message.reply_to_message.document and (message.reply_to_message.document.file_name.endswith('.mp3') or message.reply_to_message.document.file_name.endswith('.m4a')):
        audio = message.reply_to_message.document
    else:
        await message.reply_text("Please reply to a valid .mp3 or .m4a file with the /play command.", parse_mode=ParseMode.MARKDOWN)
        return

    file_path = await message.reply_to_message.download()
    logger.info(f"Downloaded audio file for chat {chat_id}: {file_path}")

    # Create a named pipe
    pipe_path = f'/tmp/{chat_id}.pipe'
    if not os.path.exists(pipe_path):
        os.mkfifo(pipe_path)

    # Use FFmpeg to stream the audio file without modifying it
    ffmpeg_command = [
        'ffmpeg',
        '-i', file_path,  # Input file
        '-f', 's16le',  # Output format
        '-ac', '2',  # Number of audio channels
        '-ar', '48000',  # Audio sample rate
        pipe_path  # Output to named pipe
    ]

    process = subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    try:
        await pytgcalls.join_group_call(
            chat_id,
            AudioPiped(
                pipe_path,
            )
        )
        await message.reply_text(f"Playing **{audio.file_name}** in the voice chat", parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Started playing audio in chat {chat_id}")
    except NoActiveGroupCall:
        await user_client.invoke(
            functions.phone.CreateGroupCall(
                peer=await user_client.resolve_peer(chat_id),
                random_id=0
            )
        )
        await pytgcalls.join_group_call(
            chat_id,
            AudioPiped(
                pipe_path,
            )
        )
        await message.reply_text(f"Playing **{audio.file_name}** in the voice chat", parse_mode=ParseMode.MARKDOWN)
        logger.info(f"Started and joined new group call in chat {chat_id}")

    # Store the file path to remove it later
    file_paths[chat_id] = file_path

@app.on_message(filters.command("leavevc") & filters.group)
async def leave_vc(client: Client, message: Message):
    chat_id = message.chat.id
    await pytgcalls.leave_group_call(chat_id)
    await message.reply_text("Left the voice chat", parse_mode=ParseMode.MARKDOWN)
    logger.info(f"Left voice chat in group {chat_id}")
    # Remove the audio file after leaving the voice chat
    if chat_id in file_paths and os.path.exists(file_paths[chat_id]):
        os.remove(file_paths[chat_id])
        del file_paths[chat_id]
        logger.info(f"Removed audio file for chat {chat_id}")

async def main():
    await app.start()
    await user_client.start()
    await pytgcalls.start()
    await idle()
    await app.stop()
    await user_client.stop()

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
