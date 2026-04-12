"""
PFMS Environment Client - EnvClient implementation for training/inference.
"""
from openenv.core import EnvClient, StepResult

from .models import PFMSAction, PFMSObservation, PFMSState


class PFMSEnv(EnvClient[PFMSAction, PFMSObservation, PFMSState]):
    """Client for interacting with the PFMS environment."""

    def _step_payload(self, action: PFMSAction) -> dict:
        payload = {"command": action.command}
        if action.target_page is not None:
            payload["target_page"] = action.target_page
        if action.amount is not None:
            payload["amount"] = action.amount
        if action.vendor is not None:
            payload["vendor"] = action.vendor
        return payload

    def _parse_result(self, payload: dict) -> StepResult[PFMSObservation]:
        obs = PFMSObservation(**payload["observation"])
        return StepResult(
            observation=obs,
            reward=payload.get("reward"),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: dict) -> PFMSState:
        return PFMSState(**payload)
