"""
PFMS Environment - Core environment logic.
"""
import os
import sys
import random
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import PFMSAction, PFMSObservation, PFMSState
from graders import grade as _grade_fn


class PFMSEnvironment:
    """
    Mock PFMS (Public Financial Management System) environment.

    Tasks:
    - happy_path (easy): Basic login + navigation + transfer
    - traffic_spike (medium): Handle 504 timeouts with backoff
    - lying_ui (hard): UI lies about success, must verify in ledger
    """

    def __init__(self):
        self._task_name = os.getenv("PFMS_TASK", "happy_path")
        self._state = PFMSState(task_name=self._task_name)

    def reset(self) -> PFMSObservation:
        self._state = PFMSState(task_name=self._task_name)
        return self._get_observation()

    def step(self, action: PFMSAction) -> dict:
        if self._state.done:
            return {"observation": self._get_observation().model_dump(), "reward": 0.0, "done": True}

        self._state.elapsed_time += 1
        self._state.ui_banner = None
        self._state.http_status = 200
        self._state.step_count += 1

        cmd = action.command.lower() if action.command else "noop"

        # Handle cooldown (server busy)
        if self._state.cooldown > 0:
            if cmd == "noop":
                self._state.cooldown -= 1
                if self._state.cooldown == 0:
                    self._state.http_status = 200
                else:
                    self._state.http_status = 504
                reward = -0.01
                return {"observation": self._get_observation().model_dump(), "reward": reward, "done": self._state.done}
            else:
                self._state.http_status = 502
                self._state.ui_banner = "CATASTROPHIC SERVER CRASH (502 Bad Gateway)"
                self._state.done = True
                return {"observation": self._get_observation().model_dump(), "reward": -10.0, "done": True}

        if cmd == "noop":
            pass
        elif cmd == "login":
            self._state.logged_in = True
            self._state.current_page = "dashboard"
            self._state.ui_banner = "Login Successful. Note: Session expires soon."
        elif cmd == "navigate":
            if not self._state.logged_in:
                self._state.ui_banner = "Error: Not logged in."
                self._state.http_status = 401
            else:
                valid_pages = ["dashboard", "fund_transfer", "ledger"]
                if action.target_page in valid_pages:
                    self._state.current_page = action.target_page
                    if self._state.current_page == "ledger":
                        self._state.ui_banner = "Loaded ledger records."
                else:
                    self._state.ui_banner = "Error: Page not found."
                    self._state.http_status = 404
        elif cmd == "submit_transfer":
            if not self._state.logged_in or self._state.current_page != "fund_transfer":
                self._state.ui_banner = "Error: Must be logged in and on the fund_transfer page."
                self._state.http_status = 401
            elif not action.amount or not action.vendor:
                self._state.ui_banner = "Error: amount and vendor are required."
                self._state.http_status = 400
            else:
                self._state.transfers_submitted += 1
                if self._task_name == "traffic_spike" and self._state.transfers_submitted == 2 and not getattr(self._state, "has_timed_out", False):
                    self._state.http_status = 504
                    self._state.ui_banner = "504 Gateway Timeout: Server too busy."
                    self._state.cooldown = 2
                    # We flag that the timeout event occurred so we don't infinitely trigger it
                    self._state.has_timed_out = True
                    self._state.transfers_submitted -= 1
                elif self._task_name == "lying_ui":
                    self._state.ui_banner = f"Success: Funds ({action.amount}) Transferred to {action.vendor}."
                    self._state.http_status = 200
                    if random.random() < 0.6:
                        pass  # Silently dropped
                    else:
                        self._state.database_records.append(
                            {"vendor": action.vendor, "amount": action.amount, "status": "processed"}
                        )
                else:
                    self._state.database_records.append(
                        {"vendor": action.vendor, "amount": action.amount, "status": "processed"}
                    )
                    self._state.ui_banner = f"Success: Funds ({action.amount}) Transferred to {action.vendor}."
                    self._state.http_status = 200
        else:
            self._state.ui_banner = f"Unknown command: {cmd}"
            self._state.http_status = 400

        reward = -0.01
        won = self._check_win_condition()
        if won:
            self._state.done = True
            reward += 1.0
            self._state.ui_banner = "ALL TASKS COMPLETED SUCCESSFULLY!"

        self._state.reward = reward
        return {"observation": self._get_observation().model_dump(), "reward": reward, "done": self._state.done}

    @property
    def state(self) -> PFMSState:
        return self._state

    def _get_observation(self) -> PFMSObservation:
        records = self._state.database_records if self._state.current_page == "ledger" else None
        return PFMSObservation(
            http_status=self._state.http_status,
            current_page=self._state.current_page,
            simulated_ui_banner=self._state.ui_banner,
            database_records=records,
            elapsed_time=self._state.elapsed_time,
            error_message=None,
        )

    def _check_win_condition(self) -> bool:
        if self._task_name == "happy_path":
            return any(
                r["amount"] == 15000 and r["vendor"] == "vendor"
                for r in self._state.database_records
            )
        elif self._task_name == "traffic_spike":
            return len(self._state.database_records) == 3
        elif self._task_name == "lying_ui":
            has_record = any(
                r["amount"] == 15000 and r["vendor"] == "vendor"
                for r in self._state.database_records
            )
            if has_record and self._state.current_page == "ledger":
                return True
        return False

    def grade(self) -> float:
        """
        Return a normalized score for the current episode strictly in (0, 1).
        Delegates to the task-specific grader.
        """
        return _grade_fn(self._state)

    async def close(self):
        pass
