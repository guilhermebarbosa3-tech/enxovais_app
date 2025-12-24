from .db import audit as audit_insert

def log_change(entity, entity_id, action, field=None, before=None, after=None, username="system"):
    audit_insert(entity, entity_id, action, field, before, after, username)
