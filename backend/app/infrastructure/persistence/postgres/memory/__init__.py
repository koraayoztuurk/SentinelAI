"""PostgreSQL persistence owned by the Memory Service (ES-041).

ORM model, domain mapper and repository adapter for the versioned Memory
Item. PostgreSQL is the authoritative store (ADR-003); embedding and
Vector-Database synchronization are out of scope here (ADR-012, second
vertical slice).
"""
