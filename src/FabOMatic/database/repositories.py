""" Database repositories for the FabOMatic application."""

import logging
from datetime import datetime
from time import time
from typing import List, Optional, Tuple

from sqlalchemy import update
from sqlalchemy.orm import Session

from .models import (
    Board,
    Use,
    Machine,
    MachineType,
    Intervention,
    User,
    Maintenance,
    Authorization,
    Role,
    Base,
    UnknownCard,
)
from .constants import DEFAULT_TIMEOUT_MINUTES
from sqlalchemy.orm import object_session


class BaseRepository:
    """Base class for all repositories."""

    def __init__(self, db_session: Session):
        self.db_session = db_session

    def create(self, model: Base):
        """Create a new model instance in the database."""
        self.db_session.add(model)
        self.db_session.commit()
        self.db_session.refresh(model)

    def update(self, model: Base):
        """Update an existing model instance in the database."""
        if object_session(model) is None:
            raise ValueError("Object is not bound to a session")
        object_session(model).commit()
        self.db_session.refresh(model)

    def delete(self, model: Base):
        """Delete a model instance from the database."""
        self.db_session.delete(model)
        self.db_session.commit()

    def rollback(self):
        """Rollback the current database session."""
        self.db_session.rollback()

    def get_all_model(self, model_class: type) -> List[Base]:
        """Retrieve all model instances of a given class from the database."""
        return self.db_session.query(model_class).all()

    def filter_by_model(self, model_class: type, **kwargs) -> List[Base]:
        """Filter model instances of a given class by specified criteria."""
        return self.db_session.query(model_class).filter_by(**kwargs).all()

    def get_model_by_id(self, model_class: type, id_filter: int) -> Base:
        """Retrieve a model instance of a given class by its ID."""
        primary_key_name = model_class.__table__.primary_key.columns.keys()[0]
        return self.db_session.query(model_class).filter_by(**{primary_key_name: id_filter}).first()

    def bulk_create(self, entities):
        self.db_session.bulk_save_objects(entities)


class RoleRepository(BaseRepository):
    """
    Repository class for managing Role objects in the database.
    """

    def __init__(self, db_session: Session):
        super().__init__(db_session)

    def get_by_role_name(self, role_name: str) -> Optional[Role]:
        """
        Retrieve a role by its name.

        Args:
            role_name (str): The name of the role.

        Returns:
            Optional[Role]: The role object if found, None otherwise.
        """
        return self.db_session.query(Role).filter_by(role_name=role_name).first()

    def get_all(self) -> List[Role]:
        """
        Retrieve all roles.

        Returns:
            List[Role]: A list of all roles.
        """
        return self.db_session.query(Role).order_by(Role.role_id).all()

    def get_by_id(self, id: int) -> Base:
        """
        Retrieve a role by its ID.

        Args:
            id (int): The ID of the role.

        Returns:
            Base: The role object if found, None otherwise.
        """
        return self.db_session.query(Role).filter_by(role_id=id).first()


class MachineTypeRepository(BaseRepository):
    """
    Repository class for managing MachineType entities.
    """

    def __init__(self, db_session: Session):
        super().__init__(db_session)

    def get_all(self) -> List[MachineType]:
        """
        Retrieves all MachineType entities from the database.

        Returns:
            A list of MachineType entities.
        """
        return self.db_session.query(MachineType).order_by(MachineType.type_id).all()

    def get_by_id(self, id: int) -> Base:
        """
        Retrieves a MachineType entity by its ID.

        Args:
            id: The ID of the MachineType entity to retrieve.

        Returns:
            The MachineType entity with the specified ID, or None if not found.
        """
        return self.db_session.query(MachineType).filter_by(type_id=id).first()


