from .models import Reading


class InMemoryStore:
    def __init__(self):
        self.reset()

    def reset(self):
        self._readings: dict[str, list[Reading]] = {}
        self._key_hashes: dict[str, str] = {}      # key hash -> device_id

    # --- devices ---
    def register_device(self, device_id: str, key_hash: str):
        self._key_hashes[key_hash] = device_id

    def device_for_key_hash(self, key_hash: str) -> str | None:
        return self._key_hashes.get(key_hash)

    # --- readings ---
    def save(self, readings: list[Reading]):
        for r in readings:
            self._readings.setdefault(r.device_id, []).append(r)

    def latest(self, device_id: str) -> Reading | None:
        readings = self._readings.get(device_id)
        return max(readings, key=lambda r: r.ts) if readings else None

    def recent_faults(self, device_id: str, limit: int = 20) -> list[Reading]:
        readings = sorted(self._readings.get(device_id, []), key=lambda r: r.ts, reverse=True)
        return [r for r in readings if r.fault_codes][:limit]