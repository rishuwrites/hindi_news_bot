import datetime as dt, json, os
from config import SLOTS_IST
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
F = "slots.json"
fmt = lambda t: t.strftime("%Y-%m-%dT%H:%M:%SZ")

def _taken():
    try: return json.load(open(F))
    except Exception: return []

def next_slot(now=None, min_lead_min=8):
    """Next upload slot (IST list in config) not already used by another scheduled video."""
    now = now or dt.datetime.now(dt.timezone.utc); taken = set(_taken())
    for d in range(0, 3):
        day = (now.astimezone(IST) + dt.timedelta(days=d)).date()
        for h, m in SLOTS_IST:
            t = dt.datetime(day.year, day.month, day.day, h, m, tzinfo=IST).astimezone(dt.timezone.utc)
            if t > now + dt.timedelta(minutes=min_lead_min) and fmt(t) not in taken: return t

def take(t):
    keep = [x for x in _taken() if x >= fmt(dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=2))]
    json.dump(keep + [fmt(t)], open(F, "w"))
