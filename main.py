import asyncio
import os
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import Message
from pytgcalls import PyTgCalls, idle
from pytgcalls.types import Update
from pytgcalls.types.input_stream import InputStream, InputAudioStream
from pytgcalls.exceptions import NoActiveGroupCall

# Replace these with your actual API details
API_ID = 24602058  # Replace with your API ID
API_HASH = "b976a44ccb8962b20113113f84aeebf6"  # Replace with your API Hash
BOT_TOKEN = "7548127733:AAEIJBaAVeYn9DPf41CfL-zze8yt7zuDXQI"  # Replace with your Bot Token
SESSION_STRING = "BQF3ZcoAsX0yc18HrzrBGcI8rNpM02CXtzn5YPHRhTs725h-OjM3KPGwv_yckjVNlFy7M6jT9u2NbAu1z2eOZzRMTg2FVPoBZ7LmPrCksegO3yK1irJjWh0f8yk3LlU1uGqRLC0ZlrJSGIzuqiF9vj7S_K8AU25Pw5IXaTuubXwPET65a6HfGtxmi6gbAQ-ayjiVcavTamd_Wc_QWS17Am4fQoLF_8fwP59sWcTY5PrXVdLfmke5xLODmxVHqBpoVkpccnxWDOskJwZXYFwoysclMcZ2V9xRiKlUpfVmgxUmSRX1GbCzHSBXCUUgBpZILJw576l7KOByjXyly1y-gVRvvrciggAAAAHWFal6AA"

# Create clients
app = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
user_client = Client("user", api_id=API_ID, api_hash=API_HASH, session_string=SESSION_STRING)

# Create PyTgCalls instance
pytgcalls = PyTgCalls(user_client)

@pytgcalls.on_stream_end()
async def on_stream_end(_, update: Update):
    chat_id = update.chat_id
    await pytgcalls.leave_group_call(chat_id)
    # Remove the audio file after the voice chat ends
    if hasattr(update, "audio_file_path") and os.path.exists(update.audio_file_path):
        os.remove(update.audio_file_path)

@app.on_message(filters.command("joinvc") & filters.group)
async def join_vc(client: Client, message: Message):
    chat_id = message.chat.id
    await user_client.join_chat(chat_id)
    await message.reply_text("Joined the voice chat", parse_mode=ParseMode.MARKDOWN)

@app.on_message(filters.command("play") & filters.group)
async def play_song(client: Client, message: Message):
    chat_id = message.chat.id

    if not message.reply_to_message or not message.reply_to_message.audio:
        await message.reply_text("Please reply to a valid .mp3 file with the /play command.", parse_mode=ParseMode.MARKDOWN)
        return

    audio = message.reply_to_message.audio
    file_path = await message.reply_to_message.download()

    try:
        await pytgcalls.join_group_call(
            chat_id,
            InputStream(
                InputAudioStream(
                    file_path,
                )
            )
        )
        await message.reply_text(f"Playing **{audio.file_name}** in the voice chat", parse_mode=ParseMode.MARKDOWN)
    except NoActiveGroupCall:
        await user_client.invoke(
            functions.phone.CreateGroupCall(
                peer=await user_client.resolve_peer(chat_id),
                random_id=0
            )
        )
        await pytgcalls.join_group_call(
            chat_id,
            InputStream(
                InputAudioStream(
                    file_path,
                )
            )
        )
        await message.reply_text(f"Playing **{audio.file_name}** in the voice chat", parse_mode=ParseMode.MARKDOWN)
    
    # Store the file path to remove it later
    update.audio_file_path = file_path

@app.on_message(filters.command("leavevc") & filters.group)
async def leave_vc(client: Client, message: Message):
    chat_id = message.chat.id
    await pytgcalls.leave_group_call(chat_id)
    await message.reply_text("Left the voice chat", parse_mode=ParseMode.MARKDOWN)

async def main():
    await app.start()
    await user_client.start()
    await pytgcalls.start()
    await idle()
    await app.stop()
    await user_client.stop()

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
