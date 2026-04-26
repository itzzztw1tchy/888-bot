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


# ------------------- 🔥 UNIVERSAL SEND WRAPPER -------------------
async def safe_send(interaction: discord.Interaction, channel, content: str):
    """
    Sends messages safely depending on context:
    - Servers → channel.send
    - DMs / GCs → interaction.followup.send fallback
    """

    if channel is None:
        await interaction.followup.send("No channel available.")
        return False

    # Server text channels
    if isinstance(channel, discord.TextChannel):
        try:
            await channel.send(content)
            return True
        except discord.Forbidden:
            await interaction.followup.send("❌ I can't send messages in this channel.")
            return False

    # DM / Group DM fallback
    else:
        try:
            await interaction.followup.send(content)
            return True
        except Exception:
            await interaction.followup.send("❌ Cannot send message here.")
            return False


# ------------------- /bspam -------------------
@tree.command(name="bspam", description="Spam a message a specified number of times")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def bspam(interaction: discord.Interaction, amount: int, message: str):

    if amount < 1:
        await interaction.response.send_message("Amount must be at least 1.")
        return

    if amount > 500:
        await interaction.response.send_message("Max is 500 for stability.")
        return

    await interaction.response.defer()
    await interaction.followup.send(f"Spamming {amount} messages...")

    channel = interaction.channel

    # ------------------- FIRST SEND -------------------
    ok = await safe_send(interaction, channel, message)
    if not ok:
        return

    # ------------------- LOOP (ONLY SAFE IN SERVERS) -------------------
    if isinstance(channel, discord.TextChannel):

        for i in range(amount - 1):
            try:
                await channel.send(message)
                await asyncio.sleep(1.5)

            except discord.Forbidden:
                await interaction.followup.send("❌ Stopped: missing permissions.")
                return

            except discord.HTTPException:
                await asyncio.sleep(3)

            except Exception as e:
                await interaction.followup.send(f"Stopped at {i}: {e}")
                return

    await safe_send(interaction, channel, "Done.")


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
