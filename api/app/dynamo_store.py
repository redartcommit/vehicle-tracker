import json
from datetime import datetime, timezone
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Attr, Key

from .models import Reading


def ts_key(ts: datetime) -> str:
    # Same UTC format every time, so DynamoDB sorts readings by time correctly.
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class DynamoStore:
    def __init__(self, telematics_table: str, devices_table: str):
        db = boto3.resource("dynamodb")
        self._telematics = db.Table(telematics_table)
        self._devices = db.Table(devices_table)

    # --- devices ---
    def register_device(self, device_id: str, key_hash: str):
        self._devices.put_item(Item={"key_hash": key_hash, "device_id": device_id})

    def device_for_key_hash(self, key_hash: str) -> str | None:
        item = self._devices.get_item(Key={"key_hash": key_hash}).get("Item")
        return item["device_id"] if item else None

    # --- readings ---
    def save(self, readings: list[Reading]):
        # Same device_id + ts overwrites the old item, so a resent reading never duplicates.
        with self._telematics.batch_writer(overwrite_by_pkeys=["device_id", "ts"]) as batch:
            for r in readings:
                item = json.loads(r.model_dump_json(), parse_float=Decimal)  # DynamoDB needs Decimal, not float
                item["ts"] = ts_key(r.ts)
                batch.put_item(Item=item)

    def latest(self, device_id: str) -> Reading | None:
        resp = self._telematics.query(
            KeyConditionExpression=Key("device_id").eq(device_id),
            ScanIndexForward=False,  # newest first
            Limit=1,
        )
        items = resp.get("Items", [])
        return Reading.model_validate(items[0]) if items else None

    def recent_faults(self, device_id: str, limit: int = 20) -> list[Reading]:
        results, start_key = [], None
        while len(results) < limit:
            kwargs = {
                "KeyConditionExpression": Key("device_id").eq(device_id),
                "FilterExpression": Attr("fault_codes").size().gt(0),
                "ScanIndexForward": False,
            }
            if start_key:
                kwargs["ExclusiveStartKey"] = start_key
            resp = self._telematics.query(**kwargs)
            results += [Reading.model_validate(i) for i in resp.get("Items", [])]
            start_key = resp.get("LastEvaluatedKey")
            if not start_key:
                break
        return results[:limit]