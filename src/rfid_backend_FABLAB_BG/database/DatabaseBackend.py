"""This is the class handling the Database. More to come."""
from os import path
from os.path import dirname, abspath
import logging
import toml
from sqlalchemy import create_engine
from sqlalchemy.orm.exc import NoResultFound

from .repositories import (
    UseRepository,
    UserRepository,
    RoleRepository,
    MachineRepository,
    MachineTypeRepository,
    AuthorizationRepository,
    MaintenanceRepository,
    InterventionRepository,
    Session,
    Base,
)

MODULE_DIR = dirname(dirname(abspath(__file__)))
CONFIG_FILE = path.join(MODULE_DIR, "conf", "settings.toml")


def getSetting(section: str, setting: str, settings_path: str = CONFIG_FILE) -> str:
    """Return setting from settings.toml.

    Args:
        setting (str): Setting to return
        section (str): Section of setting
        settings_path (str, optional): Path to settings.toml. Defaults to CONFIG_FILE.
    """
    settings = toml.load(settings_path)
    return settings[section][setting]


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
        """Connect to the database."""
        from sqlalchemy.orm import sessionmaker

        self._engine = create_engine(self._url, echo=False)
        self._session = sessionmaker(bind=self._engine)
        logging.info("Connected to database %s", self._url)

    def getOne(self, Model, **kwargs):
        """Return one instance of Model matching kwargs.

        Args:
            Model: The model class to query.
            **kwargs: Keyword arguments to filter the query.

        Returns:
            The first instance of Model matching the kwargs, or None if not found.
        """
        with self._session() as session:
            try:
                result = session.query(Model).filter_by(**kwargs).one()
                return result
            except NoResultFound:
                return None

    def query(self, Model, **kwargs):
        """Query for instances of Model matching kwargs.

        Args:
            Model: The model class to query.
            **kwargs: Keyword arguments to filter the query.

        Returns:
            A list of instances of Model matching the kwargs.
        """
        with self._session() as session:
            return session.query(Model).filter_by(**kwargs).all()

    def getSession(self) -> Session:
        """Get a session object for database operations.

        Returns:
            A session object.
        """
        return self._session()

    def getUserRepository(self, session: Session) -> UserRepository:
        """Get a UserRepository object for user-related database operations.

        Args:
            session: The session object to use for database operations.

        Returns:
            A UserRepository object.
        """
        return UserRepository(session)

    def getRoleRepository(self, session: Session) -> RoleRepository:
        """Get a RoleRepository object for role-related database operations.

        Args:
            session: The session object to use for database operations.

        Returns:
            A RoleRepository object.
        """
        return RoleRepository(session)

    def getMachineRepository(self, session: Session) -> MachineRepository:
        """Get a MachineRepository object for machine-related database operations.

        Args:
            session: The session object to use for database operations.

        Returns:
            A MachineRepository object.
        """
        return MachineRepository(session)

    def getMachineTypeRepository(self, session: Session) -> MachineTypeRepository:
        """Get a MachineTypeRepository object for machine type-related database operations.

        Args:
            session: The session object to use for database operations.

        Returns:
            A MachineTypeRepository object.
        """
        return MachineTypeRepository(session)

    def getUseRepository(self, session: Session) -> UseRepository:
        """Get a UseRepository object for use-related database operations.

        Args:
            session: The session object to use for database operations.

        Returns:
            A UseRepository object.
        """
        return UseRepository(session)

    def getAuthorizationRepository(self, session: Session) -> AuthorizationRepository:
        """Get an AuthorizationRepository object for authorization-related database operations.

        Args:
            session: The session object to use for database operations.

        Returns:
            An AuthorizationRepository object.
        """
        return AuthorizationRepository(session)

    def getMaintenanceRepository(self, session: Session) -> MaintenanceRepository:
        """Get a MaintenanceRepository object for maintenance-related database operations.

        Args:
            session: The session object to use for database operations.

        Returns:
            A MaintenanceRepository object.
        """
        return MaintenanceRepository(session)

    def getInterventionRepository(self, session: Session) -> InterventionRepository:
        """Get an InterventionRepository object for intervention-related database operations.

        Args:
            session: The session object to use for database operations.

        Returns:
            An InterventionRepository object.
        """
        return InterventionRepository(session)

    def createDatabase(self) -> None:
        """Create the database."""
        logging.debug("Creating database %s", self._url)
        Base.metadata.create_all(self._engine, checkfirst=True)

    def dropContents(self) -> None:
        """Drop all contents of the database."""
        logging.warning("Dropping all contents of database: %s", self._url)
        meta = Base.metadata
        with self._session() as session:
            trans = session.begin()
            for table in reversed(meta.sorted_tables):
                session.execute(table.delete())
            trans.commit()
