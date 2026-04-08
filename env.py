import os
import random
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

# -----------------
# Pydantic Models for State & Actions
# -----------------

class Observation(BaseModel):
    http_status: int = Field(description="HTTP status code from the server (e.g., 200, 502, 504).")
    current_page: str = Field(description="The current page the agent is on in the portal.")
    simulated_ui_banner: Optional[str] = Field(None, description="Any success/error banners shown in the UI.")
    database_records: Optional[List[Dict[str, Any]]] = Field(None, description="The list of ledger records, only visible on the Ledger page.")
    elapsed_time: int = Field(description="Simulated elapsed time since the task started, in seconds.")
    error_message: Optional[str] = Field(None, description="Internal error messaging for the agent.")

class Action(BaseModel):
    command: str = Field(description="The action to perform: 'login', 'navigate', 'submit_transfer', 'noop'")
    target_page: Optional[str] = Field(None, description="The page to go to if command is 'navigate' ('dashboard', 'fund_transfer', 'ledger').")
    amount: Optional[int] = Field(None, description="The amount to transfer if command is 'submit_transfer'.")
    vendor: Optional[str] = Field(None, description="The recipient vendor name if command is 'submit_transfer'.")

class StepResult(BaseModel):
    observation: Observation
    reward: float
    done: bool

class ResetResult(BaseModel):
    observation: Observation

# -----------------
# The PFMS Environment
# -----------------
class PFMSEnv:
    def __init__(self):
        self.task_name = os.getenv("PFMS_TASK", "happy_path") # "happy_path", "traffic_spike", "lying_ui"
        self.elapsed_time = 0
        self.current_page = "login"
        self.logged_in = False
        self.database_records = []
        self.http_status = 200
        self.ui_banner = None
        self.transfers_submitted = 0 
        self.done = False
        self.cooldown = 0  # To track 504 timeouts
        
    async def reset(self) -> ResetResult:
        self.elapsed_time = 0
        self.current_page = "login"
        self.logged_in = False
        self.database_records = []
        self.http_status = 200
        self.ui_banner = None
        self.transfers_submitted = 0
        self.done = False
        self.cooldown = 0
        
        obs = self._get_observation()
        return ResetResult(observation=obs)

    def _get_observation(self) -> Observation:
        records = self.database_records if self.current_page == "ledger" else None
        return Observation(
            http_status=self.http_status,
            current_page=self.current_page,
            simulated_ui_banner=self.ui_banner,
            database_records=records,
            elapsed_time=self.elapsed_time,
            error_message=None
        )

    async def step(self, action: Action) -> StepResult:
        if self.done:
            return StepResult(observation=self._get_observation(), reward=0.0, done=True)
            
        reward = -0.01  # Time-cost terminator!
        self.elapsed_time += 1
        self.ui_banner = None
        self.http_status = 200

        cmd = action.command.lower()

        # Handle time progression / cooldown
        if self.cooldown > 0:
            if cmd == "noop":
                self.cooldown -= 1
                # Still charging them time for waiting
                # if cooled down, site works again
                if self.cooldown == 0:
                    self.http_status = 200
                else:
                    self.http_status = 504
                return StepResult(observation=self._get_observation(), reward=reward, done=self.done)
            else:
                # Catastrophic failure for not using backoff
                self.http_status = 502 # Crashed the site!
                self.ui_banner = "CATASTROPHIC SERVER CRASH (502 Bad Gateway)"
                self.done = True
                return StepResult(observation=self._get_observation(), reward=-10.0, done=True)

        if cmd == "noop":
            # Just wasting time without a cooldown
            pass
            
        elif cmd == "login":
            self.logged_in = True
            self.current_page = "dashboard"
            self.ui_banner = "Login Successful. Note: Session expires soon."
            
        elif cmd == "navigate":
            if not self.logged_in:
                self.ui_banner = "Error: Not logged in."
                self.http_status = 401
            else:
                valid_pages = ["dashboard", "fund_transfer", "ledger"]
                if action.target_page in valid_pages:
                    self.current_page = action.target_page
                    if self.current_page == "ledger":
                        self.ui_banner = "Loaded ledger records."
                else:
                    self.ui_banner = "Error: Page not found."
                    self.http_status = 404
                    
        elif cmd == "submit_transfer":
            if not self.logged_in or self.current_page != "fund_transfer":
                self.ui_banner = "Error: Must be logged in and on the fund_transfer page."
                self.http_status = 401
            elif not action.amount or not action.vendor:
                self.ui_banner = "Error: amount and vendor are required for submitting transfer."
                self.http_status = 400
            else:
                self.transfers_submitted += 1
                
                # --- Task Logic Injectors ---
                if self.task_name == "traffic_spike" and self.transfers_submitted == 2:
                    # Throw a 504 on the second transfer!
                    self.http_status = 504
                    self.ui_banner = "504 Gateway Timeout: Server too busy."
                    self.cooldown = 2 # Need to NoOp for 2 steps
                    self.transfers_submitted -= 1 # didn't actually go through
                
                elif self.task_name == "lying_ui":
                    # Pretend it worked!
                    self.ui_banner = f"Success: Funds ({action.amount}) Transferred to {action.vendor}."
                    self.http_status = 200
                    # But randomly silently fail the database insertion 
                    if random.random() < 0.6: 
                        # Silently omitted from database!
                        pass
                    else:
                        self.database_records.append({"vendor": action.vendor, "amount": action.amount, "status": "processed"})
                        
                else:
                    # Happy path (or traffic spike successful insert)
                    self.database_records.append({"vendor": action.vendor, "amount": action.amount, "status": "processed"})
                    self.ui_banner = f"Success: Funds ({action.amount}) Transferred to {action.vendor}."
                    self.http_status = 200
                    
        else:
            self.ui_banner = f"Unknown command: {cmd}"
            self.http_status = 400

        # Win conditions check
        won = self._check_win_condition()
        if won:
            self.done = True
            reward += 1.0 # Big success payout!
            self.ui_banner = "ALL TASKS COMPLETED SUCCESSFULLY!"
            
        return StepResult(observation=self._get_observation(), reward=reward, done=self.done)
        
    def _check_win_condition(self) -> bool:
        if self.task_name == "happy_path":
            # Just successfully do 1 transfer
            return any(r["amount"] == 15000 and r["vendor"] == "vendor" for r in self.database_records)
            
        elif self.task_name == "traffic_spike":
            # Successfully do 3 transfers
            return len(self.database_records) == 3
            
        elif self.task_name == "lying_ui":
            # Must verify it is in the ledger!
            has_record = any(r["amount"] == 15000 and r["vendor"] == "vendor" for r in self.database_records)
            if has_record and self.current_page == "ledger":
                 return True
        return False
        
    async def close(self):
        # OpenEnv inference scripts usually call close() at the end
        pass
        
    @classmethod
    async def from_docker_image(cls, image_name: str = None):
        # We simulate the interface by returning an instance
        return cls()
