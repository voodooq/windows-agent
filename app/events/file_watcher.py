from __future__ import annotations

from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer as WatchdogObserver

from app.schemas.event import Event


class FileChangedHandler(FileSystemEventHandler):
    def __init__(self, event_bus) -> None:
        super().__init__()
        self.event_bus = event_bus

    def on_created(self, event) -> None:
        if event.is_directory:
            return
        self._publish("created", event.src_path)

    def on_modified(self, event) -> None:
        if event.is_directory:
            return
        self._publish("modified", event.src_path)

    def _publish(self, action: str, src_path: str) -> None:
        path = str(Path(src_path).resolve())
        self.event_bus.publish(
            Event(
                type="file.changed",
                payload={
                    "action": action,
                    "path": path,
                    "source": "file_watcher",
                },
            )
        )


class FileWatcher:
    def __init__(self, event_bus) -> None:
        self.event_bus = event_bus
        self.observer = WatchdogObserver()
        self._started = False

    def watch_path(self, path: str, recursive: bool = False) -> None:
        watch_path = Path(path)
        watch_path.mkdir(parents=True, exist_ok=True)

        handler = FileChangedHandler(self.event_bus)
        self.observer.schedule(handler, str(watch_path.resolve()), recursive=recursive)

    def start(self) -> None:
        if not self._started:
            self.observer.start()
            self._started = True

    def stop(self) -> None:
        if self._started:
            self.observer.stop()
            self.observer.join()
            self._started = False