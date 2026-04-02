class DependencyCycleError(Exception):
    def __init__(self, cycle_path: str):
        super().__init__(cycle_path)
        self.cycle_path = cycle_path
