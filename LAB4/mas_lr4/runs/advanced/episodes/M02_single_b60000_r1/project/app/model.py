from dataclasses import dataclass, field


@dataclass
class Job:
    id: str
    deps: list = field(default_factory=list)
    resources: list = field(default_factory=list)
    priority: int = 0
    duration: int = 1
    failures: int = 0
    max_retries: int = 0
    version: int = 1
    state: str = 'blocked'
    attempts: int = 0
    remaining: int = 0
    ticket: object = None
    completed_at: object = None
    dep_versions: dict = field(default_factory=dict)

    def reset(self):
        self.version += 1
        self.state = 'blocked'
        self.attempts = self.remaining = 0
        self.ticket = self.completed_at = None
        self.dep_versions = {}


def load_jobs(rows):
    return {row['id']: Job(**row) for row in rows}
