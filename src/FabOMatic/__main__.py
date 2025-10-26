"""Main module of the backend."""

import logging
import threading
import argparse

from time import sleep

from FabOMatic.database.DatabaseBackend import DatabaseBackend
from FabOMatic.mqtt.MQTTInterface import MQTTInterface
from FabOMatic.logic.MsgMapper import MsgMapper
from FabOMatic.logger import configure_logger


class Backend:
    """Backend class."""

    def __init__(self):
        self._db = DatabaseBackend()
        self._mqtt = MQTTInterface()
        self._mapper = MsgMapper(self._mqtt, self._db)
        self._mapper.registerHandlers()
        self._flaskThread = None

    def connect(self) -> bool:
        """Connect to the MQTT broker and the database."""
        try:
            session = self._db.getSession()
            logging.info(f"Session info: {session.info}")
            self._db.createAndUpdateDatabase()
            self._mqtt.connect()
            return True
        except Exception as ex:
            logging.error("Connection failed: %s", ex, exc_info=True)
            return False

    @property
    def connected(self) -> bool:
        """Check if the MQTT broker is connected."""
        return self._mqtt.connected

    def disconnect(self):
        """Disconnect from the MQTT broker"""
        self._mqtt.disconnect()

    def publishStats(self):
        self._mqtt.publishStats()

    def closeOrphans(self):
        self._db.closeOrphans()

    def purge_data(self):
        """Purge data from the database."""
        self._db.purge_data()

    def getMapper(self) -> MsgMapper:
        return self._mapper


_flaskThread: threading.Thread = None


def _startApp(back: Backend) -> None:
    from FabOMatic.web.webapplication import app

    app.backend = back
    app.run(host="0.0.0.0", port=23336, debug=True, use_reloader=False, ssl_context="adhoc")


def startServer(back: Backend) -> None:
    global _flaskThread
    _flaskThread = threading.Thread(target=_startApp, args=(back,), daemon=True)
    _flaskThread.start()


def start(loglevel):
    """Main function of the backend."""
    configure_logger(loglevel)
    logging.info("Starting backend...")
    back = Backend()
    startServer(back)

    while True:
        if not back.connected:
            if not back.connect():
                logging.error("Failed to connect to Database or MQTT broker")
        else:
            back.publishStats()
            back.closeOrphans()
        sleep(5)


def send_weekly_summary():
    """Send weekly summary emails to all eligible users."""
    from FabOMatic.logic.WeeklySummary import send_weekly_summaries
    from FabOMatic.web.webapplication import app, DBSession
    from FabOMatic.web.authentication import mail

    logging.info("Sending weekly summary emails...")

    # Get database session
    session = DBSession()

    try:
        # Set a dummy backend attribute to satisfy app context
        if not hasattr(app, 'backend'):
            app.backend = None

        with app.app_context():
            stats = send_weekly_summaries(session, mail, app)
            logging.info(
                f"Weekly summary completed: {stats['sent']} sent, {stats['failed']} failed, {stats['skipped']} skipped"
            )
    except Exception as e:
        logging.error(f"Error sending weekly summaries: {e}", exc_info=True)
    finally:
        session.close()


def main():
    parser = argparse.ArgumentParser(description="Fab-O-Matic Backend server.")
    parser.add_argument("-p", "--purge", action="store_true", help="Purge data and exit")
    parser.add_argument("-w", "--weekly-summary", action="store_true", help="Send weekly summary emails and exit")
    parser.add_argument("-l", "--loglevel", type=int, default=10, help="Set log level (default: 10)")

    args = parser.parse_args()

    if args.purge:
        configure_logger(args.loglevel)
        logging.info("Executing purge operation...")
        back = Backend()
        back.purge_data()
        logging.info("Purge operation completed. Exiting.")
    elif args.weekly_summary:
        configure_logger(args.loglevel)
        send_weekly_summary()
        logging.info("Weekly summary operation completed. Exiting.")
    else:
        start(args.loglevel)


if __name__ == "__main__":
    main()