class UserRepository(BaseRepository):
    """Repository class for managing User objects in the database."""

    def __init__(self, db_session: Session):
        super().__init__(db_session)

    def getUserByCardUUID(self, card_uuid: str) -> Optional[User]:
        """Get a user by their card UUID.

        Args:
            card_uuid (str): The card UUID of the user.

        Returns:
            Optional[User]: The user object if found, None otherwise.
        """
        return self.db_session.query(User).filter_by(card_UUID=card_uuid).first()

    def getUserUses(self, user: User) -> List[Use]:
        """Get all the uses of a user.

        Args:
            user (User): The user object.

        Returns:
            List[Use]: A list of use objects associated with the user.
        """
        return self.db_session.query(Use).filter(Use.user_id == user.user_id).all()

    def getUserTotalTime(self, user_id: int) -> float:
        """Return total time the User has used the machines.

        Args:
            user_id (int): id of the User

        Returns:
            float: User time in seconds
        """
        uses = self.db_session.query(Use).filter(Use.user_id == user_id, Use.end_timestamp.is_not(None)).all()
        return sum([use.end_timestamp - use.start_timestamp for use in uses], 0)

    def IsUserAuthorizedForMachine(self, machine: Machine, user: User) -> bool:
        """Return True if the User is authorized to use the Machine, False otherwise.

        Args:
            machine (Machine): The machine object.
            user (User): The user object.

        Returns:
            bool: True if the user is authorized, False otherwise.
        """
        if user.disabled:
            return False
        if user.deleted:
            return False

        if user.role.authorize_all:
            return True

        if machine.blocked:
            return False

        if machine.machine_type.access_management == MachineType.MANAGEMENT_WITHOUT_AUTHORIZATION:
            return True

        authorizations = self.db_session.query(Authorization).filter_by(user_id=user.user_id).all()
        machine_ids = [a.machine_id for a in authorizations]

        return machine.machine_id in machine_ids

    def get_all(self) -> List[User]:
        """Get all users.

        Returns:
            List[User]: A list of all user objects.
        """
        return self.db_session.query(User).order_by(User.user_id).all()

    def get_by_id(self, id: int) -> Optional[User]:
        """Get a user by their ID.

        Args:
            id (int): The ID of the user.

        Returns:
            Optional[User]: The user object if found, None otherwise.
        """
        return self.db_session.query(User).filter_by(user_id=id).first()

    def get_anonymous(self) -> Optional[User]:
        """Get the anonymous user by their ID.

        Returns:
            Optional[User]: The user object if found, None otherwise.
        """
        role = self.db_session.query(Role).filter_by(role_name="Anonymous").first()
        if role is None:
            return None

        return self.db_session.query(User).filter_by(role_id=role.role_id).first()


class AuthorizationRepository(BaseRepository):
    """
    Repository class for managing authorizations in the database.
    """

    def __init__(self, db_session: Session):
        super().__init__(db_session)

    def get_all(self) -> List[Authorization]:
        """
        Retrieves all authorizations from the database.

        Returns:
            A list of Authorization objects.
        """
        return self.db_session.query(Authorization).order_by(Authorization.authorization_id).all()


class MaintenanceRepository(BaseRepository):
    """
    Repository class for handling maintenance operations.
    """

    def __init__(self, db_session: Session):
        super().__init__(db_session)

    def get_all(self) -> List[Maintenance]:
        """
        Retrieve all maintenance records from the database.

        Returns:
            A list of Maintenance objects.
        """
        return self.db_session.query(Maintenance).order_by(Maintenance.maintenance_id).all()


