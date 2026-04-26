import discord
from discord import app_commands
import asyncio
import os
import re

# ------------------- INTENTS -------------------
intents = discord.Intents.default()
intents.message_content = True

# ------------------- BOT -------------------
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)


# ------------------- EVENTS -------------------
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')

    await asyncio.sleep(2)

    try:
        synced = await tree.sync()
        print(f'Synced {len(synced)} command(s) globally.')
    except Exception as e:
        print(f'Failed to sync commands: {e}')


# ------------------- /bspam -------------------
@tree.command(name="bspam", description="Spam a message a specified number of times")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def bspam(interaction: discord.Interaction, amount: int, message: str):

    if amount < 1:
        await interaction.response.send_message("Amount must be at least 1.")
        return

    if amount > 50000:
        await interaction.response.send_message("Max is 50K.")
        return

    # initial response (visible in chat)
    await interaction.response.send_message(f"Starting spam of {amount} messages...")

    for _ in range(amount):
        await interaction.channel.send(message)
        await asyncio.sleep(0.7)

    await interaction.channel.send("Done.")


# ------------------- /join -------------------
@tree.command(name="join", description="Validate invite link")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def join(interaction: discord.Interaction, invite_link: str):

    match = re.search(r'(?:discord\.gg/|discord\.com/invite/)([a-zA-Z0-9]+)', invite_link)

    if not match:
        await interaction.response.send_message("Invalid invite.")
        return

    code = match.group(1)

    try:
        invite = await bot.fetch_invite(code)

        await interaction.response.send_message(
            f"Valid invite: {invite.url}"
        )

    except Exception as e:
        await interaction.response.send_message(f"Error: {e}")


# ------------------- /botinvite -------------------
@tree.command(name="botinvite", description="Get bot invite link")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def botinvite(interaction: discord.Interaction):

    perms = discord.Permissions(
        send_messages=True,
        read_messages=True,
        embed_links=True
    )

    url = discord.utils.oauth_url(
        bot.user.id,
        permissions=perms,
        scopes=["bot", "applications.commands"]
    )

    await interaction.response.send_message(url)


# ------------------- RUN -------------------
token = os.getenv("TOKEN")

if not token:
    print("Missing TOKEN")
else:
    print("Starting bot...")
    bot.run(token)
