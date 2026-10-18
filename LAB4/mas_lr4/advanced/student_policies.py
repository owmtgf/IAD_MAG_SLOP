"""Implement the two MAS with the same Engine interface as the main lab.

All model calls and tools must go through engine. Each role has its own history;
all roles share one budget. Do not read hidden/reference or another scheme.
"""
def fixed(engine):
    """Programmer -> reviewer -> programmer, pass real handoffs and verify."""
    raise NotImplementedError('Implement fixed workflow for advanced tasks')

def coordinator(engine):
    """Validate delegate/finish decisions; developer edits, tester inspects."""
    raise NotImplementedError('Implement adaptive coordinator for advanced tasks')
