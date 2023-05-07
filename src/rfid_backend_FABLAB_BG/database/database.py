"""This is the class handling the Database. More to come."""
from os import path
from os.path import dirname, abspath

import toml
from sqlalchemy import create_engine

from .repositories import *

MODULE_DIR = dirname(dirname(abspath(__file__)))
CONFIG_FILE = path.join(MODULE_DIR, "conf\\settings.toml")


class DatabaseBackend:
    """Class handling the connection from and to the database."""

    def __init__(self, settings_path=CONFIG_FILE) -> None:
        """Create instance of Database.

        Args:
            settings_path (str, optional): TOML file settings. Defaults to CONFIG_FILE
        """
        self._settings_path = settings_path
        self._settings = None

        self._loadSettings()
        self._connect()

    def _loadSettings(self) -> None:
        """Load settings from TOML file."""
        self._settings = toml.load(self._settings_path)
        self._url = self._settings["database"]["url"]
        self._name = self._settings["database"]["name"]

    def _connect(self) -> None:
        from sqlalchemy.orm import sessionmaker
        self._engine = create_engine(self._url, echo=True)
        self._session = sessionmaker(bind=self._engine)

    def getOne(self, Model, **kwargs):
        """Return one instance of Model matching kwargs."""
        with self._session() as session:
            try:
                result = session.query(Model).filter_by(**kwargs).one()
                return result
            except NoResultFound:
                return None

    def query(self, Model, **kwargs):
        """Query for instances of Model matching kwargs."""
        with self._session() as session:
            return session.query(Model).filter_by(**kwargs).all()

    def getUserRepository(self):
        with self._session() as session:
            return UserRepository(session)

    def getSession(self) -> Session:
        return self._session()

    def getSessionUserRepository(self, session: Session):
        return UserRepository(session)

    def getRoleRepository(self):
        with self._session() as session:
            return RoleRepository(session)

    def getSessionRoleRepository(self, session: Session):
        return RoleRepository(session)

    def getMachineRepository(self):
        with self._session() as session:
            return MachineRepository(session)

    def getSessionMachineRepository(self, session: Session):
        return MachineRepository(session)

    def getMachineTypeRepository(self):
        with self._session() as session:
            return MachineTypeRepository(session)

    def getSessionMachineTypeRepository(self, session: Session):
        return MachineTypeRepository(session)

    def getUseRepository(self):
        with self._session() as session:
            return UseRepository(session)

    def getSessionUseRepository(self, session: Session):
        return UseRepository(session)

    def getAuthorizationRepository(self):
        with self._session() as session:
            return AuthorizationRepository(session)

    def getSessionAuthorizationRepository(self, session: Session):
        return AuthorizationRepository(session)

    def getMaintenanceRepository(self):
        with self._session() as session:
            return MaintenanceRepository(session)

    def getSessionMaintenanceRepository(self, session: Session):
        return MaintenanceRepository(session)

    def getInterventionRepository(self):
        with self._session() as session:
            return InterventionRepository(session)

    def getSessionInterventionRepository(self, session: Session):
        return InterventionRepository(session)

    def createDatabase(self) -> None:
        Base.metadata.create_all(self._engine, checkfirst=True)

    def dropContents(self) -> None:
        meta = Base.metadata
        with self._session() as session:
            trans = session.begin()
            for table in reversed(meta.sorted_tables):
                session.execute(table.delete())
            trans.commit()
