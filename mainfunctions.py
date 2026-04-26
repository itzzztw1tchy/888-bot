import discord
from discord import app_commands
import asyncio
import os
import re

# ------------------- INTENTS -------------------
intents = discord.Intents.default()
intents.message_content = True

# ------------------- BOT (KEEP ORIGINAL STYLE) -------------------
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)


# ------------------- EVENTS -------------------
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')

    # small delay prevents "0 commands" race condition on some hosts
    await asyncio.sleep(2)

    try:
        synced = await tree.sync()
        print(f'Synced {len(synced)} command(s) globally.')
    except Exception as e:
        print(f'Failed to sync commands: {e}')


# ------------------- /bspam -------------------
@tree.command(name="bspam", description="Spam a message a specified number of times")
async def bspam(interaction: discord.Interaction, amount: int, message: str):

    if amount < 1:
        await interaction.response.send_message("Amount must be at least 1.", ephemeral=True)
        return
    if amount > 50000:
        await interaction.response.send_message("Max is 50K.", ephemeral=True)
        return

    await interaction.response.send_message(f"Spamming {amount} messages...", ephemeral=True)

    for _ in range(amount):
        await interaction.channel.send(message)
        await asyncio.sleep(0.7)

    await interaction.followup.send("Done.", ephemeral=True)


# ------------------- /join -------------------
@tree.command(name="join", description="Validate invite link")
async def join(interaction: discord.Interaction, invite_link: str):

    match = re.search(r'(?:discord\.gg/|discord\.com/invite/)([a-zA-Z0-9]+)', invite_link)

    if not match:
        await interaction.response.send_message("Invalid invite.", ephemeral=True)
        return

    code = match.group(1)

    try:
        invite = await bot.fetch_invite(code)

        await interaction.response.send_message(
            f"Valid invite: {invite.url}",
            ephemeral=True
        )

    except Exception as e:
        await interaction.response.send_message(f"Error: {e}", ephemeral=True)


# ------------------- /botinvite -------------------
@tree.command(name="botinvite", description="Get bot invite link")
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

    await interaction.response.send_message(url, ephemeral=True)


# ------------------- RUN -------------------
token = os.getenv("TOKEN")

if not token:
    print("Missing TOKEN")
else:
    print("Starting bot...")
    bot.run(token)
