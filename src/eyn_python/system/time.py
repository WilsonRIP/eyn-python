from datetime import datetime

def to_timestamp(dt: datetime) -> int:
    return int(dt.timestamp())

def from_timestamp(ts: int) -> datetime:
    return datetime.fromtimestamp(ts)
