import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import select, delete
from src.database.db import get_session
from src.database.models import ReactionRole
from src.logger import logger

class Roles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="reaction_role", description="Setup a reaction role on a message.")
    @app_commands.checks.has_permissions(administrator=True)
    async def reaction_role(self, interaction: discord.Interaction, message_id: str, emoji: str, role: discord.Role):
        # We need the message object.
        # Since we only have ID, we might need to fetch it from the current channel or ask for channel too.
        # Simplest is to assume it's in the current channel or user provides link.
        # Let's try to fetch from current channel.

        try:
            msg_id = int(message_id)
            message = await interaction.channel.fetch_message(msg_id)
        except discord.NotFound:
            return await interaction.response.send_message("Message not found in this channel.", ephemeral=True)
        except ValueError:
            return await interaction.response.send_message("Invalid message ID.", ephemeral=True)

        # Add reaction to the message
        try:
            await message.add_reaction(emoji)
        except Exception as e:
            return await interaction.response.send_message(f"Failed to add reaction. Ensure I have permission and the emoji is valid. Error: {e}", ephemeral=True)

        # Save to DB
        async for session in get_session():
            rr = ReactionRole(
                guild_id=interaction.guild.id,
                message_id=msg_id,
                emoji=str(emoji),
                role_id=role.id
            )
            session.add(rr)
            await session.commit()

        await interaction.response.send_message(f"Reaction role set! Reacting with {emoji} gives {role.mention}.", ephemeral=True)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.member.bot:
            return

        async for session in get_session():
            stmt = select(ReactionRole).where(
                (ReactionRole.message_id == payload.message_id) &
                (ReactionRole.emoji == str(payload.emoji))
            )
            result = await session.execute(stmt)
            rr = result.scalar_one_or_none()

            if rr:
                guild = self.bot.get_guild(payload.guild_id)
                if guild:
                    role = guild.get_role(rr.role_id)
                    if role:
                        try:
                            await payload.member.add_roles(role)
                        except discord.Forbidden:
                            logger.warning(f"Missing permissions to add role {role.id} in guild {guild.id}")

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        async for session in get_session():
            stmt = select(ReactionRole).where(
                (ReactionRole.message_id == payload.message_id) &
                (ReactionRole.emoji == str(payload.emoji))
            )
            result = await session.execute(stmt)
            rr = result.scalar_one_or_none()

            if rr:
                guild = self.bot.get_guild(payload.guild_id)
                if guild:
                    member = guild.get_member(payload.user_id)
                    if member:
                        role = guild.get_role(rr.role_id)
                        if role:
                            try:
                                await member.remove_roles(role)
                            except discord.Forbidden:
                                logger.warning(f"Missing permissions to remove role {role.id} in guild {guild.id}")

async def setup(bot):
    await bot.add_cog(Roles(bot))
