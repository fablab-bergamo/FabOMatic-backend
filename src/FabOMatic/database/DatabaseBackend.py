"""This is the class handling the Database. More to come."""

import os
from os import path
from os.path import dirname, abspath
import logging
from time import time
import toml
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm.exc import NoResultFound

from FabOMatic.database.models import MachineType, Role, Use, User, Machine, Maintenance

from .repositories import (
    BoardsRepository,
    UseRepository,
    UserRepository,
    RoleRepository,
    MachineRepository,
    MachineTypeRepository,
    AuthorizationRepository,
    MaintenanceRepository,
    InterventionRepository,
    UnknownCardsRepository,
    Session,
    Base,
)

MODULE_DIR = dirname(dirname(abspath(__file__)))
CONFIG_FILE = path.join(MODULE_DIR, "conf", "settings.toml")
MIGRATIONS_DIR = path.join(MODULE_DIR, "alembic")


def getSetting(section: str, setting: str, settings_path: str = CONFIG_FILE) -> str:
    """Return setting from settings.toml.

    Args:
        setting (str): Setting to return
        section (str): Section of setting
        settings_path (str, optional): Path to settings.toml. Defaults to CONFIG_FILE.
    """
    settings = toml.load(settings_path)
    return settings[section][setting]


def getDatabaseUrl(settings_path: str = CONFIG_FILE) -> str:
    # Get the database URL
    db_url = getSetting("database", "url", settings_path)

    # Check if it's a SQLite URL
    if db_url.startswith("sqlite:///"):
        # Remove the prefix to get the file path
        file_path = db_url[len("sqlite:///") :]

        # Get the absolute path
        absolute_path = os.path.abspath(file_path)

        # Add the prefix back to get the absolute URL
        absolute_url = "sqlite:///" + absolute_path
    else:
        # If it's not a SQLite URL, just use it as is
        absolute_url = db_url
    return absolute_url


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
        self._url = getDatabaseUrl(self._settings_path)
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

    def getUnknownCardsRepository(self, session: Session) -> UnknownCardsRepository:
        return UnknownCardsRepository(session)

    def getBoardsRepository(self, session: Session) -> BoardsRepository:
        return BoardsRepository(session)

    def deleteExistingDatabase(self) -> bool:
        """Delete the existing database."""
        if self._url.startswith("sqlite:///"):
            file_path = self._url[len("sqlite:///") :]
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception as e:
                    logging.error("Error deleting existing database %s: %s", file_path, e)
                    return False
                logging.warning("Deleted existing database %s", file_path)
                return True
            else:
                logging.warning("No existing database found at %s", file_path)
                return False
        logging.warning("Not deleting non-SQLite database %s", self._url)
        return False

    def createAndUpdateDatabase(self) -> None:
        """Create the database."""
        # Runs any migrations
        from alembic.config import Config
        from alembic import command

        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", self._url)
        alembic_cfg.set_main_option("script_location", MIGRATIONS_DIR)
        alembic_cfg.attributes["configure_logger"] = False
        command.upgrade(alembic_cfg, "head")

        with self._session() as session:
            if len(self.getUserRepository(session).get_all()) == 0:
                self.seedDatabase()

        if self.getUserRepository(session).get_anonymous() is None:
            logging.warning("Adding anonymous role and user to existing database")
            role = self.seedAnonymousRole(session)
            self.seedAnonymousUser(session, role)

    def seedDatabase(self) -> None:
        """Seed the database with initial data."""
        logging.warning("Seeding empty database %s", self._url)
        with self._session() as session:
            mt1 = MachineType(type_name="Default type", type_timeout_min=8 * 60)
            self.getMachineTypeRepository(session).create(mt1)

            r1 = Role(role_name="admins", authorize_all=True, reserved=True, maintenance=True, backend_admin=True)
            self.getRoleRepository(session).create(r1)

            r3 = Role(role_name="Fab Staff", authorize_all=True, reserved=False, maintenance=True, backend_admin=False)
            self.getRoleRepository(session).create(r3)

            r2 = Role(
                role_name="Fab Users", authorize_all=True, reserved=False, maintenance=False, backend_admin=False
            )
            self.getRoleRepository(session).create(r2)

            r4 = self.seedAnonymousRole(session)
            self.seedAnonymousUser(session, r4)

            # Create default admin user
            u1 = User(
                name="admin",
                surname="admin",
                role_id=r1.role_id,
                card_UUID="12345678",
                email=getSetting("web", "default_admin_email"),
            )
            u1.set_password(User.DEFAULT_ADMIN_PASSWORD)
            self.getUserRepository(session).create(u1)

            m1 = Machine(machine_name="MACHINE1", machine_type_id=mt1.type_id)
            self.getMachineRepository(session).create(m1)

    def seedAnonymousRole(self, session) -> Role:
        anrole = Role(
            role_name="Anonymous", authorize_all=False, reserved=True, maintenance=False, backend_admin=False
        )
        self.getRoleRepository(session).create(anrole)
        return anrole

    def seedAnonymousUser(self, session, role) -> User:
        anon = User(
            name="Anonymous",
            surname="",
            role_id=role.role_id,
            card_UUID=None,
            email="",
        )
        self.getUserRepository(session).create(anon)
        return anon

    def dropContents(self) -> None:
        """Drop all contents of the database."""
        logging.warning("Dropping all contents of database: %s", self._url)
        meta = Base.metadata
        with self._session() as session:
            trans = session.begin()
            for table in reversed(meta.sorted_tables):
                session.execute(table.delete())
            trans.commit()

    def copy(self, destination: str) -> None:
        """Copy the database to a new location.

        Args:
            destination (str): The destination of the copy.
        """
        from shutil import copyfile

        copyfile(self._url.replace("sqlite:///", ""), destination)
        logging.info("Copied database from %s to %s", self._name, destination)

    def purge_data(self, max_days: int = 365) -> bool:
        try:
            with self._session() as session:
                # Get the anonymous user who will replace old data
                user_repo = self.getUserRepository(session)
                anon = user_repo.get_anonymous()
                if anon is None:
                    logging.error("Anonymous user not found, cannot purge")
                    return False

                # Calculate the cut-off date for one year ago
                today = datetime.today()
                onemonth_ago = today - timedelta(days=30)
                oneyear_ago = today - timedelta(days=max_days)

                # Get the usage records who are more than 1y old
                use_repo = self.getUseRepository(session)
                nb_deleted = use_repo.purge_records(anon, oneyear_ago)

                # Replace the intervention records who are more than 1y old
                int_repo = self.getInterventionRepository(session)
                nb_deleted += int_repo.purge_records(anon, oneyear_ago)

                # Delete the Failed authentication after 1 month
                failed_repo = self.getUnknownCardsRepository(session)
                nb_deleted += failed_repo.purge_records(onemonth_ago)

            logging.info(f"{nb_deleted} records deleted or anonymized.")
            return True
        except Exception as e:
            # Log any exception that occurs and roll back the transaction
            logging.error(f"Error purging records: {e}")
            return False

    def closeOrphans(self):
        try:
            # Close records from boards more than 1 hour old
            MAX_DELAY_S = 60 * 60 * 1
            with self._session() as session:
                uses_repo = self.getUseRepository(session)
                current_time = time()
                orphans = (
                    session.query(Use)
                    .filter(Use.end_timestamp.is_(None))
                    .filter(Use.last_seen < current_time - MAX_DELAY_S)
                    .all()
                )
                for o in orphans:
                    logging.warning(f"Closing orphan record on {o.serialize()}")
                    uses_repo.endUse(o.machine_id, o.user, int(o.last_seen - o.start_timestamp) + 1, False)
        except Exception as e:
            # Log any exception that occurs and roll back the transaction
            logging.error(f"Error closing orphans records: {e}")
            return False
