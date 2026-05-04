"""
Labor Database Module

Manages standard labor rates and tasks for underground OSP projects.
Standalone module - no external src dependencies.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class LaborTask:
    """A standard labor task with rate and time estimate."""
    task_id: str
    description: str
    unit: str
    unit_rate: float
    crew_size: int = 1
    category: str = "General"


class LaborDatabase:
    """
    Database of standard labor tasks and rates for underground OSP projects.
    """

    DEFAULT_TASKS: List[Dict] = [
        # Pole work
        {"task_id": "POLE-SET", "description": "Set utility pole", "unit": "EA", "unit_rate": 850.00, "crew_size": 4, "category": "Pole"},
        {"task_id": "POLE-RM", "description": "Remove existing pole", "unit": "EA", "unit_rate": 450.00, "crew_size": 3, "category": "Pole"},
        {"task_id": "POLE-FRAMING", "description": "Frame pole (crossarms, hardware)", "unit": "EA", "unit_rate": 275.00, "crew_size": 2, "category": "Pole"},
        {"task_id": "POLE-GROUND", "description": "Ground pole", "unit": "EA", "unit_rate": 125.00, "crew_size": 1, "category": "Pole"},
        # Comm move
        {"task_id": "COMM-MOVE-LV", "description": "Move comm attachments - low voltage", "unit": "EA", "unit_rate": 350.00, "crew_size": 2, "category": "Comm Move"},
        {"task_id": "COMM-MOVE-HV", "description": "Move comm attachments - high voltage", "unit": "EA", "unit_rate": 550.00, "crew_size": 3, "category": "Comm Move"},
        {"task_id": "COMM-TRANSFER", "description": "Transfer equipment pole to pole", "unit": "EA", "unit_rate": 425.00, "crew_size": 2, "category": "Comm Move"},
        # Underground
        {"task_id": "TRENCH-OPEN", "description": "Open trench", "unit": "FT", "unit_rate": 8.50, "crew_size": 2, "category": "Underground"},
        {"task_id": "TRENCH-CLOSE", "description": "Close and restore trench", "unit": "FT", "unit_rate": 6.00, "crew_size": 2, "category": "Underground"},
        {"task_id": "BORE-INSTALL", "description": "Directional bore installation", "unit": "FT", "unit_rate": 22.00, "crew_size": 3, "category": "Underground"},
        {"task_id": "CONDUIT-PULL", "description": "Pull cable through conduit", "unit": "FT", "unit_rate": 1.25, "crew_size": 2, "category": "Underground"},
        # Fiber
        {"task_id": "FIBER-SPLICE", "description": "Fiber splice (fusion)", "unit": "EA", "unit_rate": 45.00, "crew_size": 1, "category": "Fiber"},
        {"task_id": "FIBER-HANG", "description": "Hang aerial fiber cable", "unit": "FT", "unit_rate": 1.75, "crew_size": 2, "category": "Fiber"},
        {"task_id": "FIBER-BURY", "description": "Bury fiber cable (direct)", "unit": "FT", "unit_rate": 4.50, "crew_size": 2, "category": "Fiber"},
        {"task_id": "CLOSURE-INSTALL", "description": "Install fiber closure", "unit": "EA", "unit_rate": 185.00, "crew_size": 1, "category": "Fiber"},
        # General
        {"task_id": "INSPECT", "description": "Site inspection", "unit": "HR", "unit_rate": 95.00, "crew_size": 1, "category": "General"},
        {"task_id": "TRAFFIC-CTRL", "description": "Traffic control setup/teardown", "unit": "DAY", "unit_rate": 650.00, "crew_size": 2, "category": "General"},
        {"task_id": "PERMIT", "description": "Permit acquisition and management", "unit": "EA", "unit_rate": 250.00, "crew_size": 1, "category": "General"},
        {"task_id": "RESTORATION", "description": "Site restoration / cleanup", "unit": "HR", "unit_rate": 85.00, "crew_size": 2, "category": "General"},
    ]

    def __init__(self):
        self.tasks: List[Dict] = self.DEFAULT_TASKS.copy()
        self._index: Dict[str, Dict] = {t["task_id"]: t for t in self.tasks}

    def get_task(self, task_id: str) -> Optional[Dict]:
        return self._index.get(task_id)

    def get_tasks_by_category(self, category: str) -> List[Dict]:
        return [t for t in self.tasks if t["category"].lower() == category.lower()]

    def all_tasks(self) -> List[Dict]:
        return self.tasks

    def as_dataframe(self):
        import pandas as pd
        return pd.DataFrame(self.tasks)
