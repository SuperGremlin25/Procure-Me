"""
Remedy Action Mapper Module

Maps remedy actions to materials and labor requirements.
Generates bids from spatially joined GIS data.
"""

import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from .materials_db import MaterialsDatabase
from .labor_db import LaborDatabase


class ActionCategory(Enum):
    COMM_MOVE = "comm_move"
    POLE_REPLACE = "pole_replace"
    ATTACH = "attach"
    DETACH = "detach"
    RELOCATE = "relocate"
    INSPECT = "inspect"
    MAINTAIN = "maintain"


@dataclass
class MaterialRequirement:
    material_id: str
    description: str
    quantity: float
    unit: str
    unit_cost: float
    category: str
    notes: Optional[str] = None


@dataclass
class LaborRequirement:
    task_type: str
    description: str
    hours: float
    rate: float
    crew_size: int = 1
    notes: Optional[str] = None


class RemedyActionMapper:
    """Maps remedy actions to materials and labor, generates bids."""

    def __init__(self):
        self.materials_db = MaterialsDatabase()
        self.labor_db = LaborDatabase()

    def map_action_to_requirements(
        self,
        action_type: str,
        attachment_height: Optional[float] = None
    ) -> Tuple[List[MaterialRequirement], List[LaborRequirement]]:
        """Map a remedy action to required materials and labor."""
        materials = []
        labor = []

        action_upper = action_type.upper().strip()

        if action_upper == "COMM_MOVE":
            materials.append(MaterialRequirement(
                material_id="BDI213OR-T10",
                description="2\" HDPE Conduit - Orange",
                quantity=50,
                unit="FT",
                unit_cost=0.83,
                category="Conduit"
            ))
            materials.append(MaterialRequirement(
                material_id="FIBER-12SM",
                description="12-Strand Single Mode Fiber",
                quantity=100,
                unit="FT",
                unit_cost=0.45,
                category="Fiber Cable"
            ))
            labor.append(LaborRequirement(
                task_type="COMM-MOVE-LV",
                description="Move comm attachments",
                hours=4.0,
                rate=87.50,
                crew_size=2
            ))

        elif action_upper == "POLE_REPLACE":
            materials.append(MaterialRequirement(
                material_id="POLE-40CL1",
                description="40ft Class 1 Utility Pole",
                quantity=1,
                unit="EA",
                unit_cost=850.00,
                category="Pole"
            ))
            labor.append(LaborRequirement(
                task_type="POLE-SET",
                description="Set utility pole",
                hours=8.0,
                rate=106.25,
                crew_size=4
            ))
            labor.append(LaborRequirement(
                task_type="POLE-RM",
                description="Remove existing pole",
                hours=4.0,
                rate=112.50,
                crew_size=3
            ))

        elif action_upper in ("ATTACH", "DETACH"):
            labor.append(LaborRequirement(
                task_type="COMM-TRANSFER",
                description="Transfer equipment",
                hours=3.0,
                rate=141.67,
                crew_size=2
            ))

        elif action_upper in ("INSPECT", "MAINTAIN"):
            labor.append(LaborRequirement(
                task_type="INSPECT",
                description="Site inspection",
                hours=2.0,
                rate=95.00,
                crew_size=1
            ))

        return materials, labor

    def generate_bid_from_joined_gdf(
        self,
        joined_gdf,
        margin_rate: float = 0.10,
        tax_rate: float = 0.0825
    ) -> Dict[str, Any]:
        """Generate a bid from a spatially joined GeoDataFrame."""
        all_materials = []
        all_labor = []
        detailed_items = []

        for _, row in joined_gdf.iterrows():
            action_type = row.get("action_type")
            if pd.isna(action_type):
                continue

            materials, labor = self.map_action_to_requirements(str(action_type))
            all_materials.extend(materials)
            all_labor.extend(labor)

            detailed_items.append({
                "pole_id": row.get("pole_id", "Unknown"),
                "action_type": str(action_type),
                "materials_count": len(materials),
                "labor_tasks": len(labor)
            })

        materials_subtotal = sum(m.quantity * m.unit_cost for m in all_materials)
        labor_subtotal = sum(l.hours * l.rate for l in all_labor)
        subtotal = materials_subtotal + labor_subtotal
        margin = subtotal * margin_rate
        tax = (subtotal + margin) * tax_rate
        total = subtotal + margin + tax

        return {
            "cost_breakdown": {
                "materials_subtotal": round(materials_subtotal, 2),
                "labor_subtotal": round(labor_subtotal, 2),
                "subtotal": round(subtotal, 2),
                "margin": round(margin, 2),
                "tax": round(tax, 2),
                "total": round(total, 2)
            },
            "detailed_items": detailed_items,
            "material_count": len(all_materials),
            "labor_task_count": len(all_labor)
        }

    def estimate_project_timeline(self, joined_gdf) -> Dict[str, Any]:
        """Estimate project timeline from joined data."""
        action_count = len(joined_gdf) if joined_gdf is not None else 0
        total_hours = action_count * 4
        crew_count = 2
        working_days = max(1, total_hours / (8 * crew_count))

        return {
            "total_actions": action_count,
            "estimated_hours": total_hours,
            "crew_count": crew_count,
            "estimated_working_days": round(working_days, 1),
            "estimated_calendar_days": round(working_days * 1.4, 1)
        }