class InterventionRepository(BaseRepository):
    def __init__(self, db_session: Session):
        """
        Initializes an instance of InterventionRepository.

        Args:
            db_session (Session): The database session object.
        """
        super().__init__(db_session)

    def get_all(self) -> List[Intervention]:
        """
        Retrieves all interventions from the database.

        Returns:
            List[Intervention]: A list of Intervention objects.
        """
        return self.db_session.query(Intervention).order_by(Intervention.intervention_id).all()

    def registerInterventionsDone(self, machine_id: int, user_id: int):
        """
        Register interventions done by the user on the machine.

        Args:
            machine_id (int): The ID of the machine.
            user_id (int): The ID of the user.

        Raises:
            ValueError: If the machine_id or user_id is invalid.
            ValueError: If the user is disabled.
        """
        machine = self.db_session.query(Machine).filter_by(machine_id=machine_id).first()
        user = self.db_session.query(User).filter_by(user_id=user_id).first()

        if machine is None or user is None:
            raise ValueError("Wrong machine_id or user_id")

        if user.disabled:
            raise ValueError("Invalid user")

        machine_repo = MachineRepository(self.db_session)
        timestamp = time()
        for maintenance in machine.maintenances:
            if (
                machine_repo.getRelativeUseTimeByMaintenance(machine.machine_id, maintenance)
                > maintenance.hours_between * 3600
            ):
                intervention = Intervention(
                    machine_id=machine.machine_id,
                    maintenance_id=maintenance.maintenance_id,
                    timestamp=timestamp,
                    user_id=user.user_id,
                )
                self.db_session.add(intervention)
        self.db_session.commit()

    def purge_records(self, anon: User, cut_off: datetime) -> int:
        """Purge intervention records older than the cutoff date by anonymizing them.

        Args:
            anon (User): The anonymous user to replace old data with.
            cut_off (datetime): The cutoff date. Records older than this date will be anonymized.

        Returns:
            int: Number of records anonymized.
        """
        try:
            # Convert cutoff datetime to UNIX timestamp (float)
            cutoff_timestamp = cut_off.timestamp()

            # Query to find records older than the cutoff date
            old_records_query = self.db_session.query(Intervention).filter(Intervention.timestamp < cutoff_timestamp)

            # Count the number of records to be anonymized
            num_records_to_anonymize = old_records_query.count()

            if num_records_to_anonymize > 0:
                # Perform the anonymization (update user_id to anonymous user's ID)
                self.db_session.execute(
                    update(Intervention).where(Intervention.timestamp < cutoff_timestamp).values(user_id=anon.user_id)
                )
                # Commit the transaction
                self.db_session.commit()
                logging.info(f"Anonymized {num_records_to_anonymize} old Intervention records.")

            return num_records_to_anonymize
        except Exception as e:
            # Log any exception that occurs and roll back the transaction
            logging.error(f"Error anonymizing records: {e}")
            self.db_session.rollback()
            return 0


