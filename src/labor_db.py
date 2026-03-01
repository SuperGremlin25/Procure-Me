"""
Labor Database Module

Manages labor tasks, base rates, and equipment costs for OSP fiber construction.
All rates are sanitized to 0.00 - populate via user input or project settings.
"""

import pandas as pd
from typing import Dict, List, Optional
import json
import os


class LaborDatabase:
    """
    Database of standard labor tasks for OSP fiber construction projects.
    Separate from materials database for clear organization.
    """
    
    def __init__(self, data_file_path: str = None):
        """
        Initialize the labor database.
        
        Args:
            data_file_path: Path to the JSON file for persistence
        """
        self.data_file = data_file_path
        self.labor_tasks = self._load_labor_tasks()
    
    def _load_labor_tasks(self) -> List[Dict]:
        """
        Load labor tasks from file or use defaults.
        
        Returns:
            List of labor task dictionaries
        """
        if self.data_file and os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        return self._load_default_tasks()
    
    def _load_default_tasks(self) -> List[Dict]:
        """
        Load default labor tasks.
        All base_rate values are sanitized to 0.00.
        
        Returns:
            List of labor task dictionaries with name, unit, base_rate, category
        """
        tasks = [
            # ================================================================
            # UNDERGROUND CONSTRUCTION
            # ================================================================
            {"name": "Labor - Directional Bore", "unit": "FT", "base_rate": 0.00, "category": "Underground"},
            {"name": "Labor - Hand Dig Trench", "unit": "FT", "base_rate": 0.00, "category": "Underground"},
            {"name": "Labor - Mechanical Trench", "unit": "FT", "base_rate": 0.00, "category": "Underground"},
            {"name": "Labor - Cable Plow Single Pass", "unit": "FT", "base_rate": 0.00, "category": "Underground"},
            {"name": "Labor - Cable Plow with Conduit", "unit": "FT", "base_rate": 0.00, "category": "Underground"},
            {"name": "Labor - Plow Setup and Mobilization", "unit": "ea", "base_rate": 0.00, "category": "Underground"},
            {"name": "Labor - Conduit Install", "unit": "FT", "base_rate": 0.00, "category": "Underground"},
            {"name": "Labor - Cable Pull UG", "unit": "FT", "base_rate": 0.00, "category": "Underground"},
            {"name": "Labor - Innerduct Install", "unit": "FT", "base_rate": 0.00, "category": "Underground"},
            {"name": "Labor - Handhole Set and Level", "unit": "ea", "base_rate": 0.00, "category": "Underground"},
            {"name": "Labor - Handhole Excavation", "unit": "ea", "base_rate": 0.00, "category": "Underground"},
            {"name": "Labor - Backfill Handhole", "unit": "ea", "base_rate": 0.00, "category": "Underground"},
            {"name": "Labor - UG Conduit Stub Termination", "unit": "ea", "base_rate": 0.00, "category": "Underground"},
            
            # ================================================================
            # AERIAL CONSTRUCTION
            # ================================================================
            {"name": "Labor - Aerial Lashing", "unit": "FT", "base_rate": 0.00, "category": "Aerial"},
            {"name": "Labor - Strand Install", "unit": "FT", "base_rate": 0.00, "category": "Aerial"},
            {"name": "Labor - Aerial Cable Install", "unit": "FT", "base_rate": 0.00, "category": "Aerial"},
            {"name": "Labor - Guy Wire Install", "unit": "ea", "base_rate": 0.00, "category": "Aerial"},
            {"name": "Labor - Pole Attachment Install", "unit": "ea", "base_rate": 0.00, "category": "Aerial"},
            {"name": "Labor - Aerial Slack Loop", "unit": "ea", "base_rate": 0.00, "category": "Aerial"},
            {"name": "Labor - Riser Installation", "unit": "ea", "base_rate": 0.00, "category": "Aerial"},
            {"name": "Labor - Dead End Install", "unit": "ea", "base_rate": 0.00, "category": "Aerial"},
            
            # ================================================================
            # SPLICING AND TERMINATION
            # ================================================================
            {"name": "Labor - Fusion Splice Per Fiber", "unit": "ea", "base_rate": 0.00, "category": "Splicing"},
            {"name": "Labor - Mechanical Splice Per Fiber", "unit": "ea", "base_rate": 0.00, "category": "Splicing"},
            {"name": "Labor - Splice Closure Install", "unit": "ea", "base_rate": 0.00, "category": "Splicing"},
            {"name": "Labor - Splice Tray Setup", "unit": "ea", "base_rate": 0.00, "category": "Splicing"},
            {"name": "Labor - Fiber Preparation and Strip", "unit": "ea", "base_rate": 0.00, "category": "Splicing"},
            {"name": "Labor - Splice Closure Aerial Mount", "unit": "ea", "base_rate": 0.00, "category": "Splicing"},
            {"name": "Labor - Splice Closure UG Install", "unit": "ea", "base_rate": 0.00, "category": "Splicing"},
            {"name": "Labor - Pigtail Splice and Dress", "unit": "ea", "base_rate": 0.00, "category": "Splicing"},
            {"name": "Labor - Connector Installation SC-APC", "unit": "ea", "base_rate": 0.00, "category": "Splicing"},
            {"name": "Labor - Connector Installation LC-UPC", "unit": "ea", "base_rate": 0.00, "category": "Splicing"},
            
            # ================================================================
            # TESTING AND CERTIFICATION
            # ================================================================
            {"name": "Labor - OTDR Test Per Fiber", "unit": "ea", "base_rate": 0.00, "category": "Testing"},
            {"name": "Labor - Power Meter Test Per Fiber", "unit": "ea", "base_rate": 0.00, "category": "Testing"},
            {"name": "Labor - Visual Fault Locator Test", "unit": "ea", "base_rate": 0.00, "category": "Testing"},
            {"name": "Labor - End Face Inspection", "unit": "ea", "base_rate": 0.00, "category": "Testing"},
            {"name": "Labor - Fiber Identifier Test", "unit": "ea", "base_rate": 0.00, "category": "Testing"},
            {"name": "Labor - Test Report Generation", "unit": "hr", "base_rate": 0.00, "category": "Testing"},
            {"name": "Labor - As-Built Documentation", "unit": "hr", "base_rate": 0.00, "category": "Testing"},
            
            # ================================================================
            # INFRASTRUCTURE INSTALLATION
            # ================================================================
            {"name": "Labor - Pedestal Install", "unit": "ea", "base_rate": 0.00, "category": "Infrastructure"},
            {"name": "Labor - Cabinet Install FDH", "unit": "ea", "base_rate": 0.00, "category": "Infrastructure"},
            {"name": "Labor - Cabinet Install FAP", "unit": "ea", "base_rate": 0.00, "category": "Infrastructure"},
            {"name": "Labor - Splitter Install 1x8", "unit": "ea", "base_rate": 0.00, "category": "Infrastructure"},
            {"name": "Labor - Splitter Install 1x16", "unit": "ea", "base_rate": 0.00, "category": "Infrastructure"},
            {"name": "Labor - Splitter Install 1x32", "unit": "ea", "base_rate": 0.00, "category": "Infrastructure"},
            {"name": "Labor - Fiber Patch Panel Mount", "unit": "ea", "base_rate": 0.00, "category": "Infrastructure"},
            {"name": "Labor - Patch Cord Dress and Route", "unit": "ea", "base_rate": 0.00, "category": "Infrastructure"},
            
            # ================================================================
            # CONCRETE WORK
            # ================================================================
            {"name": "Labor - Concrete Pad Excavation 4x4", "unit": "ea", "base_rate": 0.00, "category": "Concrete"},
            {"name": "Labor - Concrete Pad Form Set 4x4", "unit": "ea", "base_rate": 0.00, "category": "Concrete"},
            {"name": "Labor - Concrete Pad Rebar Tie 4x4", "unit": "ea", "base_rate": 0.00, "category": "Concrete"},
            {"name": "Labor - Concrete Pad Pour and Finish 4x4", "unit": "ea", "base_rate": 0.00, "category": "Concrete"},
            {"name": "Labor - Concrete Pad Full Set 4x4x4in", "unit": "ea", "base_rate": 0.00, "category": "Concrete"},
            {"name": "Labor - Fiber Cabinet Set on Pad", "unit": "ea", "base_rate": 0.00, "category": "Concrete"},
            {"name": "Labor - Fiber Cabinet Anchor Bolt Torque", "unit": "ea", "base_rate": 0.00, "category": "Concrete"},
            {"name": "Labor - Conduit Stub-Up Through Pad", "unit": "ea", "base_rate": 0.00, "category": "Concrete"},
            {"name": "Labor - Gravel Base Prep and Compact", "unit": "CY", "base_rate": 0.00, "category": "Concrete"},
            
            # ================================================================
            # RESTORATION AND CLEANUP
            # ================================================================
            {"name": "Labor - Hardscape Concrete Repair Municipal", "unit": "FT", "base_rate": 0.00, "category": "Restoration"},
            {"name": "Labor - Sidewalk Concrete Repair Per FT", "unit": "FT", "base_rate": 0.00, "category": "Restoration"},
            {"name": "Labor - Curb and Gutter Repair Per FT", "unit": "FT", "base_rate": 0.00, "category": "Restoration"},
            {"name": "Labor - Asphalt Cut and Patch Per FT", "unit": "FT", "base_rate": 0.00, "category": "Restoration"},
            {"name": "Labor - Saw Cut Concrete Per FT", "unit": "FT", "base_rate": 0.00, "category": "Restoration"},
            {"name": "Labor - Landscape Restoration", "unit": "SY", "base_rate": 0.00, "category": "Restoration"},
            {"name": "Labor - Sod Replacement", "unit": "SY", "base_rate": 0.00, "category": "Restoration"},
            {"name": "Labor - Erosion Control Install", "unit": "FT", "base_rate": 0.00, "category": "Restoration"},
            {"name": "Labor - Site Cleanup Per Day", "unit": "day", "base_rate": 0.00, "category": "Restoration"},
            
            # ================================================================
            # DROP INSTALLATION
            # ================================================================
            {"name": "Labor - NID Install Indoor", "unit": "ea", "base_rate": 0.00, "category": "Drops"},
            {"name": "Labor - NID Install Outdoor", "unit": "ea", "base_rate": 0.00, "category": "Drops"},
            {"name": "Labor - Drop Install Aerial", "unit": "ea", "base_rate": 0.00, "category": "Drops"},
            {"name": "Labor - Drop Install UG", "unit": "ea", "base_rate": 0.00, "category": "Drops"},
            {"name": "Labor - Drop Cable Slack Storage", "unit": "ea", "base_rate": 0.00, "category": "Drops"},
            {"name": "Labor - Drop Fiber Terminate", "unit": "ea", "base_rate": 0.00, "category": "Drops"},
            {"name": "Labor - Drop Test and Activate", "unit": "ea", "base_rate": 0.00, "category": "Drops"},
            {"name": "Labor - Pre-Conn Drop Install", "unit": "ea", "base_rate": 0.00, "category": "Drops"},
            
            # ================================================================
            # GROUNDING AND BONDING
            # ================================================================
            {"name": "Labor - Ground Rod Install", "unit": "ea", "base_rate": 0.00, "category": "Grounding"},
            {"name": "Labor - Ground Wire Install", "unit": "FT", "base_rate": 0.00, "category": "Grounding"},
            {"name": "Labor - Ground Lug Attach", "unit": "ea", "base_rate": 0.00, "category": "Grounding"},
            {"name": "Labor - Cabinet Ground Bar Install", "unit": "ea", "base_rate": 0.00, "category": "Grounding"},
            {"name": "Labor - Strand Grounding", "unit": "ea", "base_rate": 0.00, "category": "Grounding"},
            {"name": "Labor - Splice Closure Grounding", "unit": "ea", "base_rate": 0.00, "category": "Grounding"},
            
            # ================================================================
            # TRAFFIC CONTROL AND SAFETY
            # ================================================================
            {"name": "Labor - Traffic Control Setup", "unit": "day", "base_rate": 0.00, "category": "Safety"},
            {"name": "Labor - Flagging Service Per Hour", "unit": "hr", "base_rate": 0.00, "category": "Safety"},
            {"name": "Labor - Lane Closure Setup", "unit": "ea", "base_rate": 0.00, "category": "Safety"},
            {"name": "Labor - Safety Barricade Placement", "unit": "ea", "base_rate": 0.00, "category": "Safety"},
            {"name": "Labor - Warning Tape Install", "unit": "FT", "base_rate": 0.00, "category": "Safety"},
            
            # ================================================================
            # PROJECT MANAGEMENT AND ENGINEERING
            # ================================================================
            {"name": "Labor - Project Manager Per Day", "unit": "day", "base_rate": 0.00, "category": "Management"},
            {"name": "Labor - Foreman Per Day", "unit": "day", "base_rate": 0.00, "category": "Management"},
            {"name": "Labor - Engineer Site Visit", "unit": "hr", "base_rate": 0.00, "category": "Management"},
            {"name": "Labor - QC Inspector Per Day", "unit": "day", "base_rate": 0.00, "category": "Management"},
            {"name": "Labor - Safety Officer Per Day", "unit": "day", "base_rate": 0.00, "category": "Management"},
            
            # ================================================================
            # EQUIPMENT AND MOBILIZATION
            # ================================================================
            {"name": "Equipment - Boring Machine Per Day", "unit": "day", "base_rate": 0.00, "category": "Equipment"},
            {"name": "Equipment - Trencher Per Day", "unit": "day", "base_rate": 0.00, "category": "Equipment"},
            {"name": "Equipment - Cable Plow Per Day", "unit": "day", "base_rate": 0.00, "category": "Equipment"},
            {"name": "Equipment - Excavator Per Day", "unit": "day", "base_rate": 0.00, "category": "Equipment"},
            {"name": "Equipment - Bucket Truck Per Day", "unit": "day", "base_rate": 0.00, "category": "Equipment"},
            {"name": "Equipment - Fusion Splicer Per Day", "unit": "day", "base_rate": 0.00, "category": "Equipment"},
            {"name": "Equipment - OTDR Per Day", "unit": "day", "base_rate": 0.00, "category": "Equipment"},
            {"name": "Equipment - Lashing Machine Per Day", "unit": "day", "base_rate": 0.00, "category": "Equipment"},
            {"name": "Equipment - Service Truck Per Day", "unit": "day", "base_rate": 0.00, "category": "Equipment"},
            {"name": "Equipment - Trailer Mounted Reel Stands", "unit": "day", "base_rate": 0.00, "category": "Equipment"},
            {"name": "Mobilization - Equipment to Site", "unit": "ea", "base_rate": 0.00, "category": "Equipment"},
            {"name": "Demobilization - Equipment from Site", "unit": "ea", "base_rate": 0.00, "category": "Equipment"},
        ]
        
        return tasks
    
    def get_tasks_by_category(self) -> Dict[str, List[Dict]]:
        """
        Group labor tasks by category.
        
        Returns:
            Dictionary mapping categories to task lists
        """
        categories = {}
        for task in self.labor_tasks:
            category = task.get('category', 'Other')
            if category not in categories:
                categories[category] = []
            categories[category].append(task)
        
        return categories
    
    def get_task_names(self) -> List[str]:
        """
        Get list of all task names.
        
        Returns:
            List of task names
        """
        return [t['name'] for t in self.labor_tasks]
    
    def find_task(self, name: str) -> Optional[Dict]:
        """
        Find a task by name.
        
        Args:
            name: Task name to search for
            
        Returns:
            Task dictionary or None if not found
        """
        for task in self.labor_tasks:
            if task['name'].lower() == name.lower():
                return task
        return None
    
    def add_task(self, name: str, unit: str = "ea", base_rate: float = 0.0, category: str = "Other"):
        """
        Add a new labor task to the database.
        
        Args:
            name: Task name
            unit: Unit of measure
            base_rate: Base rate per unit
            category: Task category
        """
        task = {
            "name": name,
            "unit": unit,
            "base_rate": base_rate,
            "category": category
        }
        self.labor_tasks.append(task)
        self.save()
    
    def update_task(self, name: str, **kwargs):
        """
        Update an existing task.
        
        Args:
            name: Task name to update
            **kwargs: Fields to update (unit, base_rate, category)
        """
        for task in self.labor_tasks:
            if task['name'] == name:
                for key, value in kwargs.items():
                    if key in task:
                        task[key] = value
                self.save()
                break
    
    def delete_task(self, name: str):
        """
        Delete a task from the database.
        
        Args:
            name: Task name to delete
        """
        self.labor_tasks = [t for t in self.labor_tasks if t['name'] != name]
        self.save()
    
    def save(self):
        """Save the labor database to file."""
        if not self.data_file:
            return
        try:
            with open(self.data_file, 'w') as f:
                json.dump(self.labor_tasks, f, indent=2)
        except:
            pass
    
    def to_dataframe(self, columns: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Convert labor database to DataFrame.
        
        Args:
            columns: Optional list of columns to include
            
        Returns:
            DataFrame with labor task data
        """
        df = pd.DataFrame(self.labor_tasks)
        
        if columns:
            df = df[columns]
        
        return df
