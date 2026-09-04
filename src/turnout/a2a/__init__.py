"""Agent-to-Agent protocol: how departments in different organizations talk to each other.

Each department serves its own Coverage agent over A2A with a published AgentCard. A neighbour
discovers it, sends a structured coverage request, and reads back a structured offer. Nothing about
one department's roster is ever exposed to another.
"""
