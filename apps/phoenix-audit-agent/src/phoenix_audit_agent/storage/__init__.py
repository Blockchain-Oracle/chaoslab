"""Firestore-backed persistence for runs, agents, schedules and settings.

The live SSE path stays in-memory (main.py queues); this package is the
write-through index behind the audit registry / agents / monitoring UIs.
"""
