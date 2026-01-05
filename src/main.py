import discord
from discord.ext import commands
import os
import sys
from src.config import DISCORD_TOKEN, VERSION
from src.logger import logger
from src.database.db import init_db

class Bot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=commands.when_mentioned_or("!"),
            intents=discord.Intents.all(),
            help_command=None
        )
        self.version = VERSION

    async def setup_hook(self):
        """
        This is called when the bot starts, before it connects to the Gateway.
        We load extensions and initialize the DB here.
        """
        logger.info(f"Initializing Bot v{self.version}...")

        # Initialize Database
        try:
            await init_db()
            logger.info("Database connection established and tables checked.")
        except Exception as e:
            logger.critical(f"Failed to initialize database: {e}")
            # We might want to exit here if DB is critical, but for now let's log it.

        # Load Cogs
        for filename in os.listdir('./src/cogs'):
            if filename.endswith('.py'):
                try:
                    await self.load_extension(f'src.cogs.{filename[:-3]}')
                    logger.info(f"Loaded extension: {filename[:-3]}")
                except Exception as e:
                    logger.error(f"Failed to load extension {filename}: {e}")

        # Sync Slash Commands
        try:
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} command(s).")
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")

    async def on_ready(self):
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"Bot is running on v{self.version}")

        # Broadcast version to log channels
        from src.database.db import get_session
        from src.database.models import GuildConfig
        from sqlalchemy import select

        async for session in get_session():
            stmt = select(GuildConfig)
            result = await session.execute(stmt)
            configs = result.scalars().all()

            for config in configs:
                if config.mod_log_channel_id:
                    guild = self.get_guild(config.guild_id)
                    if guild:
                        channel = guild.get_channel(config.mod_log_channel_id)
                        if channel:
                            try:
                                await channel.send(f"🟢 **Bot Online**\nVersion: `{self.version}`")
                            except Exception:
                                pass

bot = Bot()

if __name__ == '__main__':
    if not DISCORD_TOKEN:
        logger.critical("DISCORD_TOKEN is not set in .env")
        sys.exit(1)

    try:
        bot.run(DISCORD_TOKEN)
    except Exception as e:
        logger.critical(f"Bot crashed: {e}")
