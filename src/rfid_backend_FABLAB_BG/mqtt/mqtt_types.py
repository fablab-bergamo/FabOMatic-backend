import json


class Parser:
    @staticmethod
    def parse(json_data: str):
        data = json.loads(json_data)
        if "action" in data:
            match data["action"]:
                case "check_user":
                    return UserQuery.deserialize(json_data)
                case "check_machine":
                    return MachineQuery.deserialize(json_data)
                case "startuse":
                    return StartUseQuery.deserialize(json_data)
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


class UserQuery:
    action = "check_user"

    def __init__(self, card_uid: str):
        self.uid = card_uid

    @staticmethod
    def deserialize(json_data: str):
        data = json.loads(json_data)
        return UserQuery(data["uid"])


class MachineQuery:
    action = "check_machine"

    @staticmethod
    def deserialize(json_data: str):
        return MachineQuery()


class AliveQuery:
    action = "alive"

    @staticmethod
    def deserialize(json_data: str):
        return AliveQuery()


class StartUseQuery:
    action = "startuse"

    def __init__(self, card_uid: str):
        self.uid = card_uid

    @staticmethod
    def deserialize(json_data: str):
        data = json.loads(json_data)
        return StartUseQuery(data["uid"])


class EndUseQuery:
    action = "stopuse"

    def __init__(self, card_uid: str, duration_s: int):
        self.uid = card_uid
        self.duration = duration_s

    @staticmethod
    def deserialize(json_data: str):
        data = json.loads(json_data)
        return EndUseQuery(data["uid"], data["duration"])


class RegisterMaintenanceQuery:
    action = "maintenance"

    def __init__(self, card_uid: str):
        self.uid = card_uid

    @staticmethod
    def deserialize(json_data: str):
        data = json.loads(json_data)
        return RegisterMaintenanceQuery(data["uid"])


class UserResponse:
    def __init__(self, request_ok: bool, is_valid: bool, holder_name: str, user_level: int):
        self.request_ok = request_ok
        self.is_valid = is_valid
        self.name = holder_name
        self.level = user_level

    def serialize(self) -> str:
        return json.dumps(self.__dict__)


class MachineResponse:
    def __init__(self, request_ok: bool, is_valid: bool, needs_maintenance: bool, allowed: bool):
        self.request_ok = request_ok
        self.is_valid = is_valid
        self.maintenance = needs_maintenance
        self.allowed = allowed

    def serialize(self) -> str:
        return json.dumps(self.__dict__)


class SimpleResponse:
    def __init__(self, request_ok: bool, message: str = ""):
        self.request_ok = request_ok
        self.message = message

    def serialize(self) -> str:
        return json.dumps(self.__dict__)