class MachineRepository(BaseRepository):
    """
    Repository class for interacting with the Machine table in the database.
    """

    def __init__(self, db_session: Session):
        super().__init__(db_session)

    def isMachineCurrentlyUsed(self, machine_id: int) -> bool:
        """Return True if the machine is currently being used, False otherwise.

        Args:
            machine_id (int): id of the Machine

        Returns:
            bool
        """
        return (
            self.db_session.query(Use).filter(Use.machine_id == machine_id, Use.end_timestamp.is_(None)).first()
            is not None
        )

    def getTimeout(self, machine_id: int) -> int:
        """
        Retrieves the timeout value for a given machine.

        Args:
            machine_id (int): The ID of the machine.

        Returns:
            int: The timeout value in minutes.
        """
        machine = self.get_by_id(machine_id)
        if machine is None:
            return DEFAULT_TIMEOUT_MINUTES
        return machine.machine_type.type_timeout_min

    def getCurrentlyUsedMachines(self) -> List[Machine]:
        """Get a list of the Machine that are being used in this moment.

        Returns:
            List[Machine]
        """
        return (
            self.db_session.query(Machine)
            .join(Use, Machine.machine_id == Use.machine_id)
            .filter(Use.end_timestamp.is_(None))
            .all()
        )

    def get_by_id(self, machine_id: int = None) -> Optional[Machine]:
        """
        Retrieve a Machine by its ID.

        Args:
            machine_id (int): The ID of the machine.

        Returns:
            Optional[Machine]: The Machine object if found, None otherwise.
        """
        return self.db_session.query(Machine).filter_by(machine_id=machine_id).first()

    def get_all(self) -> List[Machine]:
        """
        Retrieve all machines.

        Returns:
            List[Machine]: A list of all machines.
        """
        return self.db_session.query(Machine).order_by(Machine.machine_id).all()

    def getRelativeUseTime(self, machine_id: int) -> int:
        """Return total time the Machine has been used since last intervention.

        Args:
            machine_id (int): id of the Machine

        Returns:
            int: Machine time in seconds
        """
        record = (
            self.db_session.query(Intervention)
            .filter(Intervention.machine_id == machine_id)
            .order_by(Intervention.timestamp.desc())
            .first()
        )

        if record is None:
            last_intervention = 0
        else:
            last_intervention = record.timestamp

        uses = (
            self.db_session.query(Use)
            .filter(
                Use.end_timestamp.is_not(None), Use.machine_id == machine_id, Use.start_timestamp > last_intervention
            )
            .all()
        )

        return sum([use.end_timestamp - use.start_timestamp for use in uses], 0)

    def getRelativeUseTimeByMaintenance(self, machine_id: int, maintenance: Maintenance) -> int:
        """Return total time the Machine has been used since last intervention.

        Args:
            machine_id (int): id of the Machine
            maintenance_id (int): id of the Maintenance

        Returns:
            int: Machine time in seconds
        """
        record = (
            self.db_session.query(Intervention)
            .filter(Intervention.machine_id == machine_id, Intervention.maintenance_id == maintenance.maintenance_id)
            .order_by(Intervention.timestamp.desc())
            .first()
        )

        if record is None:
            last_intervention = 0
        else:
            last_intervention = record.timestamp

        uses = (
            self.db_session.query(Use)
            .filter(
                Use.end_timestamp.is_not(None), Use.machine_id == machine_id, Use.start_timestamp > last_intervention
            )
            .all()
        )

        relative_time = sum([use.end_timestamp - use.start_timestamp for use in uses], 0)
        logging.debug(
            f"Machine {machine_id} Maintenance [{maintenance.description} - {maintenance.lcd_message}], last_intervention {last_intervention} relative time = {relative_time} seconds ({len(uses)} uses)"
        )
        return relative_time

    def getTotalUseTime(self, machine_id: int) -> int:
        """Return total time the Machine has been used.

        Args:
            machine_id (int): id of the Machine

        Returns:
            int: Machine time in seconds
        """
        uses = self.db_session.query(Use).filter(Use.end_timestamp.is_not(None), Use.machine_id == machine_id).all()

        total_time = sum([use.end_timestamp - use.start_timestamp for use in uses], 0)
        logging.debug(f"Machine {machine_id} total time = {total_time} seconds ({len(uses)} uses)")
        return total_time

    def getMachineMaintenanceNeeded(self, machine_id: int) -> Tuple[bool, str]:
        """Return True if the Machine needs any maintenance, False otherwise.

        Args:
            machine_id (int): id of the Machine

        Returns:
            bool
        """
        machine = self.db_session.query(Machine).filter(Machine.machine_id == machine_id).first()
        for maintenance in machine.maintenances:
            if self.getRelativeUseTimeByMaintenance(machine_id, maintenance) > maintenance.hours_between * 3600.0:
                logging.debug(f"Machine {machine_id} needs maintenance [{maintenance.description}]")
                return (True, maintenance.lcd_message)

        return (False, "")


