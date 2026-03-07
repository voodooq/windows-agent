from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from app.schemas.event import Event
from app.events.event_bus import EventBus


@dataclass
class IntervalJob:
    name: str
    interval_sec: int
    event_type: str
    payload_factory: Optional[Callable[[], dict]] = None
    last_run_ts: float = field(default=0.0)


class Scheduler:
    def __init__(self, event_bus: EventBus) -> None:
        self.event_bus = event_bus
        self.jobs: List[IntervalJob] = []
        self._running = False

    def add_interval_job(
        self,
        name: str,
        interval_sec: int,
        event_type: str,
        payload_factory: Optional[Callable[[], dict]] = None,
    ) -> None:
        self.jobs.append(
            IntervalJob(
                name=name,
                interval_sec=interval_sec,
                event_type=event_type,
                payload_factory=payload_factory,
            )
        )

    def tick(self) -> None:
        now = time.time()
        for job in self.jobs:
            if now - job.last_run_ts >= job.interval_sec:
                payload = job.payload_factory() if job.payload_factory else {}
                event = Event(type=job.event_type, payload=payload)
                self.event_bus.publish(event)
                job.last_run_ts = now

    def run_forever(self, sleep_sec: float = 1.0) -> None:
        self._running = True
        while self._running:
            self.tick()
            time.sleep(sleep_sec)

    def stop(self) -> None:
        self._running = False