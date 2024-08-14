"""Database models for the FabOMatic application."""

import sqlite3
import os
from time import time
from itsdangerous import URLSafeTimedSerializer as Serializer
from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy import event, Engine, Index
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

from .constants import DEFAULT_TIMEOUT_MINUTES, USER_LEVEL

Base = declarative_base()


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Set SQLite PRAGMA foreign_keys=ON."""
    if isinstance(dbapi_connection, sqlite3.Connection):  # play well with other DB backends
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("pragma auto_vacuum = incremental;")
        cursor.execute("pragma optimize;")
        cursor.close()


class Role(Base):
    """Dataclass handling a role."""

    __tablename__ = "roles"

    role_id = Column(Integer, primary_key=True, autoincrement=True)
    role_name = Column(String, unique=True, nullable=False)
    authorize_all = Column(Boolean, default=False, nullable=False)
    reserved = Column(Boolean, default=False, nullable=False)
    maintenance = Column(Boolean, default=False, nullable=False)
    backend_admin = Column(Boolean, default=False, nullable=False)

    users = relationship("User", back_populates="role")
    __table_args__ = (Index("idx_roles_role_name_unique", "role_name", unique=True),)

    def serialize(self):
        """Serialize data and return a Dict."""
        return {
            "role_id": self.role_id,
            "role_name": self.role_name,
            "authorize_all": self.authorize_all,
            "reserved": self.reserved,
            "maintenance": self.maintenance,
        }

    @classmethod
    def from_dict(cls, dict_data):
        """Deserialize data from Dictionary."""
        return cls(**dict_data)


class User(UserMixin, Base):
    """Dataclass handling a user."""

    __tablename__ = "users"
    DEFAULT_ADMIN_PASSWORD = "admin"

    user_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    surname = Column(String, nullable=False)
    role_id = Column(Integer, ForeignKey("roles.role_id"), nullable=False)
    card_UUID = Column(String, unique=True, nullable=True)
    disabled = Column(Boolean, unique=False, nullable=False, default=False)
    deleted = Column(Boolean, unique=False, nullable=False, default=False)
    password_hash = Column(String(128), nullable=True)
    email = Column(String, nullable=True)

    authorizations = relationship("Authorization", back_populates="user")
    interventions = relationship("Intervention", back_populates="user")
    uses = relationship("Use", back_populates="user")
    role = relationship("Role", back_populates="users")

    __table_args__ = (Index("idx_users_card_UUID_unique", "card_UUID", unique=True),)

    """ Methods required by Flask-Login """

    def set_password(self, password) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password) -> bool:
        return check_password_hash(self.password_hash, password)

    def get_id(self) -> str:
        return str(self.user_id)

    """ Email reset """

    def get_reset_token(self, key: bytes, salt: bytes) -> str:
        s = Serializer(secret_key=key, salt=salt)
        return s.dumps({"user_id": self.user_id})

    """ Static method to verify a token"""
    """ Returns the user_id if the token is valid, None otherwise """
    """ max_age is in seconds"""
    """ key and salt must be the same used to generate the token """

    @staticmethod
    def verify_reset_token(token: str, key: bytes, salt: bytes, max_age=1800) -> int | None:
        s = Serializer(secret_key=key, salt=salt)
        try:
            user_id = s.loads(s=token, max_age=max_age)["user_id"]
        except:
            return None

        return int(user_id)

    def serialize(self):
        """Serialize data and return a Dict."""
        return {
            "user_id": self.user_id,
            "name": self.name,
            "surname": self.surname,
            "role_id": self.role_id,
            "authorization_ids": [a.authorization_id for a in self.authorizations],
            "intervention_ids": [i.intervention_id for i in self.interventions],
            "use_ids": [u.use_id for u in self.uses],
            "card_UUID": self.card_UUID,
            "disabled": self.disabled,
            "deleted": self.deleted,
            "email": self.email,
            "password_hash": self.password_hash,
        }

    @classmethod
    def from_dict(cls, dict_data):
        """Deserialize data from Dictionary."""
        return cls(**dict_data)

    def user_level(self) -> USER_LEVEL:
        """Get the user level."""
        if self.disabled:
            return USER_LEVEL.INVALID
        if self.role.authorize_all:
            return USER_LEVEL.ADMIN
        return USER_LEVEL.NORMAL


class Authorization(Base):
    """Dataclass handling an authorization."""

    __tablename__ = "authorizations"

    authorization_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    machine_id = Column(Integer, ForeignKey("machines.machine_id"), nullable=False)

    user = relationship("User", back_populates="authorizations")
    machine = relationship("Machine", back_populates="authorizations")

    __table_args__ = (UniqueConstraint("user_id", "machine_id", name="uix_1"),)

    def serialize(self):
        """Serialize data and return a Dict."""
        return {"authorization_id": self.authorization_id, "user_id": self.user_id, "machine_id": self.machine_id}

    @classmethod
    def from_dict(cls, dict_data):
        """Deserialize data from Dictionary."""
        return cls(**dict_data)


class Maintenance(Base):
    """Dataclass handling a maintenance."""

    __tablename__ = "maintenances"

    maintenance_id = Column(Integer, primary_key=True, autoincrement=True)
    hours_between = Column(Float, nullable=False)
    description = Column(String, nullable=False)
    lcd_message = Column(String, nullable=True, default="")
    machine_id = Column(Integer, ForeignKey("machines.machine_id"), nullable=False)
    instructions_url = Column(String, nullable=True, default="")

    machine = relationship("Machine", back_populates="maintenances")
    interventions = relationship("Intervention", back_populates="maintenance")

    def serialize(self):
        """Serialize data and return a Dict."""
        return {
            "maintenance_id": self.maintenance_id,
            "hours_between": self.hours_between,
            "description": self.description,
            "lcd_message": self.lcd_message,
            "machine_id": self.machine_id,
            "instructions_url": self.instructions_url,
        }

    @classmethod
    def from_dict(cls, dict_data):
        """Deserialize data from Dictionary."""
        return cls(**dict_data)


class Intervention(Base):
    """Class handling an intervention."""

    __tablename__ = "interventions"

    intervention_id = Column(Integer, primary_key=True, autoincrement=True)
    maintenance_id = Column(Integer, ForeignKey("maintenances.maintenance_id"), nullable=False)
    machine_id = Column(Integer, ForeignKey("machines.machine_id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    timestamp = Column(Float, nullable=False)
    replay = Column(Boolean, nullable=True)

    machine = relationship("Machine", back_populates="interventions")
    maintenance = relationship("Maintenance", back_populates="interventions")
    user = relationship("User", back_populates="interventions")

    def serialize(self):
        """Serialize data and return a Dict."""
        return {
            "intervention_id": self.intervention_id,
            "maintenance_id": self.maintenance_id,
            "machine_id": self.machine_id,
            "user_id": self.user_id,
            "timestamp": self.timestamp,
            "replay": self.replay,
        }


class MachineType(Base):
    """Dataclass handling a machine type."""

    __tablename__ = "machine_types"
    MANAGEMENT_WITH_AUTHORIZATION = 0
    MANAGEMENT_WITHOUT_AUTHORIZATION = 1

    type_id = Column(Integer, primary_key=True, autoincrement=True)
    type_name = Column(String, unique=True, nullable=False)
    type_timeout_min = Column(Integer, unique=False, nullable=False, default=DEFAULT_TIMEOUT_MINUTES)
    grace_period_min = Column(Integer, unique=False, nullable=True, default=2)
    access_management = Column(Integer, unique=False, nullable=True, default=MANAGEMENT_WITH_AUTHORIZATION)
    machines = relationship("Machine", back_populates="machine_type")
    __table_args__ = (Index("idx_machine_types_type_name_unique", "type_name", unique=True),)

    def serialize(self):
        """Serialize data and return a Dict."""
        return {
            "type_id": self.type_id,
            "type_name": self.type_name,
            "type_timeout_min": self.type_timeout_min,
            "grace_period_min": self.grace_period_min,
        }

    @classmethod
    def from_dict(cls, dict_data):
        """Deserialize data from Dictionary."""
        return cls(**dict_data)


class Machine(Base):
    """Class handling a machine."""

    __tablename__ = "machines"

    machine_id = Column(Integer, primary_key=True, autoincrement=True)
    machine_name = Column(String, unique=True, nullable=False)
    machine_type_id = Column(Integer, ForeignKey("machine_types.type_id"))
    machine_hours = Column(Float, nullable=False, default=0.0)  # Somewhat redundant with sum of uses duration
    blocked = Column(Boolean, nullable=False, default=False)
    last_seen = Column(Float, nullable=True)
    maintenances = relationship("Maintenance", back_populates="machine")
    interventions = relationship("Intervention", back_populates="machine")
    authorizations = relationship("Authorization", back_populates="machine")
    machine_type = relationship("MachineType", back_populates="machines", lazy=False)
    uses = relationship("Use", back_populates="machine")
    cards = relationship("UnknownCard", back_populates="machine")
    boards = relationship("Board", back_populates="machine")

    __table_args__ = (Index("idx_machines_machine_name_unique", "machine_name", unique=True),)

    def serialize(self):
        """Serialize data and return a Dict."""
        return {
            "machine_id": self.machine_id,
            "machine_name": self.machine_name,
            "machine_type_id": self.machine_type_id,
            "machine_hours": self.machine_hours,
            "blocked": self.blocked,
            "maintenances": [maintenance.maintenance_id for maintenance in self.maintenances],
            "interventions": [intervention.intervention_id for intervention in self.interventions],
        }

    def active_user(self) -> User | None:
        """Get the current user."""
        for use in reversed(self.uses):
            if use.end_timestamp is None:
                return use.user
        return None

    def active_board(self):
        """Get the current board."""
        if len(self.boards) > 0:
            return sorted(self.boards, key=lambda b: b.last_seen, reverse=True)[0]
        return None

    def isOnline(self) -> bool:
        """Indicates is the last machine communication is less than 90s ago"""
        if self.last_seen is None:
            return False

        return time() - self.last_seen < 90


class Use(Base):
    """Class handling machine use."""

    __tablename__ = "uses"

    use_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    machine_id = Column(Integer, ForeignKey("machines.machine_id"), nullable=False)
    start_timestamp = Column(Float, nullable=False)
    last_seen = Column(Float, nullable=False)
    end_timestamp = Column(Float, nullable=True)
    replay = Column(Boolean, nullable=True)

    machine = relationship("Machine", back_populates="uses")
    user = relationship("User", back_populates="uses")

    def serialize(self):
        """Serialize data and return a Dict."""
        return {
            "use_id": self.use_id,
            "user_id": self.user_id,
            "machine_id": self.machine_id,
            "start_timestamp": self.start_timestamp,
            "end_timestamp": self.end_timestamp,
            "last_seen": self.last_seen,
            "replay": self.replay,
        }

    def __str__(self):
        """Return a string representation of the object."""
        return str(self.serialize())


class UnknownCard(Base):
    """Class handling machine use."""

    __tablename__ = "unknown_cards"
    id = Column(Integer, primary_key=True, autoincrement=True)
    card_UUID = Column(String, nullable=False)
    timestamp = Column(Float, nullable=False)
    machine_id = Column(Integer, ForeignKey("machines.machine_id"), nullable=False)

    machine = relationship("Machine", back_populates="cards")

    def serialize(self):
        """Serialize data and return a Dict."""
        return {
            "id": self.id,
            "card_UUID": self.card_UUID,
            "timestamp": self.timestamp,
            "machine_id": self.machine_id,
        }

    @classmethod
    def from_dict(cls, dict_data):
        """Deserialize data from Dictionary."""
        return cls(**dict_data)


class Board(Base):
    """Dataclass handling a role."""

    __tablename__ = "boards"

    board_id = Column(Integer, primary_key=True, autoincrement=True)
    machine_id = Column(Integer, ForeignKey("machines.machine_id"), nullable=False)
    ip_address = Column(String, unique=False, nullable=False)
    fw_version = Column(String, unique=False, nullable=False)
    serial = Column(String, unique=False, nullable=True, default="?")
    heap = Column(Integer, unique=False, nullable=True, default=0)

    last_seen = Column(Float, nullable=False)

    machine = relationship("Machine", back_populates="boards")

    def serialize(self):
        """Serialize data and return a Dict."""
        return {
            "board_id": self.board_id,
            "machine_id": self.machine_id,
            "ip_address": self.ip_address,
            "fw_version": self.fw_version,
            "serial": self.serial,
            "heap": self.heap,
            "last_seen": self.last_seen,
        }

    @classmethod
    def from_dict(cls, dict_data):
        """Deserialize data from Dictionary."""
        return cls(**dict_data)
