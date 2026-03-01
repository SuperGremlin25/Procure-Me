"""
Materials Database Module

Manages the master list of materials for underground BOM.
"""

import pandas as pd
from typing import Dict, List, Optional
import json
import os


class MaterialsDatabase:
    """
    Database of standard materials for underground OSP projects.
    """
    
    def __init__(self, data_file_path: str = None):
        """
        Initialize the materials database.
        
        Args:
            data_file: Path to the JSON file for persistence
        """
        self.data_file = data_file_path
        self.materials = self._load_materials()
        # Merge in any new defaults without overwriting user edits
        self._merge_default_materials()
    
    def _load_materials(self) -> List[Dict]:
        """
        Load materials from file or use defaults.
        
        Returns:
            List of material dictionaries
        """
        # Try to load from file
        if self.data_file and os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        # Use default materials if file doesn't exist or is invalid
        # This will happen on first run in Streamlit Cloud
        default_materials = self._load_default_materials()
        
        # Save defaults for next time
        try:
            self.save()
        except:
            # In read-only environments, just use defaults without saving
            pass
        
        return default_materials

    def _merge_default_materials(self):
        """
        Merge newly added default materials without overwriting existing ones.
        Uses cleaned names for matching and preserves user overrides.
        """
        defaults = self._load_default_materials()
        existing_names = {self._clean_material_name(m.get('name', '')): m for m in self.materials}

        merged = list(self.materials)
        for mat in defaults:
            clean = self._clean_material_name(mat.get('name', ''))
            if clean not in existing_names:
                merged.append(mat)
        self.materials = merged
        self.save()
    
    def _load_default_materials(self) -> List[Dict]:
        """
        Load the default materials list.
        
        Returns:
            List of material dictionaries with name, part_number, unit_cost, unit
        """
        materials = [
            # Conduit (UG)
            {"name": "1/2\" Conduit orange", "part_number": None, "unit_cost": 0.58, "unit": "FT", "category": "Conduit"},
            {"name": "3/4\" Conduit orange", "part_number": None, "unit_cost": 0.72, "unit": "FT", "category": "Conduit"},
            {"name": "1\" Conduit orange", "part_number": None, "unit_cost": 0.88, "unit": "FT", "category": "Conduit"},
            {"name": "1.25\" Conduit orange", "part_number": None, "unit_cost": 1.15, "unit": "FT", "category": "Conduit"},
            {"name": "1.5\" Conduit orange", "part_number": None, "unit_cost": 1.35, "unit": "FT", "category": "Conduit"},
            {"name": "2\" Conduit orange", "part_number": None, "unit_cost": 1.45, "unit": "FT", "category": "Conduit"},
            {"name": "3\" Conduit orange", "part_number": None, "unit_cost": 2.25, "unit": "FT", "category": "Conduit"},
            {"name": "4\" Conduit orange", "part_number": None, "unit_cost": 3.55, "unit": "FT", "category": "Conduit"},
            {"name": ".75\" Conduit orange", "part_number": None, "unit_cost": 0.82, "unit": "FT", "category": "Conduit"},

            # Conduit (Aerial/Fiber support)
            {"name": "1/4\" Messenger Strand", "part_number": None, "unit_cost": 0.70, "unit": "FT", "category": "Aerial"},
            {"name": "5/16\" Messenger Strand", "part_number": None, "unit_cost": 0.95, "unit": "FT", "category": "Aerial"},
            {"name": "3/8\" Messenger Strand", "part_number": None, "unit_cost": 1.20, "unit": "FT", "category": "Aerial"},
            {"name": "Figure-8 Aerial Fiber 12ct", "part_number": None, "unit_cost": 0.55, "unit": "FT", "category": "Aerial"},
            {"name": "Figure-8 Aerial Fiber 24ct", "part_number": None, "unit_cost": 0.78, "unit": "FT", "category": "Aerial"},
            {"name": "Figure-8 Aerial Fiber 48ct", "part_number": None, "unit_cost": 1.05, "unit": "FT", "category": "Aerial"},
            {"name": "ADSS Aerial Fiber 12ct", "part_number": None, "unit_cost": 0.62, "unit": "FT", "category": "Aerial"},
            {"name": "ADSS Aerial Fiber 24ct", "part_number": None, "unit_cost": 0.86, "unit": "FT", "category": "Aerial"},
            {"name": "ADSS Aerial Fiber 48ct", "part_number": None, "unit_cost": 1.15, "unit": "FT", "category": "Aerial"},

            # Strand hardware
            {"name": "Strandvise 1/4\"", "part_number": None, "unit_cost": 6.50, "unit": "ea", "category": "Aerial"},
            {"name": "Strandvise 5/16\"", "part_number": None, "unit_cost": 7.25, "unit": "ea", "category": "Aerial"},
            {"name": "Strand Clamp 1/4\"", "part_number": None, "unit_cost": 4.25, "unit": "ea", "category": "Aerial"},
            {"name": "Strand Clamp 5/16\"", "part_number": None, "unit_cost": 4.75, "unit": "ea", "category": "Aerial"},
            {"name": "Lashing Wire 1200' Roll", "part_number": None, "unit_cost": 68.00, "unit": "each", "category": "Aerial"},
            {"name": "Lasher Misc Kit", "part_number": None, "unit_cost": 45.00, "unit": "kit", "category": "Aerial"},

            # Fiber drop/closures
            {"name": "Aerial Slack Storage Bracket", "part_number": None, "unit_cost": 22.00, "unit": "ea", "category": "Aerial"},
            {"name": "Aerial Fiber Splice Closure", "part_number": None, "unit_cost": 165.00, "unit": "ea", "category": "Aerial"},
            {"name": "Aerial Fiber Drop Clamp", "part_number": None, "unit_cost": 3.25, "unit": "ea", "category": "Aerial"},
            {"name": "Aerial Fiber Suspension Clamp", "part_number": None, "unit_cost": 7.50, "unit": "ea", "category": "Aerial"},

            # Couplers
            {"name": "2\" Duct Couplers", "part_number": None, "unit_cost": 8.99, "unit": "ea", "category": "Couplers"},
            {"name": "3\" Duct Couplers", "part_number": None, "unit_cost": 15.25, "unit": "ea", "category": "Couplers"},
            {"name": "4\" Duct Couplers", "part_number": None, "unit_cost": 2.42, "unit": "ea", "category": "Couplers"},
            {
                "name": "4\" Duct Plugs",
                "part_number": None,
                "unit_cost": 5.50,
                "unit": "ea",
                "category": "Plugs"
            },
            {
                "name": "FLOWERPOT",
                "part_number": None,
                "unit_cost": 15.50,
                "unit": "each",
                "category": "Equipment"
            },
            {
                "name": "HH's (18\" X 24\") T22 rated lids",
                "part_number": None,
                "unit_cost": 328.00,
                "unit": "each",
                "category": "Hand Holes"
            },
            {
                "name": "HH's (2' X 3') T22 rated lids",
                "part_number": None,
                "unit_cost": 470.00,
                "unit": "each",
                "category": "Hand Holes"
            },
            {
                "name": "HH's (3' X 4') T22 rated lids",
                "part_number": None,
                "unit_cost": 698.00,
                "unit": "each",
                "category": "Hand Holes"
            },
            {
                "name": "Mule Tape (3000')",
                "part_number": "8700137881",
                "unit_cost": 0.052,
                "unit": "FT",
                "category": "Cable"
            },
            {
                "name": "Grounding Staples (500 box)",
                "part_number": "8700138599",
                "unit_cost": 1.13,
                "unit": "each",
                "category": "Grounding"
            },
            {
                "name": "#6 Insulated Grd Wire 600' reel",
                "part_number": "8700137948",
                "unit_cost": 1.125,
                "unit": "FT",
                "category": "Grounding"
            },
            {
                "name": "Fiber Markers",
                "part_number": None,
                "unit_cost": 45.00,
                "unit": "each",
                "category": "Markers"
            },
            {
                "name": "Ground Rod Clamp",
                "part_number": "8700131718",
                "unit_cost": 2.15,
                "unit": "each",
                "category": "Grounding"
            },
            {
                "name": "Pea Gravel",
                "part_number": None,
                "unit_cost": 6.50,
                "unit": "bag",
                "category": "Materials"
            },
            {
                "name": "Ground Rod",
                "part_number": "8700137864",
                "unit_cost": 18.95,
                "unit": "each",
                "category": "Grounding"
            },
            {
                "name": "Bollards",
                "part_number": None,
                "unit_cost": 170.00,
                "unit": "each",
                "category": "Equipment"
            },
            {
                "name": "Dig Marking Tape - 1000' Roll",
                "part_number": None,
                "unit_cost": 26.99,
                "unit": "each",
                "category": "Safety"
            },
            {
                "name": "48\" Orange Plastic Barricade (Safety Netting)",
                "part_number": None,
                "unit_cost": 26.99,
                "unit": "each",
                "category": "Safety"
            }
        ]
        
        return materials
    
    def get_materials_by_category(self) -> Dict[str, List[Dict]]:
        """
        Group materials by category.
        
        Returns:
            Dictionary mapping categories to material lists
        """
        categories = {}
        for material in self.materials:
            category = material.get('category', 'Other')
            if category not in categories:
                categories[category] = []
            categories[category].append(material)
        
        return categories
    
    def get_material_names(self) -> List[str]:
        """
        Get list of all material names.
        
        Returns:
            List of material names
        """
        return [m['name'] for m in self.materials]
    
    def find_material(self, name: str) -> Optional[Dict]:
        """
        Find a material by name.
        
        Args:
            name: Material name to search for
            
        Returns:
            Material dictionary or None if not found
        """
        for material in self.materials:
            if material['name'].lower() == name.lower():
                return material
        return None
    
    def _clean_material_name(self, name: str) -> str:
        """
        Clean material name by removing vendor descriptions in parentheses.
        
        Args:
            name: Raw material name
            
        Returns:
            Cleaned material name
        """
        import re
        
        # Remove content in parentheses
        # This handles cases like "3''duct couplers (50 pack)" -> "3''duct couplers"
        cleaned = re.sub(r'\s*\([^)]*\)', '', str(name))
        
        # Clean up extra whitespace
        cleaned = cleaned.strip()
        
        return cleaned
    
    def add_material(self, name: str, part_number: str = None, 
                     unit_cost: float = 0.0, unit: str = "each", 
                     category: str = "Other"):
        """
        Add a new material to the database.
        
        Args:
            name: Material name
            part_number: Part number (optional)
            unit_cost: Unit cost
            unit: Unit of measure
            category: Material category
        """
        # Clean the material name
        clean_name = self._clean_material_name(name)
        
        material = {
            "name": clean_name,
            "part_number": part_number,
            "unit_cost": unit_cost,
            "unit": unit,
            "category": category
        }
        self.materials.append(material)
        self.save()  # Auto-save after adding
    
    def update_material(self, name: str, **kwargs):
        """
        Update an existing material.
        
        Args:
            name: Material name to update
            **kwargs: Fields to update (unit_cost, part_number, unit, category)
        """
        for material in self.materials:
            if material['name'] == name:
                for key, value in kwargs.items():
                    if key in material:
                        material[key] = value
                self.save()  # Auto-save after updating
                break
    
    def delete_material(self, name: str):
        """
        Delete a material from the database.
        
        Args:
            name: Material name to delete
        """
        self.materials = [m for m in self.materials if m['name'] != name]
        self.save()  # Auto-save after deleting
    
    def save(self):
        """Save the materials database to file."""
        if not self.data_file:
            return
        with open(self.data_file, 'w') as f:
            json.dump(self.materials, f, indent=2)
    
    def add_materials_from_quote(self, df: pd.DataFrame, 
                                desc_col: str = 'Description',
                                part_col: str = 'Part Number',
                                unit_col: str = 'Unit',
                                cost_col: str = 'Unit Cost',
                                category: str = 'Other'):
        """
        Automatically add new materials from a processed quote.
        
        Args:
            df: DataFrame from processed quote
            desc_col: Column name for material description
            part_col: Column name for part number
            unit_col: Column name for unit
            cost_col: Column name for unit cost
            category: Default category for new materials
        """
        added_count = 0
        
        for _, row in df.iterrows():
            # Skip if description is empty
            if pd.isna(row.get(desc_col)) or not row[desc_col].strip():
                continue
                
            material_name = str(row[desc_col]).strip()
            
            # Clean the material name (remove parenthetical descriptions)
            clean_material_name = self._clean_material_name(material_name)
            
            # Check if material already exists (using cleaned name)
            if not self.find_material(clean_material_name):
                # Extract data
                part_number = row.get(part_col) if part_col in row and pd.notna(row.get(part_col)) else None
                unit = row.get(unit_col, 'ea') if unit_col in row else 'ea'
                unit_cost = row.get(cost_col, 0) if cost_col in row and pd.notna(row.get(cost_col)) else 0
                
                # Add new material with cleaned name
                self.add_material(
                    name=clean_material_name,
                    part_number=str(part_number) if part_number else None,
                    unit_cost=float(unit_cost),
                    unit=str(unit),
                    category=category
                )
                added_count += 1
        
        return added_count
    
    def to_dataframe(self, columns: Optional[List[str]] = None, hide_sensitive: bool = True) -> pd.DataFrame:
        """
        Convert materials database to DataFrame.
        
        Args:
            columns: Optional list of columns to include
            hide_sensitive: If True, hides unit_cost and part_number columns
            
        Returns:
            DataFrame with materials data
        """
        df = pd.DataFrame(self.materials)
        
        # Filter columns if specified
        if columns:
            df = df[columns]
        elif hide_sensitive:
            # Hide sensitive columns by default
            df = df[['name', 'category']]
        
        return df
    
    def save_to_file(self, filepath: str):
        """
        Save materials database to JSON file.
        
        Args:
            filepath: Path to save the file
        """
        with open(filepath, 'w') as f:
            json.dump(self.materials, f, indent=2)
    
    def load_from_file(self, filepath: str):
        """
        Load materials database from JSON file.
        
        Args:
            filepath: Path to load the file from
        """
        with open(filepath, 'r') as f:
            self.materials = json.load(f)