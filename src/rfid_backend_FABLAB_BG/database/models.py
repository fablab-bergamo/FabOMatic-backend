import sqlite3
import os
from .constants import DEFAULT_TIMEOUT_MINUTES, USER_LEVEL

from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey
from sqlalchemy import event, Engine, Index
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if type(dbapi_connection) is sqlite3.Connection:  # play well with other DB backends
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


class Role(Base):
    """Dataclass handling a role."""

    __tablename__ = "roles"

    role_id = Column(Integer, primary_key=True, autoincrement=True)
    role_name = Column(String, unique=True, nullable=False)
    authorize_all = Column(Boolean, default=False, nullable=False)
    reserved = Column(Boolean, default=False, nullable=False)
    maintenance = Column(Boolean, default=False, nullable=False)

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


class User(Base):
    """Dataclass handling a user."""

    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    surname = Column(String, nullable=False)
    role_id = Column(Integer, ForeignKey("roles.role_id"), nullable=False)
    card_UUID = Column(String, unique=True, nullable=True)
    disabled = Column(Boolean, unique=False, nullable=False, default=False)

    authorizations = relationship("Authorization", back_populates="user")
    interventions = relationship("Intervention", back_populates="user")
    uses = relationship("Use", back_populates="user")
    role = relationship("Role", back_populates="users")

    __table_args__ = (Index("idx_users_card_UUID_unique", "card_UUID", unique=True),)

    def serialize(self):
        """Serialize data and return a Dict."""
        return {
            "user_id": self.user_id,
            "name": self.name,
            "surname": self.surname,
            "role_id": self.role_id,
            "authorization_ids": [auth.authorization_id for auth in self.authorizations],
            "card_UUID": self.card_UUID,
        }

    @classmethod
    def from_dict(cls, dict_data):
        """Deserialize data from Dictionary."""
        return cls(**dict_data)

    def user_level(self) -> USER_LEVEL:
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
    machine_id = Column(Integer, ForeignKey("machines.machine_id"), nullable=False)
    attachment = Column(String, nullable=True)

    machine = relationship("Machine", back_populates="maintenances")
    interventions = relationship("Intervention", back_populates="maintenance")

    def serialize(self):
        """Serialize data and return a Dict."""
        return {
            "maintenance_id": self.maintenance_id,
            "hours_between": self.hours_between,
            "description": self.description,
            "machine_id": self.machine_id,
        }

    @classmethod
    def from_dict(cls, dict_data):
        """Deserialize data from Dictionary."""
        return cls(**dict_data)

    @property
    def attachment_path(self):
        """Get the file attachment path."""
        if self.attachment:
            return os.path.join("upload", self.attachment)
        return None

    @property
    def has_attachment(self):
        """Check if the intervention has an attachment."""
        return bool(self.attachment)


class Intervention(Base):
    """Class handling an intervention."""

    __tablename__ = "interventions"

    intervention_id = Column(Integer, primary_key=True, autoincrement=True)
    maintenance_id = Column(Integer, ForeignKey("maintenances.maintenance_id"), nullable=False)
    machine_id = Column(Integer, ForeignKey("machines.machine_id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    timestamp = Column(Float, nullable=False)

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
        }


class MachineType(Base):
    """Dataclass handling a machine type."""

    __tablename__ = "machine_types"

    type_id = Column(Integer, primary_key=True, autoincrement=True)
    type_name = Column(String, unique=True, nullable=False)
    type_timeout_min = Column(Integer, unique=False, nullable=False, default=DEFAULT_TIMEOUT_MINUTES)
    machines = relationship("Machine", back_populates="machine_type")
    __table_args__ = (Index("idx_machine_types_type_name_unique", "type_name", unique=True),)

    def serialize(self):
        """Serialize data and return a Dict."""
        return {"type_id": self.type_id, "type_name": self.type_name, "type_timeout_min": self.type_timeout_min}

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
    machine_type = relationship("MachineType", back_populates="machines")
    uses = relationship("Use", back_populates="machine")

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


class Use(Base):
    """Class handling machine use."""

    __tablename__ = "uses"

    use_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    machine_id = Column(Integer, ForeignKey("machines.machine_id"), nullable=False)
    start_timestamp = Column(Float, nullable=False)
    end_timestamp = Column(Float, nullable=True)

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
        }
