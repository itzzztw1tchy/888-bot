import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import os
import logging
import re
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ------------------- CONFIG -------------------
CONFIG = {
    "SPAM_MAX_AMOUNT": 500, # Lowered for safety
    "SPAM_DELAY": 1.4, # Base delay between messages
    "SPAM_COOLDOWN": 30, # Seconds cooldown per user on bspam
    "LOG_LEVEL": logging.INFO,
}

# ------------------- LOGGING -------------------
logging.basicConfig(
    level=CONFIG["LOG_LEVEL"],
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# ------------------- INTENTS -------------------
intents = discord.Intents.default()
intents.message_content = True # Only if you need to read message content

# ------------------- BOT CLASS -------------------
class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None # Disable default help
        )
        self.spam_tasks: dict[int, asyncio.Task] = {} # interaction.id -> task

    async def setup_hook(self):
        # Load cogs
        await self.load_extension("cogs.utility")
        await self.load_extension("cogs.invite")
        await self.load_extension("cogs.botinfo")

        # Fast sync for development guild (recommended during testing)
        if DEV_GUILD_ID := os.getenv("DEV_GUILD_ID"):
            try:
                guild = discord.Object(id=int(DEV_GUILD_ID))
                synced = await self.tree.sync(guild=guild)
                logger.info(f"Synced {len(synced)} commands to development guild.")
            except Exception as e:
                logger.warning(f"Dev guild sync failed: {e}")

        logger.info(f"{self.user} is ready! (ID: {self.user.id})")


bot = MyBot()


# ------------------- UTILITY COG -------------------
class UtilityCog(commands.Cog, name="Utility"):
    def __init__(self, bot: MyBot):
        self.bot = bot
        self._cd = commands.CooldownMapping.from_cooldown(
            1, CONFIG["SPAM_COOLDOWN"], commands.BucketType.user
        )

    @app_commands.command(name="bspam", description="Send a message multiple times (with cancel option)")
    @app_commands.describe(amount="Number of times to send (1-150)", content="Message content")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def bspam(self, interaction: discord.Interaction, amount: int, content: str):
        # Cooldown check
        bucket = self._cd.get_bucket(interaction)
        retry_after = bucket.update_rate_limit()
        if retry_after:
            return await interaction.response.send_message(
                f"⏳ You're on cooldown. Try again in {retry_after:.1f}s.",
                ephemeral=True
            )

        if amount < 1 or amount > CONFIG["SPAM_MAX_AMOUNT"]:
            return await interaction.response.send_message(
                f"Amount must be between 1 and {CONFIG['SPAM_MAX_AMOUNT']}.",
                ephemeral=True
            )

        if not content or not content.strip():
            return await interaction.response.send_message("Content cannot be empty.", ephemeral=True)

        channel = interaction.channel
        if not channel:
            return await interaction.response.send_message("Cannot access channel.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        view = SpamControlView(self.bot, interaction, channel, amount, content.strip())
        
        await interaction.followup.send(
            embed=discord.Embed(
                title="🚀 Spam Starting",
                description=f"Sending **{amount}** messages to {channel.mention if isinstance(channel, discord.TextChannel) else 'this channel'}.\n"
                            f"Click the button below to cancel.",
                color=discord.Color.orange()
            ),
            view=view,
            ephemeral=True
        )

        task = asyncio.create_task(view.run_spam())
        self.bot.spam_tasks[interaction.id] = task


class SpamControlView(discord.ui.View):
    def __init__(self, bot: MyBot, interaction: discord.Interaction, channel, amount: int, content: str):
        super().__init__(timeout=600) # 10 minutes
        self.bot = bot
        self.interaction = interaction
        self.channel = channel
        self.amount = amount
        self.content = content
        self.sent = 0
        self.cancelled = False

    async def run_spam(self):
        try:
            for _ in range(self.amount):
                if self.cancelled:
                    break

                try:
                    await self.channel.send(self.content)
                    self.sent += 1

                    # Dynamic delay with small jitter to look more natural
                    await asyncio.sleep(CONFIG["SPAM_DELAY"] + (self.sent % 5) * 0.05)

                except discord.Forbidden:
                    await self.interaction.followup.send("❌ Missing send permissions in this channel.", ephemeral=True)
                    break

                except discord.HTTPException as e:
                    if e.status == 429:
                        retry_after = float(e.response.headers.get("Retry-After", 3))
                        logger.warning(f"Rate limited during spam. Retrying after {retry_after}s")
                        await asyncio.sleep(retry_after + 1)
                        continue
                    await asyncio.sleep(2.0)

                except Exception as e:
                    logger.error(f"Unexpected error in spam: {e}")
                    await asyncio.sleep(2)

            status = "⏹️ Cancelled" if self.cancelled else "✅ Completed"
            embed = discord.Embed(
                title=status,
                description=f"Sent **{self.sent}/{self.amount}** messages.",
                color=discord.Color.red() if self.cancelled else discord.Color.green()
            )
            await self.interaction.followup.send(embed=embed, ephemeral=True)

        except Exception as e:
            logger.error(f"Spam task crashed: {e}")
        finally:
            self.bot.spam_tasks.pop(self.interaction.id, None)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, emoji="⏹️")
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.cancelled = True
        button.disabled = True
        await interaction.response.edit_message(view=self)
        await interaction.followup.send("⏹️ Spam has been cancelled.", ephemeral=True)


