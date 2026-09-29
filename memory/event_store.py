from ingestion.reader import parse_time


class EventStore:
    """Keeps every customer's events, sorted by event_time."""

    def __init__(self):
        self.by_customer = {}       # customer_id -> list of events
        self.seen_ids = set()       # for duplicate detection
        self.latest_time = {}  
        self.profiles={}     # customer_id -> newest event_time seen so far

    def add(self, event):
        """Add one event. Returns 'on_time', 'late', or 'duplicate'."""
        event_id = event["event_id"]
        if event_id in self.seen_ids:
            return "duplicate"
        self.seen_ids.add(event_id)

        customer_id = event["customer_id"]
        t = parse_time(event["event_time"])

        status = "on_time"
        if customer_id in self.latest_time and t < self.latest_time[customer_id]:
            status = "late"
        else:
            self.latest_time[customer_id] = t

        events = self.by_customer.setdefault(customer_id, [])
        events.append(event)
        events.sort(key=lambda e: parse_time(e["event_time"]))
        return status

    def events_for(self, customer_id, until=None):
        """All events for a customer, optionally only those up to a given time."""
        events = self.by_customer.get(customer_id, [])
        if until is None:
            return events
        return [e for e in events if parse_time(e["event_time"]) <= until]