class State:
    def __init__(self, log: str):
        self.log = log
        self.history = []
        self.hints = []
        self.context = {}

    def add_history(self, item):
        self.history.append(item)

    def add_hint(self, hint: str):
        if hint and hint not in self.hints:
            self.hints.append(hint)