"""Main module of the backend."""
from time import sleep, time

from database import DatabaseBackend
from mqtt import MQTTInterface


class Backend:
    """Backend class."""
    def __init__(self):
        self._m = MQTTInterface()
        self._m.setMachineAliveCallback(self.machineAlive)
        self._m.isMachineAuthorizedCallback(self.isMachineAuthorized)

        self._db = DatabaseBackend()
        self._last_alive = {}

    def machineAlive(self, machine_id: str):
        """Callback for when a machine sends an alive message."""
        self._last_alive[machine_id] = time()

    def isMachineAuthorized(self, machine_id: str):
        """Callback for when a machine asks if it is authorized."""
        pass

    def connect(self):
        """Connect to the MQTT broker and the database."""
        self._m.connect()
        self.createDatabase()

    def disconnect(self):
        """Disconnect from the MQTT broker """
        self._m.disconnect()

    def stats(self) -> str:
        """Return a string with the stats of the backend."""
        machines = self._db.getMachineRepository().get_all()
        users = self._db.getUserRepository().get_all()
        return f"{len(machines)} machines, {len(users)} users loaded."

    def createDatabase(self) -> None:
        """Create the database."""
        self._db.createDatabase()


def main():
    """Main function of the backend."""
    back = Backend()
    back.connect()

    print(back.stats())

    while True:
        print("I'm alive")
        sleep(1)


if __name__ == "__main__":
    main()