class UseRepository(BaseRepository):
    MAX_DURATION = 3600 * 24

    """Repository class for managing Use objects in the database."""

    def __init__(self, db_session: Session):
        super().__init__(db_session)

    def startUse(self, machine_id: int, user: User, timestamp: float = None, is_replay: bool = False) -> bool:
        """Start a new Use of a Machine by a User.

        Args:
            machine_id (int): id of the Machine
            user (User): User that is using the Machine
            timestamp (float, optional): timestamp of the start of the Use. Current time if None. Defaults to None.

        Returns:
            bool: True if the use was started successfully, False otherwise.
        """

        if timestamp is None:
            timestamp = time()

        machine_repo = MachineRepository(self.db_session)
        machine = machine_repo.get_by_id(machine_id)
        if machine is None or user is None:
            return False

        # Close eventual previous uses which were not closed with duration == (last_seen - start_timestamp)
        for rec in self.db_session.query(Use).filter(
            Use.machine_id == machine.machine_id, Use.end_timestamp.is_(None)
        ):
            logging.warning("Missed stopUse event in previous record, forcing stopUse")
            self.endUse(rec.machine_id, rec.user, int(rec.last_seen - rec.start_timestamp), is_replay)

        # Register start of new use
        self.db_session.add(
            Use(
                user_id=user.user_id,
                machine_id=machine.machine_id,
                start_timestamp=timestamp,
                last_seen=timestamp,
                replay=is_replay,
                end_timestamp=None,
            )
        )
        self.db_session.commit()

        return True

    def inUse(self, machine_id: int, user: User, duration_s: int) -> bool:
        """Register current usage of the machine by a user.

        Args:
            machine_id (int): id of the Machine
            user (User): User that is using the Machine.
            duration_s (int): duration of the Use.

        Returns:
            bool: if the inUse was registered successfully.
        """
        machine_repo = MachineRepository(self.db_session)
        machine = machine_repo.get_by_id(machine_id)
        if machine is None or user is None or duration_s < 0 or duration_s > UseRepository.MAX_DURATION:
            return False

        record = self.db_session.query(Use).filter(Use.machine_id == machine_id, Use.end_timestamp.is_(None)).first()
        end = time()

        if record is None:
            # InUse received but no startUse was received before
            record = Use(
                machine_id=machine_id,
                user_id=user.user_id,
                start_timestamp=(end - duration_s),
                last_seen=end,
                end_timestamp=None,
            )
            logging.warning("Missed startUse event, using inUse data.")
            self.create(record)
        else:
            # Update existing record
            record.last_seen = end

        self.db_session.commit()

        return True

    def endUse(self, machine_id: int, user: User, duration_s: int, is_replay: bool) -> int:
        """End a use that was previously started.

        Args:
            machine_id (int): id of the Machine
            user (User): User that is using the Machine.
            duration_s (int): duration of the Use.

        Returns:
            int: duration of the Use in seconds
        """
        machine_repo = MachineRepository(self.db_session)
        machine = machine_repo.get_by_id(machine_id)
        if machine is None or user is None:
            return 0

        if duration_s < 0 or duration_s > UseRepository.MAX_DURATION:
            duration_s = 1

        record = self.db_session.query(Use).filter(Use.machine_id == machine_id, Use.end_timestamp.is_(None)).first()
        end = time()

        if record is None:
            # Create missing record on the fly since we have all required information
            record = Use(
                machine_id=machine_id,
                user_id=user.user_id,
                start_timestamp=(end - duration_s),
                last_seen=end,
                end_timestamp=end,
                replay=is_replay,
            )

            # Check that there is no duplicate (could happen if a client sends several identical stopUse requests)
            existing_record = (
                self.db_session.query(Use)
                .filter(
                    Use.machine_id == record.machine_id,
                    Use.user_id == record.user_id,
                    Use.start_timestamp == record.start_timestamp,
                    Use.end_timestamp == record.end_timestamp,
                )
                .first()
            )
            if existing_record is None:
                logging.warning("Missing startUse detected, creating new record on the fly.")
                self.create(record)
                machine.machine_hours += (record.end_timestamp - record.start_timestamp) / 3600.0
                self.db_session.commit()
            else:
                logging.warning("Duplicate stopUse detected, ignoring client request")
        else:
            # Update existing record
            record.end_timestamp = record.start_timestamp + duration_s
            record.last_seen = end
            self.db_session.commit()

            # Close eventual previous uses which were not closed
            for rec in self.db_session.query(Use).filter(Use.machine_id == machine_id, Use.end_timestamp.is_(None)):
                duration_s += rec.last_seen - rec.start_timestamp
                rec.end_timestamp = rec.last_seen
                self.db_session.commit()

        machine.machine_hours += duration_s / 3600.0
        machine_repo.update(machine)

        self.db_session.commit()

        return duration_s

    def get_all(self) -> List[Use]:
        """
        Retrieve all Use objects from the database.

        Returns:
            List[Use]: A list of all Use objects.
        """
        return self.db_session.query(Use).order_by(Use.use_id).all()

    def purge_records(self, anon: User, cut_off: datetime) -> int:
        """Purge use records older than the cutoff date by anonymizing them.

        Args:
            anon (User): The anonymous user to replace old data with.
            cut_off (datetime): The cutoff date. Records older than this date will be anonymized.

        Returns:
            int: Number of records anonymized.
        """
        try:
            # Convert cutoff datetime to UNIX timestamp (float)
            cutoff_timestamp = cut_off.timestamp()

            # Query to find records older than the cutoff date
            old_records_query = self.db_session.query(Use).filter(Use.last_seen < cutoff_timestamp)

            # Count the number of records to be anonymized
            num_records_to_anonymize = old_records_query.count()

            if num_records_to_anonymize > 0:
                # Perform the anonymization (update user_id to anonymous user's ID)
                self.db_session.execute(
                    update(Use).where(Use.last_seen < cutoff_timestamp).values(user_id=anon.user_id)
                )
                # Commit the transaction
                self.db_session.commit()
                logging.info(f"Anonymized {num_records_to_anonymize} old Use records.")

            return num_records_to_anonymize
        except Exception as e:
            # Log any exception that occurs and roll back the transaction
            logging.error(f"Error anonymizing records: {e}")
            self.db_session.rollback()
            return 0


