from time import time
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session, joinedload
from sqlalchemy.orm.exc import NoResultFound

from .models import *


class BaseRepository:
    def __init__(self, db_session: Session):
        self.db_session = db_session

    def create(self, model: Base):
        self.db_session.add(model)
        self.db_session.commit()
        self.db_session.refresh(model)

    def update(self, model: Base):
        self.db_session.add(model)
        self.db_session.commit()

    def delete(self, model: Base):
        self.db_session.delete(model)
        self.db_session.commit()

    def rollback(self):
        self.db_session.rollback()

    def get_all_model(self, model_class: type) -> List[Base]:
        return self.db_session.query(model_class).all()

    def filter_by_model(self, model_class: type, **kwargs) -> List[Base]:
        return self.db_session.query(model_class).filter_by(**kwargs).all()

    def get_model_by_id(self, model_class: type, id_filter: int) -> Base:
        primary_key_name = model_class.__table__.primary_key.columns.keys()[0]
        return self.db_session.query(model_class).filter_by(**{primary_key_name: id_filter}).first()


class RoleRepository(BaseRepository):
    def __init__(self, db_session: Session):
        super().__init__(db_session)

    def get_by_role_name(self, role_name: str) -> Optional[Role]:
        return self.db_session.query(Role).filter_by(role_name=role_name).first()

    def get_all(self) -> List[Role]:
        return self.db_session.query(Role).order_by(Role.role_id).all()

    def get_by_id(self, id: int) -> Base:
        return self.db_session.query(Role).filter_by(role_id=id).first()


class MachineTypeRepository(BaseRepository):
    def __init__(self, db_session: Session):
        super().__init__(db_session)

    def get_all(self) -> List[MachineType]:
        return self.db_session.query(MachineType).order_by(MachineType.type_id).all()

    def get_by_id(self, id: int) -> Base:
        return self.db_session.query(MachineType).filter_by(type_id=id).first()


class UserRepository(BaseRepository):
    def __init__(self, db_session: Session):
        super().__init__(db_session)

    def getUserByCardUUID(self, card_uuid: str) -> Optional[User]:
        return self.db_session.query(User).filter_by(card_UUID=card_uuid).first()

    def getUserUses(self, user: User) -> List[Use]:
        return self.db_session.query(Use).filter(Use.user_id == user.user_id).all()

    def getUserTotalTime(self, user_id: int) -> float:
        """Return total time the User has used the machines.

        Args:
            user_id (int): id of the User

        Returns:
            float: User time in seconds
        """

        uses = self.db_session.query(Use).filter(
            Use.user_id == user_id, Use.end_timestamp != None
        ).all()

        return sum([use.end_timestamp - use.start_timestamp for use in uses], 0)

    def IsUserAuthorizedForMachine(self, machine: Machine, user: User) -> bool:
        """Return True if the User is authorized to use the Machine, False otherwise."""
        if user.role.authorize_all:
            return True

        if machine.blocked:
            return False

        authorizations = self.db_session.query(
            Authorization).filter_by(user_id=user.user_id).all()
        machine_ids = [a.machine_id for a in authorizations]

        return machine.machine_id in machine_ids

    def get_all(self) -> List[User]:
        return self.db_session.query(User).order_by(User.user_id).all()

    def get_by_id(self, id: int) -> Optional[User]:
        return self.db_session.query(User).filter_by(user_id=id).first()


class AuthorizationRepository(BaseRepository):
    def __init__(self, db_session: Session):
        super().__init__(db_session)

    def get_all(self) -> List[Authorization]:
        return self.db_session.query(Authorization).order_by(Authorization.authorization_id).all()


class MaintenanceRepository(BaseRepository):
    def __init__(self, db_session: Session):
        super().__init__(db_session)

    def get_all(self) -> List[Maintenance]:
        return self.db_session.query(Maintenance).order_by(Maintenance.maintenance_id).all()


class InterventionRepository(BaseRepository):
    def __init__(self, db_session: Session):
        super().__init__(db_session)

    def get_all(self) -> List[Intervention]:
        return self.db_session.query(Intervention).order_by(Intervention.intervention_id).all()

    def registerInterventionsDone(self, machine_id: int, user_id: int):
        """Register interventions done by the user on the machine."""

        machine = self.db_session.query(Machine).filter_by(
            machine_id=machine_id).first()
        user = self.db_session.query(User).filter_by(user_id=user_id).first()

        if machine is None or user is None:
            raise Exception("Wrong machine_id or user_id")

        machine_repo = MachineRepository(self.db_session)
        timestamp = time()
        for maintenance in machine.maintenances:
            if machine_repo.getRelativeUseTimeByMaintenance(machine.machine_id, maintenance.maintenance_id) > maintenance.between_hours * 3600:
                intervention = Intervention(
                    machine_id=machine.machine_id,
                    maintenance_id=maintenance.maintenance_id,
                    timestamp=timestamp,
                    user_id=user.user_id
                )
                self.db_session.add(intervention)
        self.db_session.commit()


