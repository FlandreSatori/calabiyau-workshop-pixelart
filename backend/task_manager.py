import threading

class TaskAbortedError(Exception):
    pass

class TaskManager:
    _lock = threading.Lock()
    _paused_event: threading.Event | None = None
    _abort_flag = False

    @classmethod
    def pause_current(cls) -> None:
        cls._abort_flag = False
        with cls._lock:
            if cls._paused_event is None:
                cls._paused_event = threading.Event()
            ev = cls._paused_event
        # Block until resumed
        if ev:
            ev.wait()
            
        if cls._abort_flag:
            cls._abort_flag = False
            raise TaskAbortedError("Task was aborted by user.")

    @classmethod
    def resume_all(cls) -> None:
        with cls._lock:
            if cls._paused_event is not None:
                cls._paused_event.set()
                cls._paused_event = None

    @classmethod
    def abort_all(cls) -> None:
        cls._abort_flag = True
        with cls._lock:
            if cls._paused_event is not None:
                cls._paused_event.set()
                cls._paused_event = None

    @classmethod
    def is_paused(cls) -> bool:
        with cls._lock:
            return cls._paused_event is not None and not cls._paused_event.is_set()
