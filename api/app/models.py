from datetime import datetime
from pydantic import BaseModel, Field

# what a valid reading looks like.
class Reading(BaseModel):
    device_id: str = Field(min_length=1, max_length=64)
    ts: datetime                                   # ISO 8601, e.g. 2026-11-10T14:05:12Z
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    speed_mph: float | None = Field(default=None, ge=0, le=200)
    rpm: int | None = Field(default=None, ge=0, le=10000)
    coolant_c: float | None = None
    fault_codes: list[str] = []
    on_battery: bool = False

    