# ------------------- INVITE COG -------------------
class InviteCog(commands.Cog, name="Invite"):
    def __init__(self, bot: MyBot):
        self.bot = bot

    @app_commands.command(name="join", description="Validate a Discord invite link")
    @app_commands.describe(invite_link="Invite link or code")
    async def join(self, interaction: discord.Interaction, invite_link: str):
        match = re.search(r'(?:discord(?:app)?\.com/invite/|discord\.gg/)([a-zA-Z0-9-]+)', invite_link)
        if not match:
            return await interaction.response.send_message("❌ Invalid invite format.", ephemeral=True)

        code = match.group(1)
        try:
            invite = await self.bot.fetch_invite(code, with_counts=True)
            embed = discord.Embed(title="✅ Valid Invite", color=discord.Color.green())
            embed.add_field(name="Server", value=invite.guild.name, inline=True)
            embed.add_field(name="Members", value=f"{invite.approximate_member_count:,}", inline=True)
            embed.add_field(name="Link", value=invite.url, inline=False)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except discord.NotFound:
            await interaction.response.send_message("❌ Invite expired or invalid.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)


# ------------------- BOT INFO COG -------------------
class BotInfoCog(commands.Cog, name="Bot Info"):
    def __init__(self, bot: MyBot):
        self.bot = bot

    @app_commands.command(name="botinvite", description="Get the bot's invite link")
    async def botinvite(self, interaction: discord.Interaction):
        perms = discord.Permissions(
            send_messages=True,
            read_messages=True,
            embed_links=True,
            read_message_history=True,
            attach_files=True,
            external_emojis=True,
        )

        url = discord.utils.oauth_url(
            self.bot.user.id,
            permissions=perms,
            scopes=["bot", "applications.commands"]
        )

        embed = discord.Embed(
            title="Invite Me",
            description=f"[Click here to invite the bot]({url})",
            color=discord.Color.blurple()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


# ------------------- OWNER SYNC -------------------
@bot.tree.command(name="sync", description="Sync slash commands (Owner only)")
async def sync_commands(interaction: discord.Interaction):
    if not await bot.is_owner(interaction.user):
        return await interaction.response.send_message("❌ Owner-only command.", ephemeral=True)

    await interaction.response.defer(ephemeral=True)
    try:
        synced = await bot.tree.sync()
        await interaction.followup.send(f"✅ Synced **{len(synced)}** commands globally.", ephemeral=True)
        logger.info(f"Global sync performed by {interaction.user} — {len(synced)} commands.")
    except Exception as e:
        await interaction.followup.send(f"❌ Sync failed: {e}", ephemeral=True)
        logger.error(f"Global sync failed: {e}")


# ------------------- RUN -------------------
if __name__ == "__main__":
    token = os.getenv("TOKEN")
    if not token:
        logger.critical("TOKEN environment variable is missing!")
        exit(1)

    # Optional: Set DEV_GUILD_ID in .env for fast testing
    logger.info("Starting bot...")
    bot.run(token, log_handler=None) # We handle logging ourselves
mybot/
├── main.py (the code above)
├── .env
└── cogs/
    ├── __init__.py
    ├── utility.py
    ├── invite.py
    └── botinfo.py
