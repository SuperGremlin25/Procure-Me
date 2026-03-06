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
        All unit_cost values are sanitized to 0.00.
        Populate via vendor quote import or environment config.
        
        Returns:
            List of material dictionaries with name, part_number, unit_cost, unit, category
        """
        materials = [
            # ================================================================
            # UNDERGROUND CONDUIT
            # ================================================================
            {"name": "1/2\" HDPE Conduit", "part_number": None, "unit_cost": 0.00, "unit": "FT", "category": "Conduit"},
            {"name": "3/4\" HDPE Conduit", "part_number": None, "unit_cost": 0.00, "unit": "FT", "category": "Conduit"},
            {"name": "1\" HDPE Conduit", "part_number": None, "unit_cost": 0.00, "unit": "FT", "category": "Conduit"},
            {"name": "1.25\" HDPE Conduit", "part_number": None, "unit_cost": 0.00, "unit": "FT", "category": "Conduit"},
            {"name": "1.5\" HDPE Conduit", "part_number": None, "unit_cost": 0.00, "unit": "FT", "category": "Conduit"},
            {"name": "2\" HDPE Conduit", "part_number": None, "unit_cost": 0.00, "unit": "FT", "category": "Conduit"},
            {"name": "3\" HDPE Conduit", "part_number": None, "unit_cost": 0.00, "unit": "FT", "category": "Conduit"},
            {"name": "4\" HDPE Conduit", "part_number": None, "unit_cost": 0.00, "unit": "FT", "category": "Conduit"},
            {"name": "1\" PVC Conduit Schedule 40", "part_number": None, "unit_cost": 0.00, "unit": "FT", "category": "Conduit"},
            {"name": "2\" PVC Conduit Schedule 40", "part_number": None, "unit_cost": 0.00, "unit": "FT", "category": "Conduit"},
            {"name": "4\" PVC Conduit Schedule 40", "part_number": None, "unit_cost": 0.00, "unit": "FT", "category": "Conduit"},
            {"name": "2\" Rigid Steel Conduit", "part_number": None, "unit_cost": 0.00, "unit": "FT", "category": "Conduit"},
            {"name": "4\" Rigid Steel Conduit", "part_number": None, "unit_cost": 0.00, "unit": "FT", "category": "Conduit"},

            # ================================================================
            # INNERDUCT
            # ================================================================
            {"name": "1\" Innerduct Orange", "part_number": None, "unit_cost": 0.00, "unit": "FT", "category": "Innerduct"},
            {"name": "1\" Innerduct Yellow", "part_number": None, "unit_cost": 0.00, "unit": "FT", "category": "Innerduct"},
            {"name": "1\" Innerduct Red", "part_number": None, "unit_cost": 0.00, "unit": "FT", "category": "Innerduct"},
            {"name": "1.25\" Innerduct Orange", "part_number": None, "unit_cost": 0.00, "unit": "FT", "category": "Innerduct"},
            {"name": "1.5\" Innerduct Orange", "part_number": None, "unit_cost": 0.00, "unit": "FT", "category": "Innerduct"},
            {"name": "Innerduct End Cap 1\"", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Innerduct"},
            {"name": "Innerduct Coupler 1\"", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Innerduct"},
            {"name": "Innerduct Coupler 1.25\"", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Innerduct"},

            # ================================================================
            # CONDUIT FITTINGS AND HARDWARE
            # ================================================================
            {"name": "2\" Duct Coupler", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Conduit Fittings"},
            {"name": "3\" Duct Coupler", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Conduit Fittings"},
            {"name": "4\" Duct Coupler", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Conduit Fittings"},
            {"name": "2\" Duct Plug", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Conduit Fittings"},
            {"name": "4\" Duct Plug", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Conduit Fittings"},
            {"name": "2\" 90-Degree Elbow HDPE", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Conduit Fittings"},
            {"name": "4\" 90-Degree Elbow HDPE", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Conduit Fittings"},
            {"name": "2\" End Bell", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Conduit Fittings"},
            {"name": "4\" End Bell", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Conduit Fittings"},
            {"name": "Duct Seal Compound 1lb", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Conduit Fittings"},
            {"name": "Conduit Spacer 2\" 4-way", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Conduit Fittings"},
            {"name": "Conduit Spacer 4\" 4-way", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Conduit Fittings"},

            # ================================================================
            # UNDERGROUND FIBER CABLE
            # ================================================================
            {"name": "Direct Buried Fiber 12ct SMF", "part_number": None, "unit_cost": 0.00, "unit": "FT", "category": "Underground Cable"},
            {"name": "Direct Buried Fiber 24ct SMF", "part_number": None, "unit_cost": 0.00, "unit": "FT", "category": "Underground Cable"},
            {"name": "Direct Buried Fiber 48ct SMF", "part_number": None, "unit_cost": 0.00, "unit": "FT", "category": "Underground Cable"},
            {"name": "Direct Buried Fiber 96ct SMF", "part_number": None, "unit_cost": 0.00, "unit": "FT", "category": "Underground Cable"},
            {"name": "Direct Buried Fiber 144ct SMF", "part_number": None, "unit_cost": 0.00, "unit": "FT", "category": "Underground Cable"},
            {"name": "Direct Buried Fiber 288ct SMF", "part_number": None, "unit_cost": 0.00, "unit": "FT", "category": "Underground Cable"},
            {"name": "Loose Tube Fiber 12ct SMF", "part_number": None, "unit_cost": 0.00, "unit": "FT", "category": "Underground Cable"},
            {"name": "Loose Tube Fiber 24ct SMF", "part_number": None, "unit_cost": 0.00, "unit": "FT", "category": "Underground Cable"},
            {"name": "Loose Tube Fiber 48ct SMF", "part_number": None, "unit_cost": 0.00, "unit": "FT", "category": "Underground Cable"},
            {"name": "Loose Tube Fiber 96ct SMF", "part_number": None, "unit_cost": 0.00, "unit": "FT", "category": "Underground Cable"},
            {"name": "Loose Tube Fiber 144ct SMF", "part_number": None, "unit_cost": 0.00, "unit": "FT", "category": "Underground Cable"},
            {"name": "Loose Tube Fiber 288ct SMF", "part_number": None, "unit_cost": 0.00, "unit": "FT", "category": "Underground Cable"},
            {"name": "Micro Cable Fiber 12ct SMF", "part_number": None, "unit_cost": 0.00, "unit": "FT", "category": "Underground Cable"},
            {"name": "Micro Cable Fiber 24ct SMF", "part_number": None, "unit_cost": 0.00, "unit": "FT", "category": "Underground Cable"},
            {"name": "Ribbon Fiber 144ct SMF", "part_number": None, "unit_cost": 0.00, "unit": "FT", "category": "Underground Cable"},
            {"name": "Ribbon Fiber 288ct SMF", "part_number": None, "unit_cost": 0.00, "unit": "FT", "category": "Underground Cable"},
            {"name": "Ribbon Fiber 432ct SMF", "part_number": None, "unit_cost": 0.00, "unit": "FT", "category": "Underground Cable"},

            # ================================================================
            # AERIAL STRAND AND HARDWARE
            # ================================================================
            {"name": "1/4\" Messenger Strand 6M", "part_number": None, "unit_cost": 0.00, "unit": "FT", "category": "Aerial"},
            {"name": "5/16\" Messenger Strand 6M", "part_number": None, "unit_cost": 0.00, "unit": "FT", "category": "Aerial"},
            {"name": "3/8\" Messenger Strand 6M", "part_number": None, "unit_cost": 0.00, "unit": "FT", "category": "Aerial"},
            {"name": "Lashing Wire 3/8\" 1000ft Reel", "part_number": None, "unit_cost": 0.00, "unit": "reel", "category": "Aerial"},
            {"name": "Down Guy Wire 1/4\" 250ft Reel", "part_number": None, "unit_cost": 0.00, "unit": "reel", "category": "Aerial"},
            {"name": "Guy Anchor Helix", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Aerial"},
            {"name": "Pole Band Clamp", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Aerial"},
            {"name": "Dead End Grip 3/8\" Strand", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Aerial"},
            {"name": "Strandvise 1/4\"", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Aerial"},
            {"name": "Strandvise 5/16\"", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Aerial"},
            {"name": "Strandvise 3/8\"", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Aerial"},
            {"name": "Strand Clamp 1/4\"", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Aerial"},
            {"name": "Strand Clamp 5/16\"", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Aerial"},
            {"name": "Preformed Lashing Tie", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Aerial"},
            {"name": "Lasher Misc Kit", "part_number": None, "unit_cost": 0.00, "unit": "kit", "category": "Aerial"},
            {"name": "Riser Pole Attachment Kit", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Aerial"},
            {"name": "Aerial Slack Storage Bracket", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Aerial"},
            {"name": "Aerial Fiber Drop Clamp", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Aerial"},
            {"name": "Aerial Fiber Suspension Clamp", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Aerial"},

            # ================================================================
            # AERIAL FIBER CABLE
            # ================================================================
            {"name": "Figure-8 Aerial Fiber 12ct SMF", "part_number": None, "unit_cost": 0.00, "unit": "FT", "category": "Aerial Cable"},
            {"name": "Figure-8 Aerial Fiber 24ct SMF", "part_number": None, "unit_cost": 0.00, "unit": "FT", "category": "Aerial Cable"},
            {"name": "Figure-8 Aerial Fiber 48ct SMF", "part_number": None, "unit_cost": 0.00, "unit": "FT", "category": "Aerial Cable"},
            {"name": "Figure-8 Aerial Fiber 96ct SMF", "part_number": None, "unit_cost": 0.00, "unit": "FT", "category": "Aerial Cable"},
            {"name": "Figure-8 Aerial Fiber 144ct SMF", "part_number": None, "unit_cost": 0.00, "unit": "FT", "category": "Aerial Cable"},
            {"name": "ADSS Aerial Fiber 12ct SMF", "part_number": None, "unit_cost": 0.00, "unit": "FT", "category": "Aerial Cable"},
            {"name": "ADSS Aerial Fiber 24ct SMF", "part_number": None, "unit_cost": 0.00, "unit": "FT", "category": "Aerial Cable"},
            {"name": "ADSS Aerial Fiber 48ct SMF", "part_number": None, "unit_cost": 0.00, "unit": "FT", "category": "Aerial Cable"},
            {"name": "ADSS Aerial Fiber 96ct SMF", "part_number": None, "unit_cost": 0.00, "unit": "FT", "category": "Aerial Cable"},
            {"name": "ADSS Aerial Fiber 144ct SMF", "part_number": None, "unit_cost": 0.00, "unit": "FT", "category": "Aerial Cable"},
            {"name": "OPGW Fiber Cable 24ct", "part_number": None, "unit_cost": 0.00, "unit": "FT", "category": "Aerial Cable"},
            {"name": "OPGW Fiber Cable 48ct", "part_number": None, "unit_cost": 0.00, "unit": "FT", "category": "Aerial Cable"},

            # ================================================================
            # DROP CABLE (MDU AND FTTH)
            # ================================================================
            {"name": "Fiber Drop Cable 2ct SMF Flat", "part_number": None, "unit_cost": 0.00, "unit": "FT", "category": "Drop Cable"},
            {"name": "Fiber Drop Cable 4ct SMF Flat", "part_number": None, "unit_cost": 0.00, "unit": "FT", "category": "Drop Cable"},
            {"name": "Fiber Drop Cable 2ct SMF Round", "part_number": None, "unit_cost": 0.00, "unit": "FT", "category": "Drop Cable"},
            {"name": "Fiber Drop Cable 4ct SMF Round", "part_number": None, "unit_cost": 0.00, "unit": "FT", "category": "Drop Cable"},
            {"name": "Fiber Drop Cable 2ct w/ Messenger", "part_number": None, "unit_cost": 0.00, "unit": "FT", "category": "Drop Cable"},
            {"name": "Pre-Connectorized Drop SC-APC 50ft", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Drop Cable"},
            {"name": "Pre-Connectorized Drop SC-APC 100ft", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Drop Cable"},
            {"name": "Pre-Connectorized Drop SC-APC 150ft", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Drop Cable"},
            {"name": "Pre-Connectorized Drop SC-APC 200ft", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Drop Cable"},

            # ================================================================
            # SPLICE CLOSURES
            # ================================================================
            {"name": "Aerial Inline Splice Closure 24ct", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Splice Closure"},
            {"name": "Aerial Inline Splice Closure 48ct", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Splice Closure"},
            {"name": "Aerial Inline Splice Closure 96ct", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Splice Closure"},
            {"name": "Aerial Butt Splice Closure 24ct", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Splice Closure"},
            {"name": "Aerial Butt Splice Closure 48ct", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Splice Closure"},
            {"name": "Underground Splice Closure 24ct", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Splice Closure"},
            {"name": "Underground Splice Closure 48ct", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Splice Closure"},
            {"name": "Underground Splice Closure 96ct", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Splice Closure"},
            {"name": "Underground Splice Closure 144ct", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Splice Closure"},
            {"name": "Underground Splice Closure 288ct", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Splice Closure"},
            {"name": "Pedestal Mount Splice Closure 48ct", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Splice Closure"},
            {"name": "Splice Tray 12ct Single-sided", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Splice Closure"},
            {"name": "Splice Tray 24ct Dual-sided", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Splice Closure"},
            {"name": "Fusion Splice Protector Pkg/100", "part_number": None, "unit_cost": 0.00, "unit": "pkg", "category": "Splice Closure"},
            {"name": "Mechanical Splice Connector SC", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Splice Closure"},

            # ================================================================
            # HANDHOLES AND VAULTS
            # ================================================================
            {"name": "Handhole 18\" x 24\" T22 Lid", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Hand Holes"},
            {"name": "Handhole 24\" x 36\" T22 Lid", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Hand Holes"},
            {"name": "Handhole 30\" x 48\" T22 Lid", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Hand Holes"},
            {"name": "Handhole 36\" x 60\" T22 Lid", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Hand Holes"},
            {"name": "Polymer Vault Lid T22", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Hand Holes"},
            {"name": "Concrete Vault 4x4x4", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Hand Holes"},
            {"name": "Concrete Vault 5x5x5", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Hand Holes"},
            {"name": "Flowerpot Conduit Entry", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Hand Holes"},

            # ================================================================
            # PEDESTALS
            # ================================================================
            {"name": "Fiber Pedestal 48ct SC-APC", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Pedestals"},
            {"name": "Fiber Pedestal 72ct SC-APC", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Pedestals"},
            {"name": "Fiber Pedestal 96ct SC-APC", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Pedestals"},
            {"name": "Fiber Pedestal 144ct SC-APC", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Pedestals"},
            {"name": "Pedestal Base Anchor Kit", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Pedestals"},
            {"name": "Pedestal Extension Riser 12\"", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Pedestals"},
            {"name": "Pedestal Lock Kit", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Pedestals"},

            # ================================================================
            # PASSIVE DISTRIBUTION CABINETS (FDH / FAP / FST)
            # ================================================================
            {"name": "FDH Cabinet 288ct SC-APC Aerial", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Passive Cabinet"},
            {"name": "FDH Cabinet 288ct SC-APC Pedestal", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Passive Cabinet"},
            {"name": "FDH Cabinet 576ct SC-APC Aerial", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Passive Cabinet"},
            {"name": "FDH Cabinet 576ct SC-APC Pedestal", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Passive Cabinet"},
            {"name": "FAP Fiber Access Point 48ct", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Passive Cabinet"},
            {"name": "FAP Fiber Access Point 96ct", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Passive Cabinet"},
            {"name": "FAP Fiber Access Point 144ct", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Passive Cabinet"},
            {"name": "Fiber Splice Terminal 8ct Aerial", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Passive Cabinet"},
            {"name": "Fiber Splice Terminal 16ct Aerial", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Passive Cabinet"},
            {"name": "Fiber Splice Terminal 24ct Pedestal", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Passive Cabinet"},
            {"name": "Wall Mount Fiber Distribution Box 12ct", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Passive Cabinet"},
            {"name": "Wall Mount Fiber Distribution Box 24ct", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Passive Cabinet"},
            {"name": "Fiber Patch Panel 24-port SC-APC 1U", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Passive Cabinet"},
            {"name": "Fiber Patch Panel 48-port SC-APC 2U", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Passive Cabinet"},
            {"name": "Fiber Patch Panel 24-port LC-UPC 1U", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Passive Cabinet"},
            {"name": "Cabinet Ground Lug Kit", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Passive Cabinet"},
            {"name": "Cabinet Mounting Pole Kit", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Passive Cabinet"},

            # ================================================================
            # ACTIVE CABINETS AND EQUIPMENT
            # ================================================================
            {"name": "OLT Outdoor Hardened Cabinet", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Active Cabinet"},
            {"name": "OLT Shelf 4-slot", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Active Cabinet"},
            {"name": "OLT Shelf 8-slot", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Active Cabinet"},
            {"name": "OLT Line Card GPON 8-port", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Active Cabinet"},
            {"name": "OLT Line Card GPON 16-port", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Active Cabinet"},
            {"name": "OLT Line Card XGS-PON 8-port", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Active Cabinet"},
            {"name": "OLT Line Card XGS-PON 16-port", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Active Cabinet"},
            {"name": "OLT Uplink Card 10G SFP+", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Active Cabinet"},
            {"name": "OLT Power Supply Unit -48VDC", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Active Cabinet"},
            {"name": "OLT Fan Tray Replacement", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Active Cabinet"},
            {"name": "Remote OLT Node Outdoor Hardened", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Active Cabinet"},
            {"name": "Fiber Node Cabinet Outdoor 19\" Rack", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Active Cabinet"},
            {"name": "Cabinet AC Power Distribution Unit", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Active Cabinet"},
            {"name": "Cabinet Battery Backup Unit 48V", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Active Cabinet"},
            {"name": "Cabinet Cooling Fan Unit", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Active Cabinet"},

            # ================================================================
            # SPLITTERS (PASSIVE OPTICAL)
            # ================================================================
            {"name": "PLC Splitter 1x2 SC-APC Bare", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Splitters"},
            {"name": "PLC Splitter 1x4 SC-APC Bare", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Splitters"},
            {"name": "PLC Splitter 1x8 SC-APC Bare", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Splitters"},
            {"name": "PLC Splitter 1x16 SC-APC Bare", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Splitters"},
            {"name": "PLC Splitter 1x32 SC-APC Bare", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Splitters"},
            {"name": "PLC Splitter 1x64 SC-APC Bare", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Splitters"},
            {"name": "PLC Splitter 1x8 SC-APC Cassette", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Splitters"},
            {"name": "PLC Splitter 1x16 SC-APC Cassette", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Splitters"},
            {"name": "PLC Splitter 1x32 SC-APC Cassette", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Splitters"},
            {"name": "PLC Splitter 2x32 SC-APC Tray Mount", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Splitters"},

            # ================================================================
            # CONNECTORS AND PIGTAILS
            # ================================================================
            {"name": "SC-APC Pigtail SMF 900um 1M", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Connectors"},
            {"name": "SC-UPC Pigtail SMF 900um 1M", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Connectors"},
            {"name": "LC-APC Pigtail SMF 900um 1M", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Connectors"},
            {"name": "LC-UPC Pigtail SMF 900um 1M", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Connectors"},
            {"name": "SC-APC Patch Cord SMF 3M", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Connectors"},
            {"name": "SC-APC Patch Cord SMF 5M", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Connectors"},
            {"name": "LC-UPC Patch Cord SMF 3M", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Connectors"},
            {"name": "SC-APC to LC-UPC Hybrid Patch Cord 3M", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Connectors"},
            {"name": "SC-APC Adapter Coupler", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Connectors"},
            {"name": "LC-UPC Adapter Coupler", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Connectors"},
            {"name": "Optical Attenuator SC-APC 5dB", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Connectors"},
            {"name": "Optical Attenuator SC-APC 10dB", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Connectors"},
            {"name": "Fiber Optic Dust Cap SC", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Connectors"},
            {"name": "Fiber Optic Dust Cap LC", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Connectors"},

            # ================================================================
            # NETWORK INTERFACE DEVICES (NIDs)
            # ================================================================
            {"name": "NID Single Port SC-APC Indoor", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "NID"},
            {"name": "NID Dual Port SC-APC Indoor", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "NID"},
            {"name": "NID Single Port SC-APC Outdoor", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "NID"},
            {"name": "NID Hardened Outdoor 2-port", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "NID"},
            {"name": "NID Hardened Outdoor 4-port", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "NID"},
            {"name": "NID Wall Mount Bracket", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "NID"},

            # ================================================================
            # PULL WIRE AND MULE TAPE
            # ================================================================
            {"name": "Mule Tape 3000ft Reel", "part_number": None, "unit_cost": 0.00, "unit": "reel", "category": "Pull Supplies"},
            {"name": "Pull Wire Steel 1200ft Roll", "part_number": None, "unit_cost": 0.00, "unit": "roll", "category": "Pull Supplies"},
            {"name": "Pull String Nylon 1000ft Roll", "part_number": None, "unit_cost": 0.00, "unit": "roll", "category": "Pull Supplies"},
            {"name": "Cable Lubricant 1 Gallon", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Pull Supplies"},
            {"name": "Cable Lubricant 5 Gallon", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Pull Supplies"},
            {"name": "Fiber Pull Swivel 2\"", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Pull Supplies"},
            {"name": "Fiber Pull Sock 1\"", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Pull Supplies"},
            {"name": "Fiber Pull Sock 2\"", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Pull Supplies"},

            # ================================================================
            # GROUNDING
            # ================================================================
            {"name": "Ground Rod 5/8\" x 8ft Copper", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Grounding"},
            {"name": "Ground Rod Clamp", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Grounding"},
            {"name": "#6 Insulated Ground Wire 600ft Reel", "part_number": None, "unit_cost": 0.00, "unit": "FT", "category": "Grounding"},
            {"name": "#4 Bare Copper Ground Wire 500ft Reel", "part_number": None, "unit_cost": 0.00, "unit": "FT", "category": "Grounding"},
            {"name": "Grounding Staples 500-pack", "part_number": None, "unit_cost": 0.00, "unit": "box", "category": "Grounding"},
            {"name": "Split Bolt Connector #6", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Grounding"},
            {"name": "Compression Ground Lug #6", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Grounding"},
            {"name": "Strand Ground Clamp", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Grounding"},
            {"name": "Cabinet Ground Bar Kit", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Grounding"},

            # ================================================================
            # SAFETY AND SITE MATERIALS
            # ================================================================
            {"name": "Dig Marking Tape Orange 1000ft Roll", "part_number": None, "unit_cost": 0.00, "unit": "roll", "category": "Safety"},
            {"name": "Warning Tape Fiber Optic 1000ft", "part_number": None, "unit_cost": 0.00, "unit": "roll", "category": "Safety"},
            {"name": "48\" Orange Plastic Safety Barricade", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Safety"},
            {"name": "Traffic Cone 28\" Orange", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Safety"},
            {"name": "Vinyl Flagging Tape Roll", "part_number": None, "unit_cost": 0.00, "unit": "roll", "category": "Safety"},
            {"name": "Bollard Post Steel", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Safety"},
            {"name": "Bollard Cover Orange", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Safety"},

            # ================================================================
            # MARKERS AND IDENTIFICATION
            # ================================================================
            {"name": "Fiber Route Marker Post", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Markers"},
            {"name": "Fiber ID Label Pkg/50", "part_number": None, "unit_cost": 0.00, "unit": "pkg", "category": "Markers"},
            {"name": "Cable ID Tag Pkg/100", "part_number": None, "unit_cost": 0.00, "unit": "pkg", "category": "Markers"},
            {"name": "Handhole Lid ID Plate", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Markers"},
            {"name": "Pedestal ID Tag", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Markers"},
            {"name": "Splice Closure ID Tag", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Markers"},

            # ================================================================
            # CONSUMABLES AND SUPPLIES
            # ================================================================
            {"name": "Fiber Cleaning Kit IBC", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Consumables"},
            {"name": "Fiber End-Face Cleaner 500 clicks", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Consumables"},
            {"name": "Isopropyl Alcohol 99% 1L", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Consumables"},
            {"name": "Lint-Free Wipes Pkg/100", "part_number": None, "unit_cost": 0.00, "unit": "pkg", "category": "Consumables"},
            {"name": "Cable Ties 8\" Pkg/100", "part_number": None, "unit_cost": 0.00, "unit": "pkg", "category": "Consumables"},
            {"name": "Self-Amalgamating Tape Roll", "part_number": None, "unit_cost": 0.00, "unit": "roll", "category": "Consumables"},
            {"name": "Electrical Tape Roll", "part_number": None, "unit_cost": 0.00, "unit": "roll", "category": "Consumables"},
            {"name": "Heat Shrink Tubing Assortment", "part_number": None, "unit_cost": 0.00, "unit": "pkg", "category": "Consumables"},
            {"name": "Silicone Sealant 10oz", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Consumables"},
            {"name": "Expanding Foam Sealant 12oz", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Consumables"},
            {"name": "Dielectric Grease 4oz", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Consumables"},

            # ================================================================
            # BULK MATERIALS AND AGGREGATES
            # ================================================================
            {"name": "Pea Gravel Bag", "part_number": None, "unit_cost": 0.00, "unit": "bag", "category": "Materials"},
            {"name": "Sand Fill Bag", "part_number": None, "unit_cost": 0.00, "unit": "bag", "category": "Materials"},
            {"name": "Concrete Premix 60lb Bag", "part_number": None, "unit_cost": 0.00, "unit": "bag", "category": "Materials"},
            {"name": "Flowable Fill CY", "part_number": None, "unit_cost": 0.00, "unit": "CY", "category": "Materials"},
            {"name": "Asphalt Cold Patch Bag", "part_number": None, "unit_cost": 0.00, "unit": "bag", "category": "Materials"},

            # ================================================================
            # TEST AND INSPECTION
            # ================================================================
            {"name": "OTDR Test Port Adapter SC-APC", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Test Equipment"},
            {"name": "OTDR Test Port Adapter LC-UPC", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Test Equipment"},
            {"name": "Optical Power Meter Handheld", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Test Equipment"},
            {"name": "Visual Fault Locator VFL 10mW", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Test Equipment"},
            {"name": "Fiber End-Face Inspection Scope 400x", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Test Equipment"},
            {"name": "Optical Light Source SM 1310/1550nm", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Test Equipment"},
            {"name": "Fiber Identifier Live Fiber Detector", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Test Equipment"},

            # ================================================================
            # PLOW CONSTRUCTION MATERIALS
            # ================================================================
            {"name": "Plow-Grade Direct Buried Fiber 48ct SMF", "part_number": None, "unit_cost": 0.00, "unit": "FT", "category": "Plow Construction"},
            {"name": "Plow-Grade Direct Buried Fiber 96ct SMF", "part_number": None, "unit_cost": 0.00, "unit": "FT", "category": "Plow Construction"},
            {"name": "Plow-Grade Direct Buried Fiber 144ct SMF", "part_number": None, "unit_cost": 0.00, "unit": "FT", "category": "Plow Construction"},
            {"name": "Plow-Grade Direct Buried Fiber 288ct SMF", "part_number": None, "unit_cost": 0.00, "unit": "FT", "category": "Plow Construction"},
            {"name": "Plow-Grade 1\" HDPE Conduit", "part_number": None, "unit_cost": 0.00, "unit": "FT", "category": "Plow Construction"},
            {"name": "Plow-Grade 1.25\" HDPE Conduit", "part_number": None, "unit_cost": 0.00, "unit": "FT", "category": "Plow Construction"},
            {"name": "Plow-Grade 2\" HDPE Conduit", "part_number": None, "unit_cost": 0.00, "unit": "FT", "category": "Plow Construction"},
            {"name": "Plow Depth Marker Flag Pkg/100", "part_number": None, "unit_cost": 0.00, "unit": "pkg", "category": "Plow Construction"},
            {"name": "Cable Reel Trailer Stand Rental Day", "part_number": None, "unit_cost": 0.00, "unit": "day", "category": "Plow Construction"},
            {"name": "Reel Brake Assembly Rental Day", "part_number": None, "unit_cost": 0.00, "unit": "day", "category": "Plow Construction"},

            # ================================================================
            # CONCRETE PAD MATERIALS
            # ================================================================
            {"name": "Concrete Ready-Mix 3000psi CY", "part_number": None, "unit_cost": 0.00, "unit": "CY", "category": "Concrete Pad"},
            {"name": "Concrete Premix 60lb Bag 3000psi", "part_number": None, "unit_cost": 0.00, "unit": "bag", "category": "Concrete Pad"},
            {"name": "Rebar #4 20ft Stick", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Concrete Pad"},
            {"name": "Rebar #4 Cut and Bent Per Piece", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Concrete Pad"},
            {"name": "Rebar Tie Wire 16ga 3.5lb Coil", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Concrete Pad"},
            {"name": "Rebar Chair Spacer 2\" Pkg/50", "part_number": None, "unit_cost": 0.00, "unit": "pkg", "category": "Concrete Pad"},
            {"name": "Anchor Bolt Kit 4x4 Cabinet 4-bolt", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Concrete Pad"},
            {"name": "Anchor Bolt Kit 4x4 Cabinet 6-bolt", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Concrete Pad"},
            {"name": "Anchor Bolt 1/2\" x 12\" L-Type", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Concrete Pad"},
            {"name": "Anchor Bolt Template 4x4 Pad", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Concrete Pad"},
            {"name": "Conduit Stub-Up 2\" 90-Degree Through Pad", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Concrete Pad"},
            {"name": "Plywood Form Board 3/4\" 4x8 Sheet", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Concrete Pad"},
            {"name": "Form Stake Steel 1.5\" x 18\"", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Concrete Pad"},
            {"name": "Form Release Oil 1 Gallon", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Concrete Pad"},
            {"name": "Gravel Base Compacted 4\" Depth CY", "part_number": None, "unit_cost": 0.00, "unit": "CY", "category": "Concrete Pad"},
            {"name": "Geotextile Fabric 4x4 Pad Cut", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Concrete Pad"},
            {"name": "Concrete Sealer Penetrating 1 Gallon", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Concrete Pad"},
            {"name": "Expansion Joint Filler 1/2\" x 4\" Strip", "part_number": None, "unit_cost": 0.00, "unit": "FT", "category": "Concrete Pad"},
            
            # ================================================================
            # ELECTRICAL - WIRE & CABLE
            # ================================================================
            {"name": "12/2 NM-B Romex Wire 250ft", "part_number": None, "unit_cost": 0.00, "unit": "roll", "category": "Electrical Wire"},
            {"name": "14/2 NM-B Romex Wire 250ft", "part_number": None, "unit_cost": 0.00, "unit": "roll", "category": "Electrical Wire"},
            {"name": "12/3 NM-B Romex Wire 250ft", "part_number": None, "unit_cost": 0.00, "unit": "roll", "category": "Electrical Wire"},
            {"name": "10/2 NM-B Romex Wire 250ft", "part_number": None, "unit_cost": 0.00, "unit": "roll", "category": "Electrical Wire"},
            {"name": "#6 THHN/THWN Wire 500ft", "part_number": None, "unit_cost": 0.00, "unit": "roll", "category": "Electrical Wire"},
            {"name": "#4 THHN/THWN Wire 500ft", "part_number": None, "unit_cost": 0.00, "unit": "roll", "category": "Electrical Wire"},
            {"name": "#2 THHN/THWN Wire 500ft", "part_number": None, "unit_cost": 0.00, "unit": "roll", "category": "Electrical Wire"},
            {"name": "Cat6 Ethernet Cable 1000ft Box", "part_number": None, "unit_cost": 0.00, "unit": "box", "category": "Electrical Wire"},
            {"name": "Cat6A Ethernet Cable 1000ft Box", "part_number": None, "unit_cost": 0.00, "unit": "box", "category": "Electrical Wire"},
            {"name": "RG6 Coax Cable Quad Shield 1000ft", "part_number": None, "unit_cost": 0.00, "unit": "roll", "category": "Electrical Wire"},
            {"name": "18/2 Thermostat Wire 250ft", "part_number": None, "unit_cost": 0.00, "unit": "roll", "category": "Electrical Wire"},
            {"name": "14/4 Security Alarm Wire 500ft", "part_number": None, "unit_cost": 0.00, "unit": "roll", "category": "Electrical Wire"},
            
            # ================================================================
            # ELECTRICAL - BOXES & DEVICES
            # ================================================================
            {"name": "Single Gang New Work Box", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Electrical Boxes"},
            {"name": "Double Gang New Work Box", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Electrical Boxes"},
            {"name": "4\" Square Box 2-1/8\" Deep", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Electrical Boxes"},
            {"name": "4-11/16\" Square Box 2-1/8\" Deep", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Electrical Boxes"},
            {"name": "Ceiling Fan Rated Box", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Electrical Boxes"},
            {"name": "Outdoor Weatherproof Box 1-Gang", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Electrical Boxes"},
            {"name": "15A Duplex Receptacle White", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Electrical Devices"},
            {"name": "20A Duplex Receptacle White", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Electrical Devices"},
            {"name": "15A GFCI Receptacle White", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Electrical Devices"},
            {"name": "20A GFCI Receptacle White", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Electrical Devices"},
            {"name": "15A AFCI Breaker Receptacle", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Electrical Devices"},
            {"name": "Single Pole Switch 15A White", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Electrical Devices"},
            {"name": "3-Way Switch 15A White", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Electrical Devices"},
            {"name": "4-Way Switch 15A White", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Electrical Devices"},
            {"name": "Dimmer Switch 3-Way LED Compatible", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Electrical Devices"},
            {"name": "USB Charging Receptacle White", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Electrical Devices"},
            
            # ================================================================
            # ELECTRICAL - PANELS & BREAKERS
            # ================================================================
            {"name": "200A Main Breaker Panel 40-Space", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Electrical Panel"},
            {"name": "100A Main Breaker Panel 20-Space", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Electrical Panel"},
            {"name": "15A Single Pole Breaker", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Electrical Panel"},
            {"name": "20A Single Pole Breaker", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Electrical Panel"},
            {"name": "30A Double Pole Breaker", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Electrical Panel"},
            {"name": "40A Double Pole Breaker", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Electrical Panel"},
            {"name": "50A Double Pole Breaker", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Electrical Panel"},
            {"name": "15A GFCI Circuit Breaker", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Electrical Panel"},
            {"name": "20A GFCI Circuit Breaker", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Electrical Panel"},
            {"name": "15A AFCI Circuit Breaker", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Electrical Panel"},
            {"name": "20A AFCI Circuit Breaker", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Electrical Panel"},
            {"name": "Dual Function AFCI/GFCI Breaker 20A", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Electrical Panel"},
            
            # ================================================================
            # PLUMBING - PIPE & FITTINGS (PEX)
            # ================================================================
            {"name": "1/2\" PEX Tubing Red 100ft Coil", "part_number": None, "unit_cost": 0.00, "unit": "coil", "category": "Plumbing PEX"},
            {"name": "1/2\" PEX Tubing Blue 100ft Coil", "part_number": None, "unit_cost": 0.00, "unit": "coil", "category": "Plumbing PEX"},
            {"name": "3/4\" PEX Tubing Red 100ft Coil", "part_number": None, "unit_cost": 0.00, "unit": "coil", "category": "Plumbing PEX"},
            {"name": "3/4\" PEX Tubing Blue 100ft Coil", "part_number": None, "unit_cost": 0.00, "unit": "coil", "category": "Plumbing PEX"},
            {"name": "1\" PEX Tubing Red 100ft Coil", "part_number": None, "unit_cost": 0.00, "unit": "coil", "category": "Plumbing PEX"},
            {"name": "1/2\" PEX Crimp Ring Pkg/25", "part_number": None, "unit_cost": 0.00, "unit": "pkg", "category": "Plumbing PEX"},
            {"name": "3/4\" PEX Crimp Ring Pkg/25", "part_number": None, "unit_cost": 0.00, "unit": "pkg", "category": "Plumbing PEX"},
            {"name": "1/2\" PEX Elbow Brass", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Plumbing PEX"},
            {"name": "3/4\" PEX Elbow Brass", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Plumbing PEX"},
            {"name": "1/2\" PEX Tee Brass", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Plumbing PEX"},
            {"name": "3/4\" PEX Tee Brass", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Plumbing PEX"},
            {"name": "1/2\" PEX x 1/2\" MIP Adapter", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Plumbing PEX"},
            {"name": "1/2\" PEX x 1/2\" FIP Adapter", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Plumbing PEX"},
            
            # ================================================================
            # PLUMBING - COPPER PIPE & FITTINGS
            # ================================================================
            {"name": "1/2\" Type L Copper Pipe 10ft Stick", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Plumbing Copper"},
            {"name": "3/4\" Type L Copper Pipe 10ft Stick", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Plumbing Copper"},
            {"name": "1\" Type L Copper Pipe 10ft Stick", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Plumbing Copper"},
            {"name": "1/2\" Copper 90-Degree Elbow", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Plumbing Copper"},
            {"name": "3/4\" Copper 90-Degree Elbow", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Plumbing Copper"},
            {"name": "1/2\" Copper Tee", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Plumbing Copper"},
            {"name": "3/4\" Copper Tee", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Plumbing Copper"},
            {"name": "1/2\" Copper Coupling", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Plumbing Copper"},
            {"name": "Lead-Free Solder 1lb Spool", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Plumbing Copper"},
            {"name": "Flux Paste 8oz", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Plumbing Copper"},
            
            # ================================================================
            # PLUMBING - DRAIN WASTE VENT (DWV)
            # ================================================================
            {"name": "3\" PVC DWV Pipe 10ft Stick", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Plumbing DWV"},
            {"name": "4\" PVC DWV Pipe 10ft Stick", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Plumbing DWV"},
            {"name": "2\" PVC DWV Pipe 10ft Stick", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Plumbing DWV"},
            {"name": "3\" PVC DWV 90-Degree Elbow", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Plumbing DWV"},
            {"name": "4\" PVC DWV 90-Degree Elbow", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Plumbing DWV"},
            {"name": "3\" PVC DWV Tee Sanitary", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Plumbing DWV"},
            {"name": "4\" PVC DWV Tee Sanitary", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Plumbing DWV"},
            {"name": "3\" PVC DWV Wye Fitting", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Plumbing DWV"},
            {"name": "4\" PVC DWV Wye Fitting", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Plumbing DWV"},
            {"name": "3\" PVC DWV Coupling", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Plumbing DWV"},
            {"name": "3\" PVC Cleanout with Plug", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Plumbing DWV"},
            {"name": "2\" PVC P-Trap", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Plumbing DWV"},
            
            # ================================================================
            # PLUMBING - FIXTURES & VALVES
            # ================================================================
            {"name": "1/2\" Ball Valve Brass Full Port", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Plumbing Valves"},
            {"name": "3/4\" Ball Valve Brass Full Port", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Plumbing Valves"},
            {"name": "1\" Ball Valve Brass Full Port", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Plumbing Valves"},
            {"name": "1/2\" Stop Valve Quarter Turn", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Plumbing Valves"},
            {"name": "1/2\" x 3/8\" Angle Stop Valve", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Plumbing Valves"},
            {"name": "Water Heater Drain Valve", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Plumbing Valves"},
            {"name": "Toilet Fill Valve Universal", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Plumbing Fixtures"},
            {"name": "Toilet Flapper Valve Universal", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Plumbing Fixtures"},
            {"name": "Toilet Wax Ring with Flange", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Plumbing Fixtures"},
            {"name": "Faucet Supply Line 1/2\" x 12\"", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Plumbing Fixtures"},
            {"name": "Faucet Supply Line 1/2\" x 20\"", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Plumbing Fixtures"},
            
            # ================================================================
            # HVAC - DUCTWORK
            # ================================================================
            {"name": "6\" Round Duct Pipe 5ft", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "HVAC Duct"},
            {"name": "8\" Round Duct Pipe 5ft", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "HVAC Duct"},
            {"name": "10\" Round Duct Pipe 5ft", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "HVAC Duct"},
            {"name": "6\" Round Duct Elbow 90-Degree", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "HVAC Duct"},
            {"name": "8\" Round Duct Elbow 90-Degree", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "HVAC Duct"},
            {"name": "6\" to 4\" Duct Reducer", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "HVAC Duct"},
            {"name": "8\" to 6\" Duct Reducer", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "HVAC Duct"},
            {"name": "6\" Round Boot Floor Register", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "HVAC Duct"},
            {"name": "6\" x 12\" Rectangular Duct 5ft", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "HVAC Duct"},
            {"name": "8\" x 12\" Rectangular Duct 5ft", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "HVAC Duct"},
            {"name": "Insulated Flex Duct 6\" x 25ft", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "HVAC Duct"},
            {"name": "Insulated Flex Duct 8\" x 25ft", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "HVAC Duct"},
            {"name": "Duct Damper 6\" Manual", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "HVAC Duct"},
            {"name": "Duct Damper 8\" Manual", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "HVAC Duct"},
            {"name": "HVAC Foil Tape 2.5\" x 50yd", "part_number": None, "unit_cost": 0.00, "unit": "roll", "category": "HVAC Duct"},
            {"name": "Duct Mastic Sealant 1 Gallon", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "HVAC Duct"},
            
            # ================================================================
            # HVAC - REGISTERS & GRILLES
            # ================================================================
            {"name": "Floor Register 4\" x 10\" White", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "HVAC Registers"},
            {"name": "Floor Register 4\" x 12\" White", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "HVAC Registers"},
            {"name": "Wall Register 4\" x 10\" White", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "HVAC Registers"},
            {"name": "Wall Register 6\" x 10\" White", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "HVAC Registers"},
            {"name": "Ceiling Diffuser 6\" Round White", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "HVAC Registers"},
            {"name": "Ceiling Diffuser 8\" Round White", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "HVAC Registers"},
            {"name": "Return Air Grille 14\" x 14\" White", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "HVAC Registers"},
            {"name": "Return Air Grille 20\" x 20\" White", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "HVAC Registers"},
            {"name": "Filter Grille 16\" x 20\" with Filter", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "HVAC Registers"},
            
            # ================================================================
            # HVAC - REFRIGERANT LINES
            # ================================================================
            {"name": "1/4\" Refrigerant Line Set 25ft", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "HVAC Refrigerant"},
            {"name": "3/8\" Refrigerant Line Set 25ft", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "HVAC Refrigerant"},
            {"name": "1/2\" Refrigerant Line Set 25ft", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "HVAC Refrigerant"},
            {"name": "Line Set Insulation 1/4\" 6ft", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "HVAC Refrigerant"},
            {"name": "Condensate Drain Pan 18\" x 24\"", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "HVAC Refrigerant"},
            {"name": "Condensate Drain Line 3/4\" PVC 10ft", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "HVAC Refrigerant"},
            {"name": "Condensate Pump 230V", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "HVAC Refrigerant"},
            {"name": "Disconnect Box 60A Non-Fused", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "HVAC Refrigerant"},
            {"name": "Thermostat Programmable 7-Day", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "HVAC Refrigerant"},
            {"name": "Thermostat WiFi Smart", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "HVAC Refrigerant"},
            
            # ================================================================
            # CARPENTRY - LUMBER
            # ================================================================
            {"name": "2x4 SPF Stud 8ft", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Lumber Framing"},
            {"name": "2x4 SPF Stud 10ft", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Lumber Framing"},
            {"name": "2x6 SPF Stud 8ft", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Lumber Framing"},
            {"name": "2x6 SPF Board 12ft", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Lumber Framing"},
            {"name": "2x8 SPF Board 12ft", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Lumber Framing"},
            {"name": "2x10 SPF Board 12ft", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Lumber Framing"},
            {"name": "2x12 SPF Board 12ft", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Lumber Framing"},
            {"name": "4x4 PT Post 8ft", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Lumber Framing"},
            {"name": "4x6 PT Post 8ft", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Lumber Framing"},
            {"name": "1x4 Pine Board 8ft", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Lumber Trim"},
            {"name": "1x6 Pine Board 8ft", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Lumber Trim"},
            {"name": "1x8 Pine Board 8ft", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Lumber Trim"},
            
            # ================================================================
            # CARPENTRY - SHEATHING & PANELS
            # ================================================================
            {"name": "OSB Sheathing 7/16\" 4x8 Sheet", "part_number": None, "unit_cost": 0.00, "unit": "sheet", "category": "Sheathing"},
            {"name": "OSB Sheathing 1/2\" 4x8 Sheet", "part_number": None, "unit_cost": 0.00, "unit": "sheet", "category": "Sheathing"},
            {"name": "OSB Sheathing 5/8\" 4x8 Sheet", "part_number": None, "unit_cost": 0.00, "unit": "sheet", "category": "Sheathing"},
            {"name": "OSB Sheathing 3/4\" 4x8 Sheet T&G", "part_number": None, "unit_cost": 0.00, "unit": "sheet", "category": "Sheathing"},
            {"name": "Plywood 1/2\" 4x8 Sheet BC Grade", "part_number": None, "unit_cost": 0.00, "unit": "sheet", "category": "Sheathing"},
            {"name": "Plywood 3/4\" 4x8 Sheet BC Grade", "part_number": None, "unit_cost": 0.00, "unit": "sheet", "category": "Sheathing"},
            {"name": "Plywood 1/2\" 4x8 ACX Exterior", "part_number": None, "unit_cost": 0.00, "unit": "sheet", "category": "Sheathing"},
            {"name": "Zip Sheathing 7/16\" 4x8 Sheet", "part_number": None, "unit_cost": 0.00, "unit": "sheet", "category": "Sheathing"},
            {"name": "Zip Tape 3-3/4\" x 90ft Roll", "part_number": None, "unit_cost": 0.00, "unit": "roll", "category": "Sheathing"},
            
            # ================================================================
            # CARPENTRY - FASTENERS
            # ================================================================
            {"name": "16d Common Nail 5lb Box", "part_number": None, "unit_cost": 0.00, "unit": "box", "category": "Fasteners"},
            {"name": "8d Common Nail 5lb Box", "part_number": None, "unit_cost": 0.00, "unit": "box", "category": "Fasteners"},
            {"name": "Framing Nail 3\" x .131 2000ct", "part_number": None, "unit_cost": 0.00, "unit": "box", "category": "Fasteners"},
            {"name": "Framing Nail 3-1/4\" x .131 2000ct", "part_number": None, "unit_cost": 0.00, "unit": "box", "category": "Fasteners"},
            {"name": "Deck Screw #10 x 3\" 1lb Box", "part_number": None, "unit_cost": 0.00, "unit": "box", "category": "Fasteners"},
            {"name": "Wood Screw #8 x 2-1/2\" 1lb Box", "part_number": None, "unit_cost": 0.00, "unit": "box", "category": "Fasteners"},
            {"name": "Joist Hanger 2x6 Galvanized", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Fasteners"},
            {"name": "Joist Hanger 2x8 Galvanized", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Fasteners"},
            {"name": "Joist Hanger 2x10 Galvanized", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Fasteners"},
            {"name": "Hurricane Tie Simpson H2.5A", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Fasteners"},
            {"name": "Simpson Strong-Tie Anchor Bolt", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Fasteners"},
            {"name": "Construction Adhesive 28oz Tube", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Fasteners"},
            
            # ================================================================
            # DRYWALL - PANELS & MUD
            # ================================================================
            {"name": "Drywall 1/2\" 4x8 Lightweight", "part_number": None, "unit_cost": 0.00, "unit": "sheet", "category": "Drywall"},
            {"name": "Drywall 1/2\" 4x12 Lightweight", "part_number": None, "unit_cost": 0.00, "unit": "sheet", "category": "Drywall"},
            {"name": "Drywall 5/8\" 4x8 Type X Fire", "part_number": None, "unit_cost": 0.00, "unit": "sheet", "category": "Drywall"},
            {"name": "Drywall 1/2\" 4x8 Moisture Resist", "part_number": None, "unit_cost": 0.00, "unit": "sheet", "category": "Drywall"},
            {"name": "Joint Compound All-Purpose 5gal", "part_number": None, "unit_cost": 0.00, "unit": "pail", "category": "Drywall Compound"},
            {"name": "Joint Compound Lightweight 4.5gal", "part_number": None, "unit_cost": 0.00, "unit": "pail", "category": "Drywall Compound"},
            {"name": "Joint Tape Paper 2\" x 250ft", "part_number": None, "unit_cost": 0.00, "unit": "roll", "category": "Drywall Compound"},
            {"name": "Joint Tape Mesh 2\" x 300ft", "part_number": None, "unit_cost": 0.00, "unit": "roll", "category": "Drywall Compound"},
            {"name": "Corner Bead Metal 8ft", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Drywall Compound"},
            {"name": "Corner Bead Vinyl 8ft", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Drywall Compound"},
            {"name": "Drywall Screw 1-1/4\" 1lb Box", "part_number": None, "unit_cost": 0.00, "unit": "box", "category": "Drywall"},
            {"name": "Drywall Screw 1-5/8\" 1lb Box", "part_number": None, "unit_cost": 0.00, "unit": "box", "category": "Drywall"},
            
            # ================================================================
            # PAINTING - PAINT & PRIMER
            # ================================================================
            {"name": "Interior Paint Flat White 5gal", "part_number": None, "unit_cost": 0.00, "unit": "pail", "category": "Paint"},
            {"name": "Interior Paint Eggshell White 5gal", "part_number": None, "unit_cost": 0.00, "unit": "pail", "category": "Paint"},
            {"name": "Interior Paint Semi-Gloss White 5gal", "part_number": None, "unit_cost": 0.00, "unit": "pail", "category": "Paint"},
            {"name": "Exterior Paint Satin White 5gal", "part_number": None, "unit_cost": 0.00, "unit": "pail", "category": "Paint"},
            {"name": "Primer Drywall PVA White 5gal", "part_number": None, "unit_cost": 0.00, "unit": "pail", "category": "Paint"},
            {"name": "Primer Bonding Multi-Surface 1gal", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Paint"},
            {"name": "Stain Blocking Primer 1gal", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Paint"},
            {"name": "Paint Roller Cover 9\" 3/8\" Nap", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Paint Supplies"},
            {"name": "Paint Roller Frame 9\"", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Paint Supplies"},
            {"name": "Paint Brush 2.5\" Angled", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Paint Supplies"},
            {"name": "Painter's Tape 1.5\" x 60yd Blue", "part_number": None, "unit_cost": 0.00, "unit": "roll", "category": "Paint Supplies"},
            {"name": "Plastic Drop Cloth 9x12", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Paint Supplies"},
            
            # ================================================================
            # ROOFING - SHINGLES & UNDERLAYMENT
            # ================================================================
            {"name": "3-Tab Asphalt Shingle Bundle Black", "part_number": None, "unit_cost": 0.00, "unit": "bundle", "category": "Roofing Shingles"},
            {"name": "Architectural Shingle Bundle Black", "part_number": None, "unit_cost": 0.00, "unit": "bundle", "category": "Roofing Shingles"},
            {"name": "Architectural Shingle Bundle Brown", "part_number": None, "unit_cost": 0.00, "unit": "bundle", "category": "Roofing Shingles"},
            {"name": "Ridge Cap Shingle Bundle", "part_number": None, "unit_cost": 0.00, "unit": "bundle", "category": "Roofing Shingles"},
            {"name": "Starter Strip Shingles 100ft Roll", "part_number": None, "unit_cost": 0.00, "unit": "roll", "category": "Roofing Shingles"},
            {"name": "Roofing Felt #15 432 SF Roll", "part_number": None, "unit_cost": 0.00, "unit": "roll", "category": "Roofing Underlayment"},
            {"name": "Roofing Felt #30 216 SF Roll", "part_number": None, "unit_cost": 0.00, "unit": "roll", "category": "Roofing Underlayment"},
            {"name": "Synthetic Underlayment 10sq Roll", "part_number": None, "unit_cost": 0.00, "unit": "roll", "category": "Roofing Underlayment"},
            {"name": "Ice & Water Shield 225 SF Roll", "part_number": None, "unit_cost": 0.00, "unit": "roll", "category": "Roofing Underlayment"},
            {"name": "Drip Edge Aluminum 10ft White", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Roofing Flashing"},
            {"name": "Step Flashing Aluminum 8\" x 8\"", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Roofing Flashing"},
            {"name": "Valley Flashing Aluminum 10ft", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Roofing Flashing"},
            {"name": "Roof Vent Plastic Static 12\" Base", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Roofing Vents"},
            {"name": "Ridge Vent Aluminum 4ft Section", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Roofing Vents"},
            {"name": "Roofing Nail 1-1/4\" Coil 7200ct", "part_number": None, "unit_cost": 0.00, "unit": "box", "category": "Roofing Fasteners"},
            
            # ================================================================
            # SITE WORK - LANDSCAPING
            # ================================================================
            {"name": "Topsoil Screened Cubic Yard", "part_number": None, "unit_cost": 0.00, "unit": "CY", "category": "Landscaping"},
            {"name": "Mulch Hardwood Dyed Brown CY", "part_number": None, "unit_cost": 0.00, "unit": "CY", "category": "Landscaping"},
            {"name": "River Rock 1-3\" CY", "part_number": None, "unit_cost": 0.00, "unit": "CY", "category": "Landscaping"},
            {"name": "Gravel 3/4\" Clean CY", "part_number": None, "unit_cost": 0.00, "unit": "CY", "category": "Landscaping"},
            {"name": "Sod Fescue Pallet 500 SF", "part_number": None, "unit_cost": 0.00, "unit": "pallet", "category": "Landscaping"},
            {"name": "Grass Seed Tall Fescue 50lb Bag", "part_number": None, "unit_cost": 0.00, "unit": "bag", "category": "Landscaping"},
            {"name": "Landscape Fabric 3x300ft Roll", "part_number": None, "unit_cost": 0.00, "unit": "roll", "category": "Landscaping"},
            {"name": "Edging Plastic 20ft Coil", "part_number": None, "unit_cost": 0.00, "unit": "coil", "category": "Landscaping"},
            {"name": "Landscape Timber 4x6x8 PT", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Landscaping"},
            {"name": "Retaining Wall Block Standard", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Landscaping"},
            {"name": "Paver Brick 4x8 Red", "part_number": None, "unit_cost": 0.00, "unit": "ea", "category": "Landscaping"},
            {"name": "Paver Base Sand 50lb Bag", "part_number": None, "unit_cost": 0.00, "unit": "bag", "category": "Landscaping"},
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