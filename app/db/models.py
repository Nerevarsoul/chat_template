from sqlalchemy import (
    UUID,
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    PrimaryKeyConstraint,
    String,
    func,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.schema import MetaData

from app.db.enums import ChatState, ChatUserRole

Base = declarative_base(metadata=MetaData())


class User(Base):
    __tablename__ = "users"

    uid = Column(UUID(as_uuid=True), primary_key=True, index=True)
    name = Column(String(256), nullable=False)
    is_blocked = Column(Boolean, default=False)


class Chat(Base):
    __tablename__ = "chats"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    Column("state", Integer, nullable=False),
    Column("time_created", DateTime(timezone=True), server_default=func.now()),
    Column("time_updated", DateTime(timezone=True), onupdate=func.now()),


class ChatRelationship(Base):
    __tablename__ = "chats_relationships"

    user_uid = Column(UUID(as_uuid=True), ForeignKey("users.uid"), nullable=False, index=True)
    chat_id = Column(BigInteger, ForeignKey("chats.id"), nullable=False, index=True)
    chat_name = Column(String(256), nullable=False)
    state = Column(Enum(ChatState), nullable=False)
    is_admin = Column(Boolean, default=False)
    last_read_message_id = Column(BigInteger)
    unread_counter = Column(Integer, default=0)
    is_pinned = Column(Boolean, default=False)
    user_role = Column(Enum(ChatUserRole))

    __table_args__ = (PrimaryKeyConstraint("user_uid", "chat_id", name="chats_relationships_pk"),)
