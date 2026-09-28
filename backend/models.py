"""Relational projection plus durable event, send, feedback, and export ledgers."""
from sqlalchemy import JSON, ForeignKey, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Delivery(Base):
    __tablename__ = 'deliveries'
    id: Mapped[int] = mapped_column(primary_key=True)
    received_at: Mapped[str]
    event: Mapped[str | None]
    body_sha256: Mapped[str]
    payload: Mapped[dict | list] = mapped_column(JSON)


class Customer(Base):
    __tablename__ = 'customers'
    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str | None]
    phone: Mapped[str | None]
    conversations: Mapped[list['Conversation']] = relationship(back_populates='customer')


class Agent(Base):
    __tablename__ = 'agents'
    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str | None]
    email: Mapped[str | None]


class Conversation(Base):
    __tablename__ = 'conversations'
    id: Mapped[str] = mapped_column(primary_key=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey('customers.id'), index=True)
    started_at: Mapped[float] = mapped_column(index=True)
    closed_at: Mapped[float | None]
    first_response_at: Mapped[float | None]
    first_response_agent_id: Mapped[str | None] = mapped_column(ForeignKey('agents.id'))
    assigned_agent_id: Mapped[str | None] = mapped_column(ForeignKey('agents.id'), index=True)
    resolution_agent_id: Mapped[str | None] = mapped_column(ForeignKey('agents.id'))
    reassignments: Mapped[int]
    frt_seconds: Mapped[float | None]
    resolution_seconds: Mapped[float | None]
    customer: Mapped[Customer] = relationship(back_populates='conversations')
    messages: Mapped[list['Message']] = relationship(back_populates='conversation')
    assigned_agent: Mapped[Agent | None] = relationship(foreign_keys=[assigned_agent_id])


class Message(Base):
    __tablename__ = 'messages'
    id: Mapped[str] = mapped_column(primary_key=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey('customers.id'), index=True)
    conversation_id: Mapped[str | None] = mapped_column(ForeignKey('conversations.id'), index=True)
    at: Mapped[float] = mapped_column(index=True)
    direction: Mapped[str]
    text: Mapped[str | None] = mapped_column(Text)
    agent_email: Mapped[str | None]
    app_type: Mapped[str | None]
    agent_id: Mapped[str | None] = mapped_column(ForeignKey('agents.id'))
    sender_kind: Mapped[str]
    purpose: Mapped[str | None]
    conversation: Mapped[Conversation | None] = relationship(back_populates='messages')


class Assignment(Base):
    __tablename__ = 'assignments'
    id: Mapped[int] = mapped_column(primary_key=True)
    event: Mapped[str]
    customer_id: Mapped[str] = mapped_column(ForeignKey('customers.id'))
    conversation_id: Mapped[str | None] = mapped_column(ForeignKey('conversations.id'), index=True)
    at: Mapped[float]
    agent_id: Mapped[str | None] = mapped_column(ForeignKey('agents.id'))
    previous_agent_id: Mapped[str | None] = mapped_column(ForeignKey('agents.id'))
    is_reassignment: Mapped[bool]


# Ledgers retain immutable identities even if a projection is rebuilt. They do
# not reference projection rows: source history may precede observed conversations.
class SendIntent(Base):
    __tablename__ = 'send_intents'
    id: Mapped[str] = mapped_column(primary_key=True)
    created_at: Mapped[str]
    agent_id: Mapped[str]
    agent_name: Mapped[str | None]
    agent_email: Mapped[str | None]
    message_id: Mapped[str | None] = mapped_column(index=True)
    status: Mapped[str]


class FeedbackRequest(Base):
    __tablename__ = 'feedback_requests'
    conversation_id: Mapped[str] = mapped_column(primary_key=True)
    customer_id: Mapped[str] = mapped_column(index=True)
    agent_id: Mapped[str]
    asked_at: Mapped[float]
    expires_at: Mapped[float]
    status: Mapped[str]
    message_id: Mapped[str | None]


class FeedbackResult(Base):
    __tablename__ = 'feedback_results'
    conversation_id: Mapped[str] = mapped_column(ForeignKey('conversations.id'), primary_key=True)
    received_at: Mapped[float | None]
    rating: Mapped[int | None]
    response_message_id: Mapped[str | None]
    superseded: Mapped[bool] = mapped_column(default=False)


class Outbox(Base):
    __tablename__ = 'outbox'
    destination: Mapped[str] = mapped_column(primary_key=True)
    id: Mapped[str] = mapped_column(primary_key=True)
    payload: Mapped[dict] = mapped_column(JSON)
    sent_at: Mapped[str | None]


class ImportMarker(Base):
    __tablename__ = 'import_markers'
    id: Mapped[str] = mapped_column(primary_key=True)
