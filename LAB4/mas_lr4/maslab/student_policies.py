"""Implement only the two policies below. Use Engine for ALL model/tool access.

Required interface:
  engine.run_role(role, instruction, max_turns=...) -> handoff dict
  engine.coordinator_decision(feedback) -> JSON action dict
  engine.finish() -> bool (real tests of current code)

Shared source lives in engine.code; pass verified handoff objects between roles.
Do not create a provider, call an API directly, edit data/tests or inject solutions.
See docs/IMPLEMENTATION.md. NotImplementedError is intentional, not a broken setup.
"""

def fixed(engine):
    """TODO: exactly programmer -> reviewer -> programmer; then verify.

    Reviewer has read/test permissions and returns a concrete review.
    The third stage must receive that review and current trusted test state.
    Early finish from a role ends only that stage, not the whole workflow.
    Keep the sequence fixed; do not add a coordinator or conditional role routing.
    """
    raise NotImplementedError('Implement the fixed workflow for ЛР4')

def coordinator(engine):
    """TODO: coordinator chooses developer/tester and when to finish.

    Validate {action:delegate, role:developer|tester, instruction:str} or
    {action:finish}. Reject extra/invalid fields, report an error to coordinator.
    Call run_role only for a valid delegation; return its verified handoff.
    Accept finish only when engine.finish() returns True; otherwise continue.
    Bound the routing loop; all calls share the episode token budget.
    """
    raise NotImplementedError('Implement the adaptive coordinator for ЛР4')
