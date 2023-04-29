from datetime import datetime

from sqlalchemy import (
    UUID,
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    PrimaryKeyConstraint,
    String,
    func,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import MetaData

from app.db.enums import ChatState, ChatUserRole

Base = declarative_base(metadata=MetaData())


class User(Base):
    __tablename__ = "users"

    uid: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)


class Chat(Base):
    __tablename__ = "chats"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    state: Mapped[ChatState] = mapped_column(Enum(ChatState), nullable=False)
    time_created: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    time_updated: Mapped[datetime] = mapped_column(DateTime, onupdate=func.now(), nullable=True)


class ChatRelationship(Base):
    __tablename__ = "chats_relationships"

    user_uid: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.uid"), nullable=False, index=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id"), nullable=False, index=True)
    chat_name: Mapped[str] = mapped_column(String(256), nullable=False)
    state: Mapped[ChatState] = mapped_column(Enum(ChatState), nullable=False)
    last_read_message_id: Mapped[int] = mapped_column(BigInteger, nullable=True)
    unread_counter: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    user_role: Mapped[ChatUserRole] = mapped_column(Enum(ChatUserRole), nullable=False)

    __table_args__ = (PrimaryKeyConstraint("user_uid", "chat_id", name="chats_relationships_pk"),)
