import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from src.database.db import get_session
from src.database.models import GuildConfig
from src.logger import logger

class Setup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="setup", description="Interactively setup the bot channels and roles.")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_command(self, interaction: discord.Interaction,
                            mod_log_channel: discord.TextChannel = None,
                            ticket_category: discord.CategoryChannel = None,
                            staff_role: discord.Role = None):
        """
        Setup the bot for this server.
        Parameters:
        - mod_log_channel: Optional. Select an existing channel for logs.
        - ticket_category: Optional. Select an existing category for tickets.
        - staff_role: Optional. Role that can see tickets.
        """
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild

        # 1. Check/Create Mod Logs
        if mod_log_channel:
             created_mod_log = False
        else:
            mod_log_channel = discord.utils.get(guild.text_channels, name="mod-logs")
            if not mod_log_channel:
                try:
                    overwrites = {
                        guild.default_role: discord.PermissionOverwrite(read_messages=False),
                        guild.me: discord.PermissionOverwrite(read_messages=True)
                    }
                    mod_log_channel = await guild.create_text_channel("mod-logs", overwrites=overwrites)
                    created_mod_log = True
                except Exception as e:
                    return await interaction.followup.send(f"Failed to create mod-logs channel: {e}")
            else:
                created_mod_log = False

        # 2. Check/Create Tickets Category
        if ticket_category:
            created_ticket_cat = False
        else:
            ticket_category = discord.utils.get(guild.categories, name="Tickets")
            if not ticket_category:
                try:
                    ticket_category = await guild.create_category("Tickets")
                    created_ticket_cat = True
                except Exception as e:
                    return await interaction.followup.send(f"Failed to create Tickets category: {e}")
            else:
                created_ticket_cat = False

        # 3. Check/Create Bot Config Category (Optional, but good for organization)
        # 4. Save to DB

        async for session in get_session():
            stmt = select(GuildConfig).where(GuildConfig.guild_id == guild.id)
            result = await session.execute(stmt)
            config = result.scalar_one_or_none()

            if not config:
                config = GuildConfig(
                    guild_id=guild.id,
                    mod_log_channel_id=mod_log_channel.id,
                    ticket_category_id=ticket_category.id,
                    admin_role_id=staff_role.id if staff_role else None
                )
                session.add(config)
            else:
                config.mod_log_channel_id = mod_log_channel.id
                config.ticket_category_id = ticket_category.id
                if staff_role:
                    config.admin_role_id = staff_role.id

            await session.commit()

        response_msg = "Setup Complete!\n"
        response_msg += f"**Mod Log Channel:** {mod_log_channel.mention} ({'Created' if created_mod_log else 'Found'})\n"
        response_msg += f"**Tickets Category:** {ticket_category.name} ({'Created' if created_ticket_cat else 'Found'})\n"
        if staff_role:
            response_msg += f"**Staff Role:** {staff_role.mention}\n"
        response_msg += "\nYou can now use other commands."

        await interaction.followup.send(response_msg)

async def setup(bot):
    await bot.add_cog(Setup(bot))
