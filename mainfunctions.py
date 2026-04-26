import discord
from discord.ext import commands
import asyncio
import os
import re

# Intents setup
intents = discord.Intents.default()
intents.message_content = True # If you need message content in the future

bot = commands.Bot(command_prefix="!", intents=intents)

# ------------------- EVENTS -------------------
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')

@bot.event
async def on_message(message: discord.Message):
    # Ignore messages sent by the bot itself
    if message.author == bot.user:
        return

    # Process text commands first
    await bot.process_commands(message)

    # Only respond to non-command messages
    if message.content.startswith(bot.command_prefix):
        return

    # Respond to DMs
    if isinstance(message.channel, discord.DMChannel):
        await message.channel.send(f"Hey! I received your message. I'm a bot and may not monitor DMs actively, but I'm here!")
    # Respond to guild (server) messages
    else:
        await message.channel.send(f"Hello, {message.author.mention}! I see your message.")

# ------------------- !bspam COMMAND -------------------
@bot.command(name="bspam", help="Spam a message a specified number of times. Usage: !bspam <amount> <message>")
async def bspam(ctx: commands.Context, amount: int, *, message: str):
    if amount < 1:
        await ctx.send("Amount must be at least 1.")
        return
    if amount > 50000: # Hard limit to prevent abuse
        await ctx.send("Maximum amount is 50K for safety.")
        return

    await ctx.send(f"Starting spam of **{amount}** messages...")

    for i in range(amount):
        try:
            await ctx.send(message)
            await asyncio.sleep(0.7) # Delay to reduce rate limit risk (adjust if needed)
        except discord.Forbidden:
            await ctx.send("I don't have permission to send messages here!")
            return
        except Exception as e:
            print(f"Error during spam: {e}")
            await ctx.send(f"Stopped early due to error: {e}")
            return

    await ctx.send(f"Finished spamming **{amount}** times!")

# ------------------- !join COMMAND -------------------
@bot.command(name="join", help="Validate a Discord invite and get instructions to add the bot. Usage: !join <invite_link>")
async def join(ctx: commands.Context, invite_link: str):
    # Basic validation of invite format
    invite_code_match = re.search(r'(?:discord\.gg/|discord\.com/invite/)([a-zA-Z0-9]+)', invite_link)
    if not invite_code_match:
        await ctx.send("Invalid invite link format. Please provide a valid Discord invite (e.g. https://discord.gg/abc123)")
        return

    code = invite_code_match.group(1)

    try:
        # Try to fetch invite info
        invite = await bot.fetch_invite(code)
        guild_name = invite.guild.name if invite.guild else "Unknown Server"

        await ctx.send(
            f"✅ Valid invite found for server: **{guild_name}**\n\n"
            f"To add me to that server:\n"
            f"1. Open this link in your browser: {invite.url}\n"
            f"2. Make sure you have **Manage Server** permission.\n"
            f"3. Select the server and click **Authorize**.\n\n"
            f"If the link is expired or invalid, ask a server admin for a new one."
        )
    except discord.NotFound:
        await ctx.send("❌ Invite not found or expired.")
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to fetch invite details.")
    except Exception as e:
        await ctx.send(f"❌ Error processing invite: {str(e)}")

# ------------------- !botinvite COMMAND -------------------
@bot.command(name="botinvite", help="Get the link to invite this bot to a server. Usage: !botinvite")
async def botinvite(ctx: commands.Context):
    # Customize permissions here (add more as needed)
    permissions = discord.Permissions(
        send_messages=True,
        read_messages=True,
        embed_links=True,
        attach_files=True,
        # Add more if your bot needs them
    )
    invite_url = discord.utils.oauth_url(bot.user.id, permissions=permissions, scopes=["bot"])

    await ctx.send(
        f"**Invite me to a server using this link:**\n{invite_url}\n\n"
        f"Make sure the person inviting has **Manage Server** permission!"
    )

# ------------------- RUN THE BOT -------------------
if __name__ == "__main__":
    token = os.getenv("TOKEN")
    if not token:
        print("ERROR: No TOKEN found in Secrets!")
    else:
        bot.run(token)
