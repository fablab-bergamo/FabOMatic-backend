import json

from FabOMatic.database.constants import USER_LEVEL


class Parser:
    @staticmethod
    def parse(json_data: str):
        """
        Parses the given JSON data and returns the corresponding query object based on the 'action' field.

        Args:
            json_data (str): The JSON data to parse.

        Returns:
            object: The deserialized query object based on the 'action' field.

        Raises:
            ValueError: If the 'action' field is missing or invalid.
        """
        data = json.loads(json_data)
        if "action" in data:
            match data["action"]:
                case "checkuser":
                    return UserQuery.deserialize(json_data)
                case "checkmachine":
                    return MachineQuery.deserialize(json_data)
                case "startuse":
                    return StartUseQuery.deserialize(json_data)
                case "inuse":
                    return InUseQuery.deserialize(json_data)
                case "stopuse":
                    return EndUseQuery.deserialize(json_data)
                case "maintenance":
                    return RegisterMaintenanceQuery.deserialize(json_data)
                case "alive":
                    return AliveQuery.deserialize(json_data)
                case _:
                    raise ValueError("Invalid action")
        else:
            raise ValueError("Missing action field")


class BaseJson:
    def toJSON(self):
        return json.dumps(self, default=lambda o: (o.__dict__), sort_keys=True, separators=(",", ":"))

    def serialize(self) -> str:
        return json.dumps(self.__dict__)


class UserQuery(BaseJson):
    def __init__(self, card_uid: str):
        self.uid = card_uid
        self.action = "checkuser"

    @staticmethod
    def deserialize(json_data: str):
        data = json.loads(json_data)
        return UserQuery(data["uid"])


class MachineQuery(BaseJson):
    def __init__(self):
        self.action = "checkmachine"

    @staticmethod
    def deserialize(json_data: str):
        return MachineQuery()


class AliveQuery(BaseJson):
    def __init__(self, version: str, ip: str, serial: str, heap: int):
        self.action = "alive"
        self.version = version
        self.ip = ip
        self.serial = serial
        self.heap = heap

    @staticmethod
    def deserialize(json_data: str):
        data = json.loads(json_data)
        # Serial and Heaps have been added in FW revision 0.6.7
        if data.get("serial") is None:
            data["serial"] = ""
        if data.get("heap") is None:
            data["heap"] = 0
        return AliveQuery(data["version"], data["ip"], data["serial"], data["heap"])


class StartUseQuery(BaseJson):
    def __init__(self, card_uid: str, replay: bool = False):
        self.uid = card_uid
        self.action = "startuse"
        self.replay = replay

    @staticmethod
    def deserialize(json_data: str):
        data = json.loads(json_data)
        if data.get("replay") is None:
            data["replay"] = False
        return StartUseQuery(data["uid"], data["replay"])


class EndUseQuery(BaseJson):
    def __init__(self, card_uid: str, duration_s: int, replay: bool = False):
        self.uid = card_uid
        self.duration = duration_s
        self.action = "stopuse"
        self.replay = replay

    @staticmethod
    def deserialize(json_data: str):
        data = json.loads(json_data)
        if data.get("replay") is None:
            data["replay"] = False
        return EndUseQuery(data["uid"], data["duration"], data["replay"])


class InUseQuery(BaseJson):
    def __init__(self, card_uid: str, duration_s: int):
        self.uid = card_uid
        self.duration = duration_s
        self.action = "inuse"

    @staticmethod
    def deserialize(json_data: str):
        data = json.loads(json_data)
        return InUseQuery(data["uid"], data["duration"])


class RegisterMaintenanceQuery(BaseJson):
    def __init__(self, card_uid: str, replay: bool = False):
        self.uid = card_uid
        self.action = "maintenance"
        self.replay = replay

    @staticmethod
    def deserialize(json_data: str):
        data = json.loads(json_data)
        if data.get("replay") is None:
            data["replay"] = False
        return RegisterMaintenanceQuery(data["uid"], data["replay"])


class UserResponse:
    def __init__(
        self, request_ok: bool, is_valid: bool, holder_name: str, user_level: USER_LEVEL | int, missing_auth: bool
    ):
        self.request_ok = request_ok
        self.is_valid = is_valid
        self.name = holder_name
        self.missing_auth = missing_auth
        if isinstance(user_level, USER_LEVEL):
            self.level = user_level.value
        else:
            self.level = user_level

    def serialize(self) -> str:
        return json.dumps(self.__dict__)


class MachineResponse:
    def __init__(
        self,
        request_ok: bool,
        is_valid: bool,
        needs_maintenance: bool,
        allowed: bool,
        name: str,
        type_id: int,
        timeout_min: int = 0,
        grace_period_min: int = 0,
        description: str = "",
    ):
        self.request_ok = request_ok
        self.is_valid = is_valid
        self.maintenance = needs_maintenance
        self.allowed = allowed
        self.name = name
        self.logoff = timeout_min
        self.type = type_id
        self.grace = grace_period_min
        self.description = description

    def serialize(self) -> str:
        return json.dumps(self.__dict__)


class SimpleResponse:
    def __init__(self, request_ok: bool, message: str = ""):
        self.request_ok = request_ok
        self.message = message

    def serialize(self) -> str:
        return json.dumps(self.__dict__)

    def __str__(self):
        return self.serialize()


class StartRequest(BaseJson):
    def __init__(self, card_uid: str):
        self.request_type = "start"
        self.uid = card_uid

    @staticmethod
    def deserialize(json_data: str):
        data = json.loads(json_data)
        return StartRequest(data["uid"])


class StopRequest(BaseJson):
    def __init__(self, card_uid: str):
        self.request_type = "stop"
        self.uid = card_uid

    @staticmethod
    def deserialize(json_data: str):
        data = json.loads(json_data)
        return StopRequest(data["uid"])
