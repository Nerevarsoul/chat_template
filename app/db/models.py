from datetime import datetime

from sqlalchemy import (
    UUID,
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    PrimaryKeyConstraint,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, declarative_base, mapped_column, relationship
from sqlalchemy.schema import MetaData

from app.db.enums import ChatState, ChatUserRole, MessageType

Base = declarative_base(metadata=MetaData())


class User(Base):  # type: ignore[valid-type, misc]
    __tablename__ = "users"

    uid: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)


class Chat(Base):  # type: ignore[valid-type, misc]
    __tablename__ = "chats"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    state: Mapped[ChatState] = mapped_column(Enum(ChatState), nullable=False)
    time_created: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    time_updated: Mapped[datetime] = mapped_column(DateTime, onupdate=func.now(), nullable=True)

    recipients = relationship("ChatRelationship", uselist=True, lazy="noload")


class ChatRelationship(Base):  # type: ignore[valid-type, misc]
    __tablename__ = "chats_relationships"

    user_uid: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.uid"), nullable=False, index=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id"), nullable=False, index=True)
    chat_name: Mapped[str] = mapped_column(String(256), nullable=False)
    state: Mapped[ChatState] = mapped_column(Enum(ChatState), nullable=False)
    last_read_message_id: Mapped[int] = mapped_column(BigInteger, nullable=True)
    unread_counter: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    time_pinned: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    user_role: Mapped[ChatUserRole] = mapped_column(Enum(ChatUserRole), nullable=False)

    chat: Mapped["Chat"] = relationship(lazy="noload")
    user: Mapped["User"] = relationship(lazy="noload")

    __table_args__ = (PrimaryKeyConstraint("user_uid", "chat_id", name="chats_relationships_pk"),)


class Message(Base):  # type: ignore[valid-type, misc]
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_uid: Mapped[UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.uid"), nullable=True, index=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id"), nullable=False, index=True)
    client_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    search_text: Mapped[dict] = mapped_column(TSVECTOR, nullable=False)
    type_: Mapped[MessageType] = mapped_column(Enum(MessageType), nullable=False)
    quoted_message: Mapped[dict] = mapped_column(JSONB, nullable=True)
    mentions: Mapped[dict] = mapped_column(JSONB, nullable=True)
    links: Mapped[list] = mapped_column(ARRAY(String(1000)), nullable=True)
    original_id: Mapped[int] = mapped_column(ForeignKey("messages.id"), nullable=True)
    original_chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id"), nullable=True)
    time_created: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    time_updated: Mapped[datetime] = mapped_column(DateTime, onupdate=func.now(), nullable=True)

    __table_args__ = (Index("search_by_message_text", search_text, postgresql_using="gin"),)
