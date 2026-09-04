"""Strands tools. Each is a typed function with a docstring; Strands derives the tool schema from it.

Tools reach the store, clock, and channels through turnout.runtime.get(). They never call a model.
"""
