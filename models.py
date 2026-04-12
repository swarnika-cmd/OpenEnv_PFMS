"""
PFMS Environment Models - Action, Observation, and State definitions.
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class PFMSAction(BaseModel):
    """Action for the PFMS environment."""
    command: str = Field(default="noop", description="'login', 'navigate', 'submit_transfer', 'noop'")
    target_page: Optional[str] = Field(default=None, description="'dashboard', 'fund_transfer', 'ledger'")
    amount: Optional[int] = Field(default=None)
    vendor: Optional[str] = Field(default=None)


class PFMSObservation(BaseModel):
    """Observation returned by the PFMS environment."""
    http_status: int = 200
    current_page: str = "login"
    simulated_ui_banner: Optional[str] = None
    database_records: Optional[List[Dict[str, Any]]] = None
    elapsed_time: int = 0
    error_message: Optional[str] = None


class PFMSState(BaseModel):
    """Internal state of the PFMS environment."""
    task_name: str = "happy_path"
    elapsed_time: int = 0
    current_page: str = "login"
    logged_in: bool = False
    database_records: List[Dict[str, Any]] = Field(default_factory=list)
    http_status: int = 200
    ui_banner: Optional[str] = None
    transfers_submitted: int = 0
    done: bool = False
    cooldown: int = 0
    reward: float = 0.0
    step_count: int = 0
    has_timed_out: bool = False
