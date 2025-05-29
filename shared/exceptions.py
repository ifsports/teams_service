class NotFound(Exception):
    def __init__(self, name: str):
        self.name = name


class Conflict(Exception):
    def __init__(self, name: str):
        self.name = name