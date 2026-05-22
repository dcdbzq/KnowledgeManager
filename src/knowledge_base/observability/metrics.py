from dataclasses import dataclass, field
from time import perf_counter
from typing import Any


@dataclass
class MetricsRecorder:
    events: list[dict[str, Any]] = field(default_factory=list)

    def record(self, name: str, **fields: Any) -> None:
        self.events.append({"event": name, **fields})

    def timer(self) -> "Timer":
        return Timer()


class Timer:
    def __enter__(self) -> "Timer":
        self.start = perf_counter()
        self.elapsed_ms = 0.0
        return self

    def __exit__(self, *_args: Any) -> None:
        self.elapsed_ms = round((perf_counter() - self.start) * 1000, 2)
