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
intents.dm_messages = True

# ------------------- BOT -------------------
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ------------------- EVENTS -------------------
@bot.event
async def on_ready():
    await tree.sync()
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print("Slash commands synced.")

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    # Always allow commands to work
    await bot.process_commands(message)

    # OPTIONAL: prevent spam in servers (recommended)
    if message.content.startswith(bot.command_prefix):
        return

    if isinstance(message.channel, discord.DMChannel):
        await message.channel.send(
            "Hey! I received your DM. I may not actively monitor messages, but I got it 👍"
        )
    else:
        await message.channel.send(
            f"Hello {message.author.mention}, I see your message!"
        )

# ------------------- BSPAM -------------------
async def _do_bspam(send_fn, amount: int, message: str):
    if amount < 1:
        await send_fn("Amount must be at least 1.")
        return
    if amount > 50000:
        await send_fn("Maximum amount is 50K for safety.")
        return

    await send_fn(f"Starting spam of **{amount}** messages...")

    for i in range(amount):
        try:
            await send_fn(message)
            await asyncio.sleep(0.7)
        except discord.Forbidden:
            await send_fn("No permission to send messages here!")
            return
        except Exception as e:
            await send_fn(f"Error: {e}")
            return

    await send_fn("Finished spam.")

@tree.command(name="bspam", description="Spam a message")
async def slash_bspam(interaction: discord.Interaction, amount: int, message: str):
    await interaction.response.defer()
    await _do_bspam(interaction.followup.send, amount, message)

@bot.command()
async def bspam(ctx, amount: int, *, message: str):
    await _do_bspam(ctx.send, amount, message)

# ------------------- JOIN -------------------
async def _do_join(send_fn, invite_link: str):
    match = re.search(r'(?:discord\.gg/|discord\.com/invite/)([a-zA-Z0-9]+)', invite_link)

    if not match:
        await send_fn("Invalid invite link.")
        return

    code = match.group(1)

    try:
        invite = await bot.fetch_invite(code)
        guild_name = invite.guild.name if invite.guild else "Unknown"

        await send_fn(
            f"Invite valid for: **{guild_name}**\n"
            f"{invite.url}"
        )

    except Exception as e:
        await send_fn(f"Error: {e}")

@tree.command(name="join")
async def slash_join(interaction: discord.Interaction, invite_link: str):
    await interaction.response.defer()
    await _do_join(interaction.followup.send, invite_link)

@bot.command()
async def join(ctx, invite_link: str):
    await _do_join(ctx.send, invite_link)

# ------------------- BOT INVITE -------------------
async def _do_botinvite(send_fn):
    perms = discord.Permissions(
        send_messages=True,
        read_messages=True,
        embed_links=True,
        attach_files=True,
    )

    url = discord.utils.oauth_url(bot.user.id, permissions=perms, scopes=["bot"])

    await send_fn(f"Invite me here:\n{url}")

@tree.command(name="botinvite")
async def slash_botinvite(interaction: discord.Interaction):
    await interaction.response.defer()
    await _do_botinvite(interaction.followup.send)

@bot.command()
async def botinvite(ctx):
    await _do_botinvite(ctx.send)

# ------------------- RUN -------------------
token = os.getenv("TOKEN")
if not token:
    print("Missing TOKEN")
else:
    bot.run(token)
