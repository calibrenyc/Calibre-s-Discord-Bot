from sqlalchemy import Column, Integer, String, BigInteger, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from src.database.db import Base

class GuildConfig(Base):
    __tablename__ = 'guild_config'

    guild_id = Column(BigInteger, primary_key=True)
    mod_log_channel_id = Column(BigInteger, nullable=True)
    ticket_category_id = Column(BigInteger, nullable=True)
    welcome_channel_id = Column(BigInteger, nullable=True)
    admin_role_id = Column(BigInteger, nullable=True) # For ticket access, etc.

class UserProfile(Base):
    __tablename__ = 'user_profiles'

    user_id = Column(BigInteger, primary_key=True)
    guild_id = Column(BigInteger, primary_key=True) # Users might have different stats per server
    message_count = Column(Integer, default=0)
    invites_count = Column(Integer, default=0)

    # Relationships
    warnings = relationship("Warning", back_populates="user", cascade="all, delete-orphan")
    history = relationship("UserHistory", back_populates="user", cascade="all, delete-orphan")

class UserHistory(Base):
    __tablename__ = 'user_history'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    guild_id = Column(BigInteger, nullable=False)

    # We need a composite foreign key if we want to link strictly to UserProfile,
    # but SQLAlchemy composite FKs can be complex.
    # For simplicity, we just store the IDs, or we can use a simpler approach.
    # Let's map it manually for now to avoid complex composite join conditions in this plan.
    # Actually, let's just link by user_id for now or rely on app logic.
    # To properly link to UserProfile (composite PK), we need:
    # ForeignKeyConstraint(['user_id', 'guild_id'], ['user_profiles.user_id', 'user_profiles.guild_id'])

    from sqlalchemy import ForeignKeyConstraint
    __table_args__ = (
        ForeignKeyConstraint(['user_id', 'guild_id'], ['user_profiles.user_id', 'user_profiles.guild_id']),
    )

    timestamp = Column(DateTime, default=datetime.utcnow)
    old_value = Column(String, nullable=True) # e.g. Old Nickname
    new_value = Column(String, nullable=True) # e.g. New Nickname
    change_type = Column(String, nullable=False) # 'NICKNAME', 'USERNAME'

    user = relationship("UserProfile", back_populates="history")

class Warning(Base):
    __tablename__ = 'warnings'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    guild_id = Column(BigInteger, nullable=False)

    from sqlalchemy import ForeignKeyConstraint
    __table_args__ = (
        ForeignKeyConstraint(['user_id', 'guild_id'], ['user_profiles.user_id', 'user_profiles.guild_id']),
    )

    moderator_id = Column(BigInteger, nullable=False)
    reason = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    user = relationship("UserProfile", back_populates="warnings")

class Ticket(Base):
    __tablename__ = 'tickets'

    id = Column(Integer, primary_key=True, autoincrement=True)
    guild_id = Column(BigInteger, nullable=False)
    channel_id = Column(BigInteger, unique=True, nullable=False)
    owner_id = Column(BigInteger, nullable=False)
    ticket_type = Column(String, nullable=False) # 'Reporting', 'Staff', etc.
    status = Column(String, default='OPEN') # OPEN, CLOSED
    created_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)

class ReactionRole(Base):
    __tablename__ = 'reaction_roles'

    id = Column(Integer, primary_key=True, autoincrement=True)
    guild_id = Column(BigInteger, nullable=False)
    message_id = Column(BigInteger, nullable=False)
    emoji = Column(String, nullable=False) # Unicode or Custom ID
    role_id = Column(BigInteger, nullable=False)
