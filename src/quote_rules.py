"""
Quote Rules Engine
Material and labor selection rules based on GIS design attributes
Supports intelligent auto-selection and quantity calculation
"""

import math
from typing import Dict, List, Optional, Tuple
import pandas as pd


class QuoteRules:
    """Rule engine for auto-generating quotes from GIS measurements."""
    
    @staticmethod
    def select_cable_type(fiber_count: int, install_method: str) -> str:
        """
        Select appropriate fiber cable based on count and install method.
        
        Args:
            fiber_count: Number of fibers
            install_method: 'underground', 'aerial', 'boring', etc.
            
        Returns:
            Material name
        """
        if install_method.lower() in ['underground', 'direct_bury', 'boring']:
            if fiber_count <= 12:
                return f'{fiber_count}ct SMF Direct Buried Fiber Cable'
            elif fiber_count <= 24:
                return f'{fiber_count}ct SMF Direct Buried Fiber Cable'
            elif fiber_count <= 48:
                return f'{fiber_count}ct SMF Direct Buried Fiber Cable'
            elif fiber_count <= 96:
                return f'{fiber_count}ct SMF Direct Buried Fiber Cable'
            elif fiber_count <= 144:
                return f'{fiber_count}ct SMF Direct Buried Fiber Cable'
            else:
                return f'{fiber_count}ct SMF Direct Buried Fiber Cable'
                
        elif install_method.lower() in ['aerial', 'strand', 'lashed']:
            if fiber_count <= 12:
                return f'{fiber_count}ct Figure-8 Aerial Fiber Cable'
            elif fiber_count <= 24:
                return f'{fiber_count}ct Figure-8 Aerial Fiber Cable'
            elif fiber_count <= 48:
                return f'{fiber_count}ct Figure-8 Aerial Fiber Cable'
            elif fiber_count <= 96:
                return f'{fiber_count}ct Figure-8 Aerial Fiber Cable'
            elif fiber_count <= 144:
                return f'{fiber_count}ct Figure-8 Aerial Fiber Cable'
            else:
                return f'{fiber_count}ct Figure-8 Aerial Fiber Cable'
        
        else:
            return f'{fiber_count}ct SMF Fiber Cable'
    
    @staticmethod
    def select_conduit_type(cable_count: int = 1, 
                           install_method: str = 'underground',
                           depth: Optional[int] = None) -> Tuple[str, str]:
        """
        Select conduit size and type based on cable count and install method.
        
        Args:
            cable_count: Number of cables in conduit
            install_method: Installation method
            depth: Installation depth in inches
            
        Returns:
            (material_name, unit)
        """
        if install_method.lower() in ['boring', 'directional_drill']:
            material = 'HDPE Conduit DR11'
        else:
            material = 'HDPE Conduit'
        
        if cable_count == 1:
            return f'2" {material}', 'FT'
        elif cable_count <= 2:
            return f'3" {material}', 'FT'
        elif cable_count <= 4:
            return f'4" {material}', 'FT'
        elif cable_count <= 6:
            return f'6" {material}', 'FT'
        else:
            return f'8" {material}', 'FT'
    
    @staticmethod
    def calculate_splice_count(cable_length_ft: float, 
                               splice_interval: int = 2000) -> int:
        """
        Calculate number of splice points based on cable length.
        
        Args:
            cable_length_ft: Total cable length in feet
            splice_interval: Feet between splices (default 2000)
            
        Returns:
            Number of splice closures needed
        """
        if cable_length_ft <= splice_interval:
            return 0
        
        return math.ceil(cable_length_ft / splice_interval) - 1
    
    @staticmethod
    def estimate_labor_underground(length_ft: float, 
                                   soil_type: str = 'normal',
                                   depth: int = 36) -> List[Dict]:
        """
        Estimate labor hours for underground installation.
        
        Args:
            length_ft: Cable/conduit length in feet
            soil_type: 'soft', 'normal', 'hard', 'rock'
            depth: Trench depth in inches
            
        Returns:
            List of labor tasks with hours
        """
        base_rate = 500
        
        soil_multipliers = {
            'soft': 0.8,
            'normal': 1.0,
            'hard': 1.3,
            'rock': 2.0
        }
        
        depth_multiplier = 1.0 + ((depth - 36) / 36) * 0.3
        
        total_multiplier = soil_multipliers.get(soil_type, 1.0) * depth_multiplier
        ft_per_day = base_rate / total_multiplier
        
        total_days = length_ft / ft_per_day
        
        return [
            {
                'task': 'Underground Trenching',
                'hours': round(total_days * 8 * 0.4, 2),
                'description': f'Trench {depth}" deep in {soil_type} soil'
            },
            {
                'task': 'Underground Cable Installation',
                'hours': round(total_days * 8 * 0.3, 2),
                'description': 'Place conduit and cable'
            },
            {
                'task': 'Underground Backfill',
                'hours': round(total_days * 8 * 0.2, 2),
                'description': 'Backfill and compact'
            },
            {
                'task': 'Restoration',
                'hours': round(total_days * 8 * 0.1, 2),
                'description': 'Surface restoration'
            }
        ]
    
    @staticmethod
    def estimate_labor_aerial(length_ft: float, 
                             pole_count: Optional[int] = None) -> List[Dict]:
        """
        Estimate labor hours for aerial installation.
        
        Args:
            length_ft: Cable length in feet
            pole_count: Number of poles (optional, will estimate if not provided)
            
        Returns:
            List of labor tasks with hours
        """
        if pole_count is None:
            avg_span = 150
            pole_count = math.ceil(length_ft / avg_span)
        
        ft_per_day = 800
        total_days = length_ft / ft_per_day
        
        return [
            {
                'task': 'Aerial Strand Installation',
                'hours': round(total_days * 8 * 0.4, 2),
                'description': f'Install strand on {pole_count} poles'
            },
            {
                'task': 'Aerial Cable Lashing',
                'hours': round(total_days * 8 * 0.5, 2),
                'description': 'Lash cable to strand'
            },
            {
                'task': 'Aerial Hardware Install',
                'hours': round(pole_count * 0.5, 2),
                'description': 'Install hardware and guides'
            }
        ]
    
    @staticmethod
    def estimate_labor_splicing(splice_count: int, 
                               fiber_count: int,
                               splice_type: str = 'fusion') -> Dict:
        """
        Estimate splicing labor.
        
        Args:
            splice_count: Number of splice points
            fiber_count: Fibers per splice
            splice_type: 'fusion' or 'mechanical'
            
        Returns:
            Labor task dictionary
        """
        if splice_type == 'mechanical':
            fibers_per_hour = 12
        else:
            fibers_per_hour = 6
        
        hours_per_splice = fiber_count / fibers_per_hour
        total_hours = splice_count * hours_per_splice
        
        return {
            'task': f'Fiber Splicing - {splice_type.title()}',
            'hours': round(total_hours, 2),
            'description': f'{splice_count} splices × {fiber_count} fibers'
        }
    
    @staticmethod
    def generate_bom_from_measurements(measurements_df: pd.DataFrame,
                                      mapping: Dict[str, str]) -> pd.DataFrame:
        """
        Generate Bill of Materials from measured GIS features.
        
        Args:
            measurements_df: DataFrame with extracted measurements
            mapping: Column mapping dictionary
            
        Returns:
            DataFrame formatted as BOM (materials + labor)
        """
        bom_items = []
        
        for _, row in measurements_df.iterrows():
            geom_type = row.get('geometry_type', 'Unknown')
            
            if geom_type in ['LineString', 'MultiLineString']:
                length = row.get('length_ft', 0)
                
                if length > 0:
                    fiber_count = row.get(mapping.get('fiber_count', 'fiber_count'), 12)
                    install_method = row.get(mapping.get('install_method', 'install_method'), 'underground')
                    
                    cable_name = QuoteRules.select_cable_type(fiber_count, install_method)
                    bom_items.append({
                        'type': 'material',
                        'name': cable_name,
                        'quantity': round(length, 2),
                        'unit': 'FT',
                        'category': 'Fiber Cable',
                        'source': 'GIS Auto-Generated'
                    })
                    
                    if install_method.lower() in ['underground', 'boring']:
                        conduit_name, unit = QuoteRules.select_conduit_type(1, install_method)
                        bom_items.append({
                            'type': 'material',
                            'name': conduit_name,
                            'quantity': round(length, 2),
                            'unit': unit,
                            'category': 'Conduit',
                            'source': 'GIS Auto-Generated'
                        })
                        
                        labor_tasks = QuoteRules.estimate_labor_underground(length)
                        for task in labor_tasks:
                            bom_items.append({
                                'type': 'labor',
                                'name': task['task'],
                                'quantity': task['hours'],
                                'unit': 'HR',
                                'category': 'Labor',
                                'description': task['description'],
                                'source': 'GIS Auto-Generated'
                            })
                    
                    elif install_method.lower() in ['aerial']:
                        labor_tasks = QuoteRules.estimate_labor_aerial(length)
                        for task in labor_tasks:
                            bom_items.append({
                                'type': 'labor',
                                'name': task['task'],
                                'quantity': task['hours'],
                                'unit': 'HR',
                                'category': 'Labor',
                                'description': task['description'],
                                'source': 'GIS Auto-Generated'
                            })
                    
                    splice_count = QuoteRules.calculate_splice_count(length)
                    if splice_count > 0:
                        bom_items.append({
                            'type': 'material',
                            'name': f'Fiber Splice Closure {fiber_count}ct',
                            'quantity': splice_count,
                            'unit': 'EA',
                            'category': 'Splice Closures',
                            'source': 'GIS Auto-Generated'
                        })
                        
                        splice_labor = QuoteRules.estimate_labor_splicing(splice_count, fiber_count)
                        bom_items.append({
                            'type': 'labor',
                            'name': splice_labor['task'],
                            'quantity': splice_labor['hours'],
                            'unit': 'HR',
                            'category': 'Labor',
                            'description': splice_labor['description'],
                            'source': 'GIS Auto-Generated'
                        })
            
            elif geom_type in ['Point', 'MultiPoint']:
                equipment_type = row.get(mapping.get('equipment_type', 'equipment_type'), 'Unknown')
                
                if equipment_type != 'Unknown':
                    bom_items.append({
                        'type': 'material',
                        'name': equipment_type,
                        'quantity': 1,
                        'unit': 'EA',
                        'category': 'Equipment',
                        'source': 'GIS Auto-Generated'
                    })
        
        return pd.DataFrame(bom_items)
