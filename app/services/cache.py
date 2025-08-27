import time
from typing import Any, Dict, Optional

class ThreadCache:
    def __init__(self, ttl_seconds: int = 3600):
        self.ttl = ttl_seconds
        self.store: Dict[str, Any] = {}

    def key(self, channel: str, thread_ts: str) -> str:
        return f"{channel}:{thread_ts}"

    def set(self, channel: str, thread_ts: str, value: Dict[str, Any]):
        self.store[self.key(channel, thread_ts)] = {"value": value, "ts": time.time()}

    def get(self, channel: str, thread_ts: str) -> Optional[Dict[str, Any]]:
        k = self.key(channel, thread_ts)
        item = self.store.get(k)
        if not item:
            return None
        if time.time() - item["ts"] > self.ttl:
            del self.store[k]
            return None
        return item["value"]
