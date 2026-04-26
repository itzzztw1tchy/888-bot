import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import os
import re

# ------------------- INTENTS -------------------
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guilds = True

# ------------------- BOT -------------------
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree


# ------------------- EVENTS -------------------
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')

    # 1. FAST SYNC (for testing in server)
    try:
        guild = discord.Object(id=GUILD_ID)
        synced = await tree.sync(guild=guild)
        print(f"Guild sync complete: {len(synced)} commands")
    except Exception as e:
        print(f"Guild sync failed: {e}")

    # 2. GLOBAL SYNC (for DMs / long-term rollout)
    try:
        synced_global = await tree.sync()
        print(f"Global sync complete: {len(synced_global)} commands")
    except Exception as e:
        print(f"Global sync failed: {e}")

import os
import traceback

token = os.getenv("TOKEN")

if not token:
    print("❌ Missing TOKEN environment variable")
else:
    try:
        print("🚀 Starting bot...")
        bot.run(token)
    except Exception:
        print("🔥 Bot crashed on startup:")
        traceback.print_exc()
