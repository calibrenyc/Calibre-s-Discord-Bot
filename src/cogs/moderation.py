import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import select
from src.database.db import get_session
from src.database.models import GuildConfig, Warning as WarningModel, UserProfile
from src.logger import logger
from datetime import datetime, timedelta

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def log_action(self, guild, message_content):
        """Helper to log actions to the configured mod-log channel."""
        async for session in get_session():
            stmt = select(GuildConfig).where(GuildConfig.guild_id == guild.id)
            result = await session.execute(stmt)
            config = result.scalar_one_or_none()

            if config and config.mod_log_channel_id:
                channel = guild.get_channel(config.mod_log_channel_id)
                if channel:
                    await channel.send(message_content)

    @app_commands.command(name="kick", description="Kick a user from the server.")
    @app_commands.checks.has_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        await member.kick(reason=reason)
        await interaction.response.send_message(f"Kicked {member.mention}. Reason: {reason}")
        await self.log_action(interaction.guild, f"**KICK**: {interaction.user.mention} kicked {member.mention} (ID: {member.id})\nReason: {reason}")

    @app_commands.command(name="ban", description="Ban a user from the server.")
    @app_commands.checks.has_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        await member.ban(reason=reason)
        await interaction.response.send_message(f"Banned {member.mention}. Reason: {reason}")
        await self.log_action(interaction.guild, f"**BAN**: {interaction.user.mention} banned {member.mention} (ID: {member.id})\nReason: {reason}")

    @app_commands.command(name="timeout", description="Timeout a user.")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def timeout(self, interaction: discord.Interaction, member: discord.Member, minutes: int, reason: str = "No reason provided"):
        duration = timedelta(minutes=minutes)
        await member.timeout(duration, reason=reason)
        await interaction.response.send_message(f"Timed out {member.mention} for {minutes} minutes. Reason: {reason}")
        await self.log_action(interaction.guild, f"**TIMEOUT**: {interaction.user.mention} timed out {member.mention} (ID: {member.id}) for {minutes}m\nReason: {reason}")

    @app_commands.command(name="purge", description="Delete a number of messages.")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def purge(self, interaction: discord.Interaction, amount: int):
        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(f"Deleted {len(deleted)} messages.", ephemeral=True)
        await self.log_action(interaction.guild, f"**PURGE**: {interaction.user.mention} deleted {len(deleted)} messages in {interaction.channel.mention}")

    @app_commands.command(name="warn", description="Warn a user.")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        async for session in get_session():
            # Ensure profile exists
            stmt = select(UserProfile).where((UserProfile.user_id == member.id) & (UserProfile.guild_id == interaction.guild.id))
            result = await session.execute(stmt)
            profile = result.scalar_one_or_none()

            if not profile:
                profile = UserProfile(user_id=member.id, guild_id=interaction.guild.id)
                session.add(profile)

            # Create warning
            warning = WarningModel(
                user_id=member.id,
                guild_id=interaction.guild.id,
                moderator_id=interaction.user.id,
                reason=reason
            )
            session.add(warning)
            await session.commit()

        await interaction.response.send_message(f"Warned {member.mention}. Reason: {reason}")
        try:
            await member.send(f"You have been warned in **{interaction.guild.name}**. Reason: {reason}")
        except:
            pass
        await self.log_action(interaction.guild, f"**WARN**: {interaction.user.mention} warned {member.mention} (ID: {member.id})\nReason: {reason}")

    @app_commands.command(name="warnings", description="View warnings for a user.")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def warnings(self, interaction: discord.Interaction, member: discord.Member):
        async for session in get_session():
            stmt = select(WarningModel).where(
                (WarningModel.user_id == member.id) &
                (WarningModel.guild_id == interaction.guild.id)
            ).order_by(WarningModel.timestamp.desc())
            result = await session.execute(stmt)
            warnings = result.scalars().all()

        if not warnings:
            return await interaction.response.send_message(f"{member.mention} has no warnings.")

        embed = discord.Embed(title=f"Warnings for {member.display_name}", color=discord.Color.orange())
        for w in warnings:
            embed.add_field(
                name=f"ID: {w.id} | {w.timestamp.strftime('%Y-%m-%d')}",
                value=f"**Reason:** {w.reason}\n**Mod:** <@{w.moderator_id}>",
                inline=False
            )

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Moderation(bot))