class MachineRepository(BaseRepository):
    def __init__(self, db_session: Session):
        super().__init__(db_session)

    def isMachineCurrentlyUsed(self, machine_id: int) -> bool:
        """Return True if the machine is currently being used, False otherwise.

        Args:
            machine_id (int): id of the Machine

        Returns:
            bool
        """
        return self.db_session.query(Use).filter(
            Use.machine_id == machine_id,
            Use.end_timestamp == None
        ).first() is not None

    def getCurrentlyUsedMachines(self) -> List[Machine]:
        """Get a list of the Machine that are being used in this moment.

        Returns:
            List[Machine]
        """
        return self.db_session.query(Machine).join(Use, Machine.machine_id == Use.machine_id).filter(Use.end_timestamp == None).all()

    def get_by_id(self, machine_id: int = None) -> Optional[Machine]:
        return self.db_session.query(Machine).filter_by(machine_id=machine_id).first()

    def get_all(self) -> List[Machine]:
        return self.db_session.query(Machine).order_by(Machine.machine_id).all()

    def getRelativeUseTime(self, machine_id: int) -> int:
        """Return total time the Machine has been used since last intervention.

        Args:
            machine_id (int): id of the Machine

        Returns:
            int: Machine time in seconds
        """
        record = self.db_session.query(Intervention).filter(
            Intervention.machine_id == machine_id).order_by(Intervention.timestamp.desc()).first()

        if record is None:
            last_intervention = 0
        else:
            last_intervention = record.timestamp

        uses = self.db_session.query(Use).filter(
            Use.end_timestamp != None, Use.machine_id == machine_id, Use.start_timestamp > last_intervention).all()

        return sum([use.end_timestamp - use.start_timestamp for use in uses], 0)

    def getRelativeUseTimeByMaintenance(self, machine_id: int, maintenance_id: int) -> int:
        """Return total time the Machine has been used since last intervention.

        Args:
            machine_id (int): id of the Machine
            maintenance_id (int): id of the Maintenance

        Returns:
            int: Machine time in seconds
        """
        record = self.db_session.query(Intervention).filter(Intervention.machine_id == machine_id,
                                                            Intervention.maintenance_id == maintenance_id).order_by(Intervention.timestamp.desc()).first()

        if record is None:
            last_intervention = 0
        else:
            last_intervention = record.timestamp

        uses = self.db_session.query(Use).filter(
            Use.end_timestamp != None, Use.machine_id == machine_id, Use.start_timestamp > last_intervention).all()

        return sum([use.end_timestamp - use.start_timestamp for use in uses], 0)

    def getTotalUseTime(self, machine_id: int) -> int:
        """Return total time the Machine has been used.

        Args:
            machine_id (int): id of the Machine

        Returns:
            int: Machine time in seconds
        """
        uses = self.db_session.query(Use).filter(
            Use.end_timestamp != None, Use.machine_id == machine_id).all()

        return sum([use.end_timestamp - use.start_timestamp for use in uses], 0)

    def getMachineMaintenanceNeeded(self, machine_id: int) -> Tuple[bool, str]:
        """Return True if the Machine needs any maintenance, False otherwise.

        Args:
            machine_id (int): id of the Machine

        Returns:
            bool
        """
        machine = self.db_session.query(Machine).filter(
            Machine.machine_id == machine_id).first()
        for maintenance in machine.maintenances:
            if self.getRelativeUseTimeByMaintenance(machine_id, maintenance.maintenance_id) > maintenance.hours_between * 3600.0:
                return (True, maintenance.description)

        return (False, "")


class UseRepository(BaseRepository):
    def __init__(self, db_session: Session):
        super().__init__(db_session)

    def startUse(
            self,
            machine_id: int,
            user: User,
            timestamp: float = None,
    ) -> None:
        """Start a new Use of a Machine by a User.

        Args:
            machine_id (int): id of the Machine
            user (User): User that is using the Machine
            timestamp (float, optional): timestamp of the start of the Use. Current time if None. Defaults to None.
        """

        if timestamp is None:
            timestamp = time()

        # Close eventual previous uses which were not closed with 0 duration
        self.db_session.query(Use).filter(Use.machine_id == machine_id, Use.end_timestamp == None).update(
            {Use.end_timestamp: Use.start_timestamp})

        # Register start of new use
        self.db_session.add(
            Use(user_id=user.user_id, machine_id=machine_id, start_timestamp=timestamp))
        self.db_session.commit()

    def endUse(
            self,
            machine_id: int,
            user: User,
            duration_s: int
    ) -> int:
        """End a use that was previously started.

        Args:
            machine_id (int): id of the Machine
            user (User): User that is using the Machine.
            duration_s (int): duration of the Use.

        Returns:
            int: duration of the Use in seconds
        """

        record = self.db_session.query(Use).filter(
            Use.machine_id == machine_id, Use.end_timestamp == None).first()

        if record is None:
            end = time()
            # Create missing record on the fly since we have all required information
            record = Use(machine_id=machine_id, user_id=user.user_id,
                         start_timestamp=(end - duration_s),
                         end_timestamp=end)
            self.create(record)
        else:
            # Update existing record
            record.end_timestamp = record.start_timestamp + duration_s
            self.update(record)

            # Close eventual previous uses which were not closed
            self.db_session.query(Use).filter(Use.machine_id == machine_id, Use.end_timestamp == None).update(
                {Use.end_timestamp: Use.start_timestamp})

        self.db_session.commit()

        return duration_s

    def get_all(self) -> List[Use]:
        return self.db_session.query(Use).order_by(Use.use_id).all()
