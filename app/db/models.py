from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

# Source of a lead that arrived without a ?src= label.
DEFAULT_SOURCE = "direct"

# Lead statuses. Stored as text, not a Postgres enum, so a new status needs no
# migration. Leads are never deleted: "rejected" is a status that keeps the
# lead out of the working tabs but in the statistics.
STATUS_NEW = "new"
STATUS_IN_WORK = "in_work"
STATUS_BOUGHT = "bought"
STATUS_REJECTED = "rejected"
STATUSES = (STATUS_NEW, STATUS_IN_WORK, STATUS_BOUGHT, STATUS_REJECTED)

# Closed statuses: the deal is over and the seller's contact details are no
# longer needed. The retention period counts from entering one of these.
CLOSED_STATUSES = (STATUS_BOUGHT, STATUS_REJECTED)

# Form answers that have a column of their own. Everything else the preset
# asks goes to `answers`, so adding a question never needs a migration.
FIXED_ANSWER_COLUMNS = {
    "make": str,
    "model": str,
    "year": int,
    "mileage": int,
    "asking_price": int,
    "location": str,
    "phone": str,
    "name": str,
}


class Lead(Base):
    """A car seller's request, created when the contact step is submitted."""

    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)

    make: Mapped[str | None] = mapped_column(String(64))
    model: Mapped[str | None] = mapped_column(String(64))
    year: Mapped[int | None] = mapped_column(Integer)
    mileage: Mapped[int | None] = mapped_column(Integer)
    # What the seller wants for the car, in whole units of CURRENCY. Optional:
    # many sellers have no idea and wait for an offer. Deal data, not personal
    # data, so retention keeps it.
    asking_price: Mapped[int | None] = mapped_column(BigInteger)
    location: Mapped[str | None] = mapped_column(String(128))
    # Personal data: wiped by retention after the lead is closed.
    phone: Mapped[str | None] = mapped_column(String(32))
    name: Mapped[str | None] = mapped_column(String(128))

    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=STATUS_NEW, server_default=STATUS_NEW, index=True
    )
    # Source label frozen when the lead is created. Statistics group by it, so
    # last month's numbers never change when a seller later scans another code.
    source: Mapped[str] = mapped_column(
        String(64), nullable=False, default=DEFAULT_SOURCE, server_default=DEFAULT_SOURCE
    )
    has_photos: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    # When the lead entered a closed status. Cleared if it is reopened.
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Every other answer, keyed by preset field id.
    answers: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    # Which preset produced the answers, so old leads still render after the
    # preset changes.
    preset_id: Mapped[str] = mapped_column(String(64), nullable=False)

    # Seller pressed the final submit on the review step. Until then the lead
    # exists (saved at the contact step) but photos may still be coming.
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # First time the owner opened the lead.
    viewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status_changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # When retention wiped the personal data. Tells "never given" apart from
    # "deleted after the retention period", so the owner does not think the
    # system lost a phone number.
    purged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    photos: Mapped[list["Photo"]] = relationship(
        back_populates="lead", cascade="all, delete-orphan", order_by="Photo.id"
    )
    notes: Mapped[list["Note"]] = relationship(cascade="all, delete-orphan", order_by="Note.id")
    events: Mapped[list["LeadEvent"]] = relationship(
        cascade="all, delete-orphan", order_by="LeadEvent.id"
    )

    def __repr__(self) -> str:
        return f"<Lead id={self.id} status={self.status!r} source={self.source!r}>"


class Photo(Base):
    """A photo of the car, stored in the bucket; the row keeps the object keys.

    Photos are re-encoded on upload (EXIF, including GPS, is dropped), and a
    small preview is stored next to each one for the lead list.
    """

    __tablename__ = "photos"
    # One photo per guided angle; extra photos have no slot and are unlimited
    # here (the preset caps them).
    __table_args__ = (UniqueConstraint("lead_id", "slot"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    lead_id: Mapped[int] = mapped_column(
        ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Preset slot id ("front_left"), or None for an extra photo.
    slot: Mapped[str | None] = mapped_column(String(64))
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    thumb_key: Mapped[str] = mapped_column(String(255), nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    lead: Mapped[Lead] = relationship(back_populates="photos")


class Note(Base):
    """The owner's note on a lead: negotiation details, agreed price, viewing time.

    Deleting only marks the note, so the dashboard's "Undo" can bring it back.
    Notes are the owner's own words and are not touched by retention; the
    help screen says not to keep sellers' contact details in them.
    """

    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    lead_id: Mapped[int] = mapped_column(
        ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LeadEvent(Base):
    """A line in the lead's activity log, such as a status change."""

    __tablename__ = "lead_events"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    lead_id: Mapped[int] = mapped_column(
        ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    from_status: Mapped[str | None] = mapped_column(String(16))
    to_status: Mapped[str | None] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class OwnerAccount(Base):
    """The single owner login of this instance (one row, id 1).

    The password starts as OWNER_PASSWORD, and the dashboard asks the owner to
    replace it at the first sign-in: while both hashes are the same, the
    password is the one that was handed over (app/services/auth.py). The hash
    of the environment value is kept separately: when OWNER_PASSWORD is changed
    and the app restarted, the dashboard password is reset to it, which is the
    way back in after a forgotten password.
    """

    __tablename__ = "owner_account"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    env_password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    password_changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class OwnerSession(Base):
    """A signed-in device. Only a hash of the cookie value is stored."""

    __tablename__ = "owner_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    user_agent: Mapped[str | None] = mapped_column(String(255))


class PushSubscription(Base):
    """A device that receives Web Push notifications (the owner's phone, laptop)."""

    __tablename__ = "push_subscriptions"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    endpoint: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    p256dh: Mapped[str] = mapped_column(String(128), nullable=False)
    auth: Mapped[str] = mapped_column(String(64), nullable=False)
    user_agent: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_failure_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failure_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )


# Events waiting to be delivered to the owner.
EVENT_NEW_LEAD = "new_lead"
EVENT_PHOTOS_ADDED = "photos_added"


class OutboxEvent(Base):
    """A notification to deliver, written in the same transaction as its cause.

    A restart between saving a lead and notifying the owner cannot lose the
    notification: the worker picks up whatever is still pending, retries
    with growing pauses, and gives up only after several attempts.
    """

    __tablename__ = "notification_outbox"
    __table_args__ = (Index("ix_notification_outbox_due", "status", "next_attempt_at"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    lead_id: Mapped[int] = mapped_column(
        ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    # pending -> sent | skipped (no device to deliver to) | failed (gave up)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending", server_default="pending"
    )
    attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    next_attempt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Technical reason only, never personal data.
    last_error: Mapped[str | None] = mapped_column(String(255))
