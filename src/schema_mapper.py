"""
Schema Mapper
Flexible attribute mapping between GIS files and internal schema
Supports auto-detection and user-defined mappings
"""

from typing import Dict, List, Optional, Tuple
import json
from pathlib import Path

try:
    import geopandas as gpd
    import pandas as pd
    GIS_AVAILABLE = True
except ImportError:
    GIS_AVAILABLE = False


class SchemaMapper:
    """Map GIS file attributes to internal quote schema."""
    
    STANDARD_SCHEMA = {
        'feature_type': 'Type of feature (fiber_cable, conduit, splice_point, equipment, etc.)',
        'material_name': 'Name of material from database',
        'material_category': 'Category for material lookup',
        'quantity': 'Measured quantity (length, count, area)',
        'unit': 'Unit of measure (FT, EA, SQ_FT, etc.)',
        'install_method': 'Installation method (underground, aerial, boring, etc.)',
        'description': 'Text description of item',
        'part_number': 'Part/model number if applicable',
        'fiber_count': 'Number of fibers in cable',
        'conduit_size': 'Conduit diameter in inches',
        'splice_type': 'Type of splice closure',
        'equipment_type': 'Type of equipment',
        'depth': 'Installation depth in inches',
        'location_name': 'Location or site identifier'
    }
    
    # Common attribute name variations from different GIS tools
    ATTRIBUTE_PATTERNS = {
        'length': ['length', 'len', 'distance', 'dist', 'shape_length', 'length_ft', 'feet'],
        'fiber_count': ['fiber_count', 'fibercount', 'fibers', 'fiber_ct', 'count', 'strand_count'],
        'cable_type': ['cable_type', 'cabletype', 'type', 'cable', 'material', 'mat_type'],
        'install_method': ['install_method', 'method', 'install_type', 'placement', 'install'],
        'conduit_size': ['conduit_size', 'size', 'diameter', 'conduit_dia', 'pipe_size'],
        'description': ['description', 'desc', 'name', 'label', 'comments', 'notes'],
        'location': ['location', 'site', 'site_name', 'area', 'zone', 'region']
    }
    
    def __init__(self):
        if not GIS_AVAILABLE:
            raise ImportError("GIS libraries required. Run: pip install geopandas")
    
    @staticmethod
    def auto_detect_fields(gdf: gpd.GeoDataFrame) -> Dict[str, Optional[str]]:
        """
        Auto-detect field mappings based on column names.
        
        Returns:
            Dictionary mapping standard fields to detected column names
        """
        detected = {}
        available_cols = [col.lower() for col in gdf.columns if col != 'geometry']
        
        for standard_field, patterns in SchemaMapper.ATTRIBUTE_PATTERNS.items():
            for pattern in patterns:
                for col in gdf.columns:
                    if col.lower() == pattern or pattern in col.lower():
                        detected[standard_field] = col
                        break
                if standard_field in detected:
                    break
        
        return detected
    
    @staticmethod
    def create_mapping_template(gdf: gpd.GeoDataFrame, 
                                filename: str = "mapping_template") -> Dict:
        """
        Create a mapping template for user review/editing.
        
        Args:
            gdf: GeoDataFrame to analyze
            filename: Name for the template
            
        Returns:
            Template dictionary with auto-detected and unmapped fields
        """
        auto_detected = SchemaMapper.auto_detect_fields(gdf)
        
        available_columns = [col for col in gdf.columns if col != 'geometry']
        
        template = {
            'template_name': filename,
            'source_file': 'unknown',
            'auto_detected': auto_detected,
            'user_mappings': {},
            'available_columns': available_columns,
            'column_info': {
                col: {
                    'type': str(gdf[col].dtype),
                    'sample_values': gdf[col].dropna().head(5).tolist(),
                    'unique_count': int(gdf[col].nunique())
                }
                for col in available_columns
            }
        }
        
        return template
    
    @staticmethod
    def apply_mapping(gdf: gpd.GeoDataFrame, mapping: Dict[str, str]) -> gpd.GeoDataFrame:
        """
        Apply attribute mapping to GeoDataFrame.
        
        Args:
            gdf: Original GeoDataFrame
            mapping: Dictionary of {standard_field: source_column}
            
        Returns:
            GeoDataFrame with renamed/mapped columns
        """
        mapped_gdf = gdf.copy()
        
        for standard_field, source_col in mapping.items():
            if source_col in gdf.columns:
                mapped_gdf[standard_field] = gdf[source_col]
        
        return mapped_gdf
    
    @staticmethod
    def extract_measurements(gdf: gpd.GeoDataFrame, 
                           feature_type_col: Optional[str] = None) -> pd.DataFrame:
        """
        Extract measurements from GeoDataFrame geometries.
        
        Args:
            gdf: GeoDataFrame with geometries
            feature_type_col: Column name for feature type (optional)
            
        Returns:
            DataFrame with extracted measurements
        """
        measurements = []
        
        for idx, row in gdf.iterrows():
            geom = row.geometry
            geom_type = geom.geom_type
            
            measurement = {
                'feature_id': idx,
                'geometry_type': geom_type
            }
            
            if feature_type_col and feature_type_col in row.index:
                measurement['feature_type'] = row[feature_type_col]
            
            if geom_type in ['LineString', 'MultiLineString']:
                length_ft = geom.length * 364000
                measurement['length_ft'] = round(length_ft, 2)
                measurement['quantity'] = length_ft
                measurement['unit'] = 'FT'
                
            elif geom_type in ['Point', 'MultiPoint']:
                measurement['quantity'] = 1
                measurement['unit'] = 'EA'
                
            elif geom_type in ['Polygon', 'MultiPolygon']:
                area_sqft = geom.area * (364000 ** 2)
                measurement['area_sqft'] = round(area_sqft, 2)
                measurement['quantity'] = area_sqft
                measurement['unit'] = 'SQ_FT'
            
            for col in gdf.columns:
                if col not in ['geometry', 'geom_type']:
                    measurement[col] = row[col]
            
            measurements.append(measurement)
        
        return pd.DataFrame(measurements)
    
    @staticmethod
    def save_template(template: Dict, filepath: str):
        """Save mapping template to JSON file."""
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(template, f, indent=2, default=str)
    
    @staticmethod
    def load_template(filepath: str) -> Dict:
        """Load mapping template from JSON file."""
        with open(filepath, 'r') as f:
            return json.load(f)
    
    @staticmethod
    def get_mapping_suggestions(gdf: gpd.GeoDataFrame, 
                                target_field: str) -> List[Tuple[str, float]]:
        """
        Get suggested column mappings for a target field based on similarity.
        
        Args:
            gdf: GeoDataFrame
            target_field: Standard field name to map
            
        Returns:
            List of (column_name, confidence_score) tuples
        """
        suggestions = []
        
        if target_field not in SchemaMapper.ATTRIBUTE_PATTERNS:
            return suggestions
        
        patterns = SchemaMapper.ATTRIBUTE_PATTERNS[target_field]
        
        for col in gdf.columns:
            if col == 'geometry':
                continue
                
            col_lower = col.lower()
            
            for i, pattern in enumerate(patterns):
                if col_lower == pattern:
                    confidence = 1.0 - (i * 0.1)
                    suggestions.append((col, confidence))
                    break
                elif pattern in col_lower:
                    confidence = 0.7 - (i * 0.1)
                    suggestions.append((col, confidence))
                    break
        
        suggestions.sort(key=lambda x: x[1], reverse=True)
        return suggestions[:3]
    
    @staticmethod
    def validate_mapping(gdf: gpd.GeoDataFrame, mapping: Dict[str, str]) -> Tuple[bool, List[str]]:
        """
        Validate a mapping configuration.
        
        Returns:
            (is_valid, list_of_errors)
        """
        errors = []
        
        for standard_field, source_col in mapping.items():
            if source_col not in gdf.columns:
                errors.append(f"Source column '{source_col}' not found in data")
        
        if 'quantity' in mapping:
            qty_col = mapping['quantity']
            if qty_col in gdf.columns:
                if not pd.api.types.is_numeric_dtype(gdf[qty_col]):
                    errors.append(f"Quantity column '{qty_col}' must be numeric")
        
        return len(errors) == 0, errors
