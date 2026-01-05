import discord
from discord import app_commands
from discord.ext import commands
import os
import sys
import subprocess
from src.logger import logger

class System(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Check the bot's latency.")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"Pong! Latency: {round(self.bot.latency * 1000)}ms")

    @app_commands.command(name="update", description="Pull latest changes from git and restart.")
    @app_commands.checks.has_permissions(administrator=True)
    async def update(self, interaction: discord.Interaction):
        await interaction.response.send_message("Pulling latest changes from GitHub...", ephemeral=True)

        try:
            # Run git pull
            process = subprocess.run(["git", "pull"], capture_output=True, text=True)

            if process.returncode == 0:
                await interaction.followup.send(f"Git pull successful.\nOutput:\n```\n{process.stdout}\n```\nRestarting bot...")
                logger.info("Update command initiated. Restarting...")

                # Restart the bot process
                # This works if running via a wrapper or simple python script.
                # In Docker, the container might exit and restart if configured to do so (restart: always).
                os.execv(sys.executable, ['python'] + sys.argv)
            else:
                await interaction.followup.send(f"Git pull failed.\nError:\n```\n{process.stderr}\n```")
        except Exception as e:
            await interaction.followup.send(f"An error occurred during update: {str(e)}")
            logger.error(f"Update failed: {e}")

async def setup(bot):
    await bot.add_cog(System(bot))
