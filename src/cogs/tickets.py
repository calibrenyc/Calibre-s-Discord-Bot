import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Select, Button
from sqlalchemy import select
from src.database.db import get_session
from src.database.models import GuildConfig, Ticket
from src.logger import logger

class TicketSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Reporting", description="Report a user or issue", emoji="🛡️"),
            discord.SelectOption(label="Staff Applications", description="Apply for staff", emoji="📝"),
            discord.SelectOption(label="Applications", description="General applications", emoji="📋"),
            discord.SelectOption(label="Inquiries", description="General questions", emoji="❓"),
        ]
        super().__init__(placeholder="Select the ticket category...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        # Create the ticket channel
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        category_id = None

        staff_role_id = None
        async for session in get_session():
            stmt = select(GuildConfig).where(GuildConfig.guild_id == guild.id)
            result = await session.execute(stmt)
            config = result.scalar_one_or_none()
            if config:
                category_id = config.ticket_category_id
                staff_role_id = config.admin_role_id

        category = guild.get_channel(category_id) if category_id else None

        # Permission overwrites
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        # Add staff role overwrites
        if staff_role_id:
            staff_role = guild.get_role(staff_role_id)
            if staff_role:
                 overwrites[staff_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        ticket_type = self.values[0]
        channel_name = f"{ticket_type.lower().replace(' ', '-')}-{interaction.user.name}"

        try:
            channel = await guild.create_text_channel(name=channel_name, category=category, overwrites=overwrites)
        except Exception as e:
            return await interaction.followup.send(f"Failed to create ticket channel: {e}", ephemeral=True)

        # Save to DB
        async for session in get_session():
            ticket = Ticket(
                guild_id=guild.id,
                channel_id=channel.id,
                owner_id=interaction.user.id,
                ticket_type=ticket_type,
                status='OPEN'
            )
            session.add(ticket)
            await session.commit()

        # Send welcome message
        embed = discord.Embed(
            title=f"{ticket_type} Ticket",
            description=f"Welcome {interaction.user.mention}. Staff will be with you shortly.",
            color=discord.Color.green()
        )
        await channel.send(embed=embed, view=TicketControlView())

        await interaction.followup.send(f"Ticket created: {channel.mention}", ephemeral=True)

class TicketControlView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.red, custom_id="ticket_close_btn")
    async def close_ticket(self, interaction: discord.Interaction, button: Button):
        # We could add a confirmation or just close/delete
        # Let's verify it's a ticket channel via DB
        async for session in get_session():
            stmt = select(Ticket).where(Ticket.channel_id == interaction.channel.id)
            result = await session.execute(stmt)
            ticket = result.scalar_one_or_none()

            if ticket:
                ticket.status = 'CLOSED'
                ticket.closed_at = datetime.utcnow()
                await session.commit()

                await interaction.response.send_message("Ticket closing in 5 seconds...")
                await discord.utils.sleep_until(discord.utils.utcnow() + timedelta(seconds=5))
                await interaction.channel.delete()
            else:
                await interaction.response.send_message("This does not appear to be a tracked ticket channel.", ephemeral=True)

from datetime import datetime, timedelta

class TicketLauncherView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())

class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ticket_panel", description="Send the ticket creation panel.")
    @app_commands.checks.has_permissions(administrator=True)
    async def ticket_panel(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="Open a Ticket",
            description="Select a category below to open a ticket.",
            color=discord.Color.blue()
        )
        await interaction.channel.send(embed=embed, view=TicketLauncherView())
        await interaction.response.send_message("Panel sent!", ephemeral=True)

    # Re-register views on startup for persistence
    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(TicketLauncherView())
        self.bot.add_view(TicketControlView())

async def setup(bot):
    await bot.add_cog(Tickets(bot))
