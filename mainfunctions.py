import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import os
import re

# Intents setup
intents = discord.Intents.default()
intents.message_content = True

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
    # Ignore messages sent by the bot itself
    if message.author == bot.user:
        return

    # Process text commands first
    await bot.process_commands(message)

    # Skip generic replies for command messages
    if message.content.startswith(bot.command_prefix):
        return

    # Respond to DMs
    if isinstance(message.channel, discord.DMChannel):
        await message.channel.send("Hey! I received your message. I'm a bot and may not monitor DMs actively, but I'm here!")
    # Respond to guild (server) messages
    else:
        await message.channel.send(f"Hello, {message.author.mention}! I see your message.")

# ------------------- BSPAM COMMANDS -------------------
async def _do_bspam(send_fn, amount: int, message: str):
    """Shared logic for bspam used by both slash and text commands."""
    if amount < 1:
        await send_fn("Amount must be at least 1.")
        return
    if amount > 50000:  # Hard limit to prevent abuse
        await send_fn("Maximum amount is 50K for safety.")
        return

    await send_fn(f"Starting spam of **{amount}** messages...")

    for i in range(amount):
        try:
            await send_fn(message)
            await asyncio.sleep(0.7)  # Delay to reduce rate limit risk
        except discord.Forbidden:
            await send_fn("I don't have permission to send messages here!")
            return
        except Exception as e:
            print(f"Error during spam: {e}")
            await send_fn(f"Stopped early due to error: {e}")
            return

    await send_fn(f"Finished spamming **{amount}** times!")

@tree.command(name="bspam", description="Spam a message a specified number of times.")
@app_commands.describe(amount="Number of times to send the message", message="The message to spam")
async def slash_bspam(interaction: discord.Interaction, amount: int, message: str):
    await interaction.response.defer()
    await _do_bspam(interaction.followup.send, amount, message)

@bot.command(name="bspam", help="Spam a message a specified number of times. Usage: !bspam <amount> <message>")
async def text_bspam(ctx: commands.Context, amount: int, *, message: str):
    await _do_bspam(ctx.send, amount, message)

# ------------------- JOIN COMMANDS -------------------
async def _do_join(send_fn, invite_link: str):
    """Shared logic for join used by both slash and text commands."""
    invite_code_match = re.search(r'(?:discord\.gg/|discord\.com/invite/)([a-zA-Z0-9]+)', invite_link)
    if not invite_code_match:
        await send_fn("Invalid invite link format. Please provide a valid Discord invite (e.g. https://discord.gg/abc123)")
        return

    code = invite_code_match.group(1)

    try:
        invite = await bot.fetch_invite(code)
        guild_name = invite.guild.name if invite.guild else "Unknown Server"

        await send_fn(
            f"✅ Valid invite found for server: **{guild_name}**\n\n"
            f"To add me to that server:\n"
            f"1. Open this link in your browser: {invite.url}\n"
            f"2. Make sure you have **Manage Server** permission.\n"
            f"3. Select the server and click **Authorize**.\n\n"
            f"If the link is expired or invalid, ask a server admin for a new one."
        )
    except discord.NotFound:
        await send_fn("❌ Invite not found or expired.")
    except discord.Forbidden:
        await send_fn("❌ I don't have permission to fetch invite details.")
    except Exception as e:
        await send_fn(f"❌ Error processing invite: {str(e)}")

@tree.command(name="join", description="Validate a Discord invite and get instructions to add the bot.")
@app_commands.describe(invite_link="The Discord invite link to validate")
async def slash_join(interaction: discord.Interaction, invite_link: str):
    await interaction.response.defer()
    await _do_join(interaction.followup.send, invite_link)

@bot.command(name="join", help="Validate a Discord invite and get instructions to add the bot. Usage: !join <invite_link>")
async def text_join(ctx: commands.Context, invite_link: str):
    await _do_join(ctx.send, invite_link)

# ------------------- BOTINVITE COMMANDS -------------------
async def _do_botinvite(send_fn):
    """Shared logic for botinvite used by both slash and text commands."""
    permissions = discord.Permissions(
        send_messages=True,
        read_messages=True,
        embed_links=True,
        attach_files=True,
    )
    invite_url = discord.utils.oauth_url(bot.user.id, permissions=permissions, scopes=["bot"])

    await send_fn(
        f"**Invite me to a server using this link:**\n{invite_url}\n\n"
        f"Make sure the person inviting has **Manage Server** permission!"
    )

@tree.command(name="botinvite", description="Get the link to invite this bot to a server.")
async def slash_botinvite(interaction: discord.Interaction):
    await interaction.response.defer()
    await _do_botinvite(interaction.followup.send)

@bot.command(name="botinvite", help="Get the link to invite this bot to a server. Usage: !botinvite")
async def text_botinvite(ctx: commands.Context):
    await _do_botinvite(ctx.send)

# ------------------- RUN THE BOT -------------------
if __name__ == "__main__":
    token = os.getenv("TOKEN")
    if not token:
        print("ERROR: No TOKEN found in Secrets!")
    else:
        bot.run(token)

