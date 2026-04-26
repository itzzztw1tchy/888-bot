import discord
from discord import app_commands
import asyncio
import os
import re

# Intents setup
intents = discord.Intents.default()
intents.message_content = True # If you need message content in the future

bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

# ------------------- EVENTS -------------------
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    try:
        synced = await tree.sync()
        print(f'Synced {len(synced)} command(s) globally.')
    except Exception as e:
        print(f'Failed to sync commands: {e}')

# ------------------- /bspam COMMAND -------------------
@tree.command(name="bspam", description="Spam a message a specified number of times (use responsibly!)")
@app_commands.describe(
    amount="Number of times to spam (1-100 recommended max)",
    message="The sentence/message to spam"
)
async def bspam(interaction: discord.Interaction, amount: int, message: str):
    if amount < 1:
        await interaction.response.send_message("Amount must be at least 1.", ephemeral=True)
        return
    if amount > 50000: # Hard limit to prevent abuse
        await interaction.response.send_message("Maximum amount is 50K for safety.", ephemeral=True)
        return

    await interaction.response.send_message(f"Starting spam of **{amount}** messages...", ephemeral=True)

    for i in range(amount):
        try:
            await interaction.channel.send(message)
            await asyncio.sleep(0.7) # Delay to reduce rate limit risk (adjust if needed)
        except discord.Forbidden:
            await interaction.followup.send("I don't have permission to send messages here!", ephemeral=True)
            return
        except Exception as e:
            print(f"Error during spam: {e}")
            await interaction.followup.send(f"Stopped early due to error: {e}", ephemeral=True)
            return

    await interaction.followup.send(f"Finished spamming **{amount}** times!", ephemeral=True)

# ------------------- /join COMMAND -------------------
@tree.command(name="join", description="Validate a Discord invite and get instructions to add the bot")
@app_commands.describe(invite_link="The full Discord invite link (e.g. https://discord.gg/abc123)")
async def join(interaction: discord.Interaction, invite_link: str):
    # Basic validation of invite format
    invite_code_match = re.search(r'(?:discord\.gg/|discord\.com/invite/)([a-zA-Z0-9]+)', invite_link)
    if not invite_code_match:
        await interaction.response.send_message("Invalid invite link format. Please provide a valid Discord invite (e.g. https://discord.gg/abc123)", ephemeral=True)
        return

    code = invite_code_match.group(1)

    try:
        # Try to fetch invite info
        invite = await bot.fetch_invite(code)
        guild_name = invite.guild.name if invite.guild else "Unknown Server"
        
        await interaction.response.send_message(
            f"✅ Valid invite found for server: **{guild_name}**\n\n"
            f"To add me to that server:\n"
            f"1. Open this link in your browser: {invite.url}\n"
            f"2. Make sure you have **Manage Server** permission.\n"
            f"3. Select the server and click **Authorize**.\n\n"
            f"If the link is expired or invalid, ask a server admin for a new one.",
            ephemeral=True
        )
    except discord.NotFound:
        await interaction.response.send_message("❌ Invite not found or expired.", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to fetch invite details.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error processing invite: {str(e)}", ephemeral=True)

# ------------------- OPTIONAL: Bot Invite Link Helper -------------------
@tree.command(name="botinvite", description="Get the link to invite this bot to a server")
async def botinvite(interaction: discord.Interaction):
    # Customize permissions here (add more as needed)
    permissions = discord.Permissions(
        send_messages=True,
        read_messages=True,
        embed_links=True,
        attach_files=True,
        # Add more if your bot needs them
    )
    invite_url = discord.utils.oauth_url(bot.user.id, permissions=permissions, scopes=["bot", "applications.commands"])
    
    await interaction.response.send_message(
        f"**Invite me to a server using this link:**\n{invite_url}\n\n"
        f"Make sure the person inviting has **Manage Server** permission!",
        ephemeral=True
    )

# ------------------- RUN THE BOT -------------------
if __name__ == "__main__":
    token = os.getenv("DISCORDTOKEN")
    if not token:
        print("ERROR: No TOKEN found in Secrets!")
    else:
        bot.run(token)
