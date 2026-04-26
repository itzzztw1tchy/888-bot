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
    if channel is None:
        await interaction.followup.send("No channel available.")
        return False

    if isinstance(channel, discord.TextChannel):
        try:
            await channel.send(content)
            return True
        except discord.Forbidden:
            await interaction.followup.send(" ")
            return False
    else:
        try:
            await interaction.followup.send(content)
            return True
        except Exception:
            await interaction.followup.send("❌ Cannot send message here.")
            return False


# ------------------- /bspam (FIXED VERSION) -------------------
@tree.command(name="bspam", description="Send a message multiple times (context-safe)")
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def bspam(interaction: discord.Interaction, amount: int, message: str):

    if amount < 1:
        await interaction.response.send_message("Amount must be at least 1.", ephemeral=True)
        return

    if amount > 900:
        await interaction.response.send_message("Max is 900 for stability.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    await interaction.followup.send(
        f"Processing {amount} messages...",
        ephemeral=True
    )

    channel = interaction.channel

    if channel is None:
        await interaction.followup.send("No channel available.", ephemeral=True)
        return

    # ------------------- SERVER MODE -------------------
    if isinstance(channel, discord.TextChannel):
        for i in range(amount):
            try:
                await interaction.followup.send(message)
                await asyncio.sleep(1.2)

            except discord.Forbidden:
                await interaction.followup.send(
                    "❌ No permission to send messages here.",
                    ephemeral=True
                )
                return

            except discord.HTTPException:
                await asyncio.sleep(2)

    # ------------------- DM / GC MODE -------------------
    else:
        for i in range(amount):
            try:
               await interaction.followup.send(message)
               await asyncio.sleep(1.2)

            except discord.HTTPException:
                await asyncio.sleep(2)

    await interaction.followup.send("Done.", ephemeral=True)

    # ------------------- MAIN LOOP (FIXED LOGIC) -------------------

    try:
        for i in range(amount):
            await channel.send(message)
            await asyncio.sleep(1.2)

    except discord.Forbidden:
        await interaction.followup.send(
            "❌ I don't have permission to send messages here.",
            ephemeral=True
        )
        return

    except discord.HTTPException:
        await interaction.followup.send(
            "❌ Rate limited or blocked by Discord.",
            ephemeral=True
        )
        return

    except Exception as e:
        await interaction.followup.send(
            f"Stopped early: {e}",
            ephemeral=True
        )
        return

    await interaction.followup.send("Done.", ephemeral=True)


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
