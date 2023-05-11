"""This is the class handling the Database. More to come."""
from os import path
from os.path import dirname, abspath
import logging
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
        self._engine = create_engine(self._url, echo=False)
        self._session = sessionmaker(bind=self._engine)
        logging.info("Connected to database %s", self._url)

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

    def getSession(self) -> Session:
        return self._session()

    def getUserRepository(self, session: Session) -> UserRepository:
        return UserRepository(session)

    def getRoleRepository(self, session: Session) -> RoleRepository:
        return RoleRepository(session)

    def getMachineRepository(self, session: Session) -> MachineRepository:
        return MachineRepository(session)

    def getMachineTypeRepository(self, session: Session) -> MachineTypeRepository:
        return MachineTypeRepository(session)

    def getUseRepository(self, session: Session) -> UseRepository:
        return UseRepository(session)

    def getAuthorizationRepository(self, session: Session) -> AuthorizationRepository:
        return AuthorizationRepository(session)

    def getMaintenanceRepository(self, session: Session) -> MaintenanceRepository:
        return MaintenanceRepository(session)

    def getInterventionRepository(self, session: Session) -> InterventionRepository:
        return InterventionRepository(session)

    def createDatabase(self) -> None:
        logging.debug("Creating database %s", self._url)
        Base.metadata.create_all(self._engine, checkfirst=True)

    def dropContents(self) -> None:
        logging.warning("Dropping all contents of database: %s", self._url)
        meta = Base.metadata
        with self._session() as session:
            trans = session.begin()
            for table in reversed(meta.sorted_tables):
                session.execute(table.delete())
            trans.commit()