class UnknownCardsRepository(BaseRepository):
    def __init__(self, db_session: Session):
        super().__init__(db_session)

    def get_all(self) -> List[UnknownCard]:
        return self.db_session.query(UnknownCard).order_by(UnknownCard.id).all()

    def registerUnknownCard(self, uuid: str, machine: Machine) -> int:
        """Register an unknown card that was used on a machine.

        Args:
            card_uuid (str): UUID of the unknown card
            machine (Machine): Machine where the card was used

        Returns:
            int: id of the new UnknownCard record
        """
        record = UnknownCard(card_UUID=uuid, machine_id=machine.machine_id, timestamp=time())
        self.create(record)
        self.db_session.commit()
        return record.id

    def purge_records(self, cutoff: datetime) -> int:
        """Purge unknown card records older than the cutoff date.

        Args:
            cutoff (datetime): The cutoff date. Records older than this date will be deleted.

        Returns:
            int: Number of records deleted.
        """
        try:
            # Convert cutoff datetime to UNIX timestamp (float)
            cutoff_timestamp = cutoff.timestamp()

            # Query to find records older than the cutoff date
            old_records_query = self.db_session.query(UnknownCard).filter(UnknownCard.timestamp < cutoff_timestamp)
            # Count the number of records to be deleted
            num_deleted = old_records_query.count()
            # Perform the deletion
            old_records_query.delete(synchronize_session=False)
            # Commit the transaction
            self.db_session.commit()
            logging.info(f"Deleted {num_deleted} old UnknownCard records.")
            return num_deleted
        except Exception as e:
            # Log any exception that occurs and roll back the transaction
            logging.error(f"Error purging records: {e}")
            self.db_session.rollback()
            return 0


class BoardsRepository(BaseRepository):
    def __init__(self, db_session: Session):
        super().__init__(db_session)

    def get_all(self) -> List[Board]:
        return self.db_session.query(Board).order_by(Board.board_id).all()

    def registerBoard(self, ip: str, version: str, serial: str, heap: int, machine: Machine) -> int:
        """Register a board that was used on a machine.

        Args:
            ip (str): IP address of the board
            version (str): Firmware version of the board
            serial (str): Serial number of the board
            heap (int): Free heap size of the board
            machine (Machine): Machine where the board was used

        Returns:
            int: id of the new Board record
        """
        if machine is None:
            raise ValueError("Invalid machine")

        # Checks if a board already exists for this machine
        record = self.db_session.query(Board).filter(Board.machine_id == machine.machine_id).first()
        if record is not None:
            record.ip_address = ip
            record.fw_version = version
            record.serial = serial
            record.heap = heap
            record.last_seen = time()
            self.update(record)
            self.db_session.commit()
            logging.debug(
                f"Updated board #{record.board_id} for machine {machine.machine_id} (IP: {ip}, FW: {version}, Serial: {serial})"
            )
            return record.board_id

        # Create a new record
        record = Board(
            ip_address=ip,
            fw_version=version,
            machine_id=machine.machine_id,
            serial=serial,
            heap=heap,
            last_seen=time(),
        )
        self.create(record)
        self.db_session.commit()
        logging.info(
            f"Registered new board #{record.board_id} for machine {machine.machine_id} (IP: {ip}, FW: {version})"
        )
        return record.board_id
