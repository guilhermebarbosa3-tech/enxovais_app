from .db import audit as audit_insert

def log_change(entity, entity_id, action, field=None, before=None, after=None, user="system"):
    audit_insert(entity, entity_id, action, field, before, after, user)
