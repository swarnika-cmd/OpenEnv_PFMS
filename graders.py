"""
PFMS Graders - Task-specific grading functions.

Each grader takes a PFMSState and returns a float score strictly in (0, 1).
"""
from models import PFMSState

MAX_STEPS = 15


def _efficiency_bonus(step_count: int) -> float:
    """More steps = lower efficiency bonus. Returns value in [0, 0.2]."""
    if step_count <= 0:
        return 0.2
    ratio = max(0.0, 1.0 - (step_count / MAX_STEPS))
    return round(ratio * 0.2, 4)


def grade_happy_path(state: PFMSState) -> float:
    """
    Grade the happy_path task.
    Success: Agent completed 1 transfer of 15000 to 'vendor'.
    Score based on: completion + efficiency.
    """
    completed = any(
        r.get("amount") == 15000 and r.get("vendor") == "vendor"
        for r in state.database_records
    )

    if completed and state.done and state.reward > 0:
        # Successful completion
        score = 0.6 + _efficiency_bonus(state.step_count)
    elif completed:
        # Completed but maybe timed out or other issue
        score = 0.4
    elif state.logged_in:
        # Made progress (at least logged in)
        score = 0.15
    else:
        # No meaningful progress
        score = 0.05

    return max(0.01, min(0.99, score))


def grade_traffic_spike(state: PFMSState) -> float:
    """
    Grade the traffic_spike task.
    Success: Agent completed 3 transfers while handling 504 timeouts.
    Score based on: transfers completed + backoff handling + efficiency.
    """
    num_records = len(state.database_records)

    if num_records >= 3 and state.done and state.reward > 0:
        # Full success
        score = 0.6 + _efficiency_bonus(state.step_count)
    elif num_records >= 2:
        # Partial success (2 of 3 transfers)
        score = 0.4 + (num_records / 10.0)
    elif num_records >= 1:
        # At least 1 transfer
        score = 0.2 + (num_records / 10.0)
    elif state.http_status == 502:
        # Catastrophic crash (didn't wait for backoff)
        score = 0.05
    elif state.logged_in:
        score = 0.1
    else:
        score = 0.03

    return max(0.01, min(0.99, score))


def grade_lying_ui(state: PFMSState) -> float:
    """
    Grade the lying_ui task.
    Success: Agent verified transfer in ledger (not just trusting UI).
    Score based on: verification behavior + actual DB record + efficiency.
    """
    has_record = any(
        r.get("amount") == 15000 and r.get("vendor") == "vendor"
        for r in state.database_records
    )
    visited_ledger = (state.current_page == "ledger")

    if has_record and visited_ledger and state.done and state.reward > 0:
        # Full success: verified in ledger
        score = 0.6 + _efficiency_bonus(state.step_count)
    elif has_record and visited_ledger:
        # Record exists and checked ledger but episode didn't end cleanly
        score = 0.45
    elif has_record:
        # Record exists but never verified in ledger
        score = 0.3
    elif visited_ledger:
        # Checked ledger but no record (tried to verify, data was dropped)
        score = 0.2
    elif state.logged_in:
        score = 0.1
    else:
        score = 0.03

    return max(0.01, min(0.99, score))


# Lookup map for grader functions by task name
GRADERS = {
    "happy_path": grade_happy_path,
    "traffic_spike": grade_traffic_spike,
    "lying_ui": grade_lying_ui,
}


def grade(state: PFMSState) -> float:
    """
    Universal grader entry point.
    Routes to the appropriate task-specific grader based on state.task_name.
    Always returns a score strictly in (0, 1).
    """
    grader_fn = GRADERS.get(state.task_name, grade_happy_path)
    score = grader_fn(state)
    return max(0.01, min(0.99, score))
