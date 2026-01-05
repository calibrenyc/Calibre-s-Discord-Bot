import discord
from discord import app_commands
from discord.ext import commands
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from src.database.db import get_session
from src.database.models import UserProfile, UserHistory
from src.logger import logger
from datetime import datetime

class Tracking(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        async for session in get_session():
            # Upsert UserProfile
            # We use Postgres insert().on_conflict_do_update() for efficiency if possible,
            # but standard ORM way is also fine for low scale.

            stmt = select(UserProfile).where(
                (UserProfile.user_id == message.author.id) &
                (UserProfile.guild_id == message.guild.id)
            )
            result = await session.execute(stmt)
            profile = result.scalar_one_or_none()

            if not profile:
                profile = UserProfile(user_id=message.author.id, guild_id=message.guild.id, message_count=1)
                session.add(profile)
            else:
                profile.message_count += 1

            await session.commit()

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.bot:
            return

        # Check for nickname change
        if before.nick != after.nick:
            async for session in get_session():
                history = UserHistory(
                    user_id=after.id,
                    guild_id=after.guild.id,
                    change_type='NICKNAME',
                    old_value=before.nick,
                    new_value=after.nick,
                    timestamp=datetime.utcnow()
                )
                session.add(history)
                await session.commit()

        # Check for username change (if global update happens while in guild context?
        # Actually on_member_update covers guild-specific changes like nickname.
        # on_user_update covers global username changes, but we track per guild history usually)

        # If username changed (rarely captured in on_member_update unless we check user object)
        if before.name != after.name:
             async for session in get_session():
                history = UserHistory(
                    user_id=after.id,
                    guild_id=after.guild.id,
                    change_type='USERNAME',
                    old_value=before.name,
                    new_value=after.name,
                    timestamp=datetime.utcnow()
                )
                session.add(history)
                await session.commit()

    # Invite Tracking
    # We maintain a local cache of invites to compare against when a member joins

    def __init__(self, bot):
        self.bot = bot
        self._invites_cache = {}

    @commands.Cog.listener()
    async def on_ready(self):
        # Cache invites for all guilds on startup
        for guild in self.bot.guilds:
            try:
                self._invites_cache[guild.id] = await guild.invites()
            except:
                pass

    @commands.Cog.listener()
    async def on_invite_create(self, invite):
        # Update cache when new invite is created
        if invite.guild.id in self._invites_cache:
             self._invites_cache[invite.guild.id].append(invite)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        guild = member.guild
        if guild.id not in self._invites_cache:
            return

        old_invites = self._invites_cache[guild.id]
        try:
            new_invites = await guild.invites()
        except:
            return

        # Find which invite usage count incremented
        used_invite = None
        for new_inv in new_invites:
            for old_inv in old_invites:
                if new_inv.code == old_inv.code:
                    if new_inv.uses > old_inv.uses:
                        used_invite = new_inv
                        break
            if used_invite:
                break

        # Update cache
        self._invites_cache[guild.id] = new_invites

        if used_invite and used_invite.inviter:
             async for session in get_session():
                # Update inviter's stats
                stmt = select(UserProfile).where(
                    (UserProfile.user_id == used_invite.inviter.id) &
                    (UserProfile.guild_id == guild.id)
                )
                result = await session.execute(stmt)
                profile = result.scalar_one_or_none()

                if not profile:
                    profile = UserProfile(
                        user_id=used_invite.inviter.id,
                        guild_id=guild.id,
                        invites_count=1
                    )
                    session.add(profile)
                else:
                    profile.invites_count += 1

                await session.commit()
                logger.info(f" tracked invite for {member} by {used_invite.inviter}")

async def setup(bot):
    await bot.add_cog(Tracking(bot))
