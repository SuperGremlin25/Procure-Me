"""
GIS File Parser
Supports shapefile, GeoJSON, KML, GeoPackage, and DXF formats
Extracts geometric features and attributes for quote generation
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json
import zipfile
import tempfile

try:
    import geopandas as gpd
    import pandas as pd
    from shapely.geometry import Point, LineString, Polygon, MultiLineString
    import fiona
    GIS_AVAILABLE = True
except ImportError:
    GIS_AVAILABLE = False
    gpd = None
    pd = None


class GISParser:
    """Parse GIS files and extract features for quote generation."""
    
    SUPPORTED_FORMATS = {
        '.shp': 'Shapefile',
        '.geojson': 'GeoJSON',
        '.json': 'GeoJSON',
        '.kml': 'KML',
        '.kmz': 'KMZ (Compressed KML)',
        '.gpkg': 'GeoPackage',
        '.dxf': 'AutoCAD DXF'
    }
    
    def __init__(self):
        if not GIS_AVAILABLE:
            raise ImportError(
                "GIS libraries not installed. "
                "Run: pip install geopandas shapely fiona pyproj"
            )
    
    @staticmethod
    def detect_format(filepath: str) -> Optional[str]:
        """Detect GIS file format from extension."""
        ext = Path(filepath).suffix.lower()
        return GISParser.SUPPORTED_FORMATS.get(ext)
    
    @staticmethod
    def is_supported(filepath: str) -> bool:
        """Check if file format is supported."""
        return GISParser.detect_format(filepath) is not None
    
    def parse_file(self, filepath: str) -> gpd.GeoDataFrame:
        """
        Parse any supported GIS file and return GeoDataFrame.
        
        Args:
            filepath: Path to GIS file
            
        Returns:
            GeoDataFrame with features and attributes
        """
        format_name = self.detect_format(filepath)
        
        if not format_name:
            raise ValueError(f"Unsupported file format: {Path(filepath).suffix}")
        
        ext = Path(filepath).suffix.lower()
        
        if ext == '.shp':
            return self.parse_shapefile(filepath)
        elif ext in ['.geojson', '.json']:
            return self.parse_geojson(filepath)
        elif ext == '.kml':
            return self.parse_kml(filepath)
        elif ext == '.kmz':
            return self.parse_kmz(filepath)
        elif ext == '.gpkg':
            return self.parse_geopackage(filepath)
        elif ext == '.dxf':
            return self.parse_dxf(filepath)
        else:
            raise ValueError(f"Parser not implemented for {format_name}")
    
    @staticmethod
    def parse_shapefile(filepath: str) -> gpd.GeoDataFrame:
        """Parse ESRI Shapefile."""
        try:
            gdf = gpd.read_file(filepath)
            gdf = GISParser._standardize_gdf(gdf)
            return gdf
        except Exception as e:
            raise ValueError(f"Failed to parse shapefile: {str(e)}")
    
    @staticmethod
    def parse_geojson(filepath: str) -> gpd.GeoDataFrame:
        """Parse GeoJSON file."""
        try:
            gdf = gpd.read_file(filepath)
            gdf = GISParser._standardize_gdf(gdf)
            return gdf
        except Exception as e:
            raise ValueError(f"Failed to parse GeoJSON: {str(e)}")
    
    @staticmethod
    def parse_kml(filepath: str) -> gpd.GeoDataFrame:
        """Parse KML file."""
        try:
            fiona.drvsupport.supported_drivers['KML'] = 'rw'
            gdf = gpd.read_file(filepath, driver='KML')
            gdf = GISParser._standardize_gdf(gdf)
            return gdf
        except Exception as e:
            raise ValueError(f"Failed to parse KML: {str(e)}")
    
    @staticmethod
    def parse_kmz(filepath: str) -> gpd.GeoDataFrame:
        """Parse KMZ (compressed KML) file."""
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                with zipfile.ZipFile(filepath, 'r') as zip_ref:
                    zip_ref.extractall(tmpdir)
                
                kml_files = list(Path(tmpdir).glob('**/*.kml'))
                if not kml_files:
                    raise ValueError("No KML file found in KMZ archive")
                
                fiona.drvsupport.supported_drivers['KML'] = 'rw'
                gdf = gpd.read_file(str(kml_files[0]), driver='KML')
                gdf = GISParser._standardize_gdf(gdf)
                return gdf
        except Exception as e:
            raise ValueError(f"Failed to parse KMZ: {str(e)}")
    
    @staticmethod
    def parse_geopackage(filepath: str) -> gpd.GeoDataFrame:
        """Parse GeoPackage file."""
        try:
            layers = fiona.listlayers(filepath)
            if not layers:
                raise ValueError("No layers found in GeoPackage")
            
            gdf = gpd.read_file(filepath, layer=layers[0])
            gdf = GISParser._standardize_gdf(gdf)
            return gdf
        except Exception as e:
            raise ValueError(f"Failed to parse GeoPackage: {str(e)}")
    
    @staticmethod
    def parse_dxf(filepath: str) -> gpd.GeoDataFrame:
        """Parse AutoCAD DXF file (basic support)."""
        try:
            import ezdxf
            from shapely.geometry import Point, LineString, Polygon
            
            doc = ezdxf.readfile(filepath)
            msp = doc.modelspace()
            
            features = []
            for entity in msp:
                geom = None
                attributes = {'layer': entity.dxf.layer}
                
                if entity.dxftype() == 'LINE':
                    start = entity.dxf.start
                    end = entity.dxf.end
                    geom = LineString([(start.x, start.y), (end.x, end.y)])
                    
                elif entity.dxftype() == 'POLYLINE':
                    points = [(v.dxf.location.x, v.dxf.location.y) for v in entity.vertices]
                    if len(points) >= 2:
                        geom = LineString(points)
                
                elif entity.dxftype() == 'LWPOLYLINE':
                    points = [(p[0], p[1]) for p in entity.get_points()]
                    if len(points) >= 2:
                        geom = LineString(points)
                
                elif entity.dxftype() == 'POINT':
                    loc = entity.dxf.location
                    geom = Point(loc.x, loc.y)
                
                if geom:
                    features.append({'geometry': geom, **attributes})
            
            if not features:
                raise ValueError("No valid geometries found in DXF file")
            
            gdf = gpd.GeoDataFrame(features, crs='EPSG:4326')
            gdf = GISParser._standardize_gdf(gdf)
            return gdf
            
        except ImportError:
            raise ImportError("ezdxf library required for DXF parsing. Run: pip install ezdxf")
        except Exception as e:
            raise ValueError(f"Failed to parse DXF: {str(e)}")
    
    @staticmethod
    def _standardize_gdf(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """Standardize GeoDataFrame - ensure WGS84, add geometry type."""
        if gdf.crs is None:
            gdf = gdf.set_crs('EPSG:4326')
        elif gdf.crs != 'EPSG:4326':
            gdf = gdf.to_crs('EPSG:4326')
        
        gdf['geom_type'] = gdf.geometry.geom_type
        
        return gdf
    
    @staticmethod
    def get_layer_summary(gdf: gpd.GeoDataFrame) -> Dict:
        """Get summary statistics of GeoDataFrame."""
        return {
            'total_features': len(gdf),
            'geometry_types': gdf['geom_type'].value_counts().to_dict(),
            'bounds': gdf.total_bounds.tolist(),
            'crs': str(gdf.crs),
            'columns': list(gdf.columns),
            'attribute_summary': {
                col: {
                    'type': str(gdf[col].dtype),
                    'non_null': int(gdf[col].notna().sum()),
                    'unique_values': int(gdf[col].nunique()) if gdf[col].dtype == 'object' else None
                }
                for col in gdf.columns if col != 'geometry'
            }
        }
    
    @staticmethod
    def list_geopackage_layers(filepath: str) -> List[str]:
        """List all layers in a GeoPackage file."""
        try:
            return fiona.listlayers(filepath)
        except Exception as e:
            raise ValueError(f"Failed to list layers: {str(e)}")
    
    @staticmethod
    def validate_schema(gdf: gpd.GeoDataFrame) -> Tuple[bool, List[str]]:
        """
        Validate GeoDataFrame schema for quote generation.
        
        Returns:
            (is_valid, list_of_warnings)
        """
        warnings = []
        
        if len(gdf) == 0:
            warnings.append("No features found in file")
            return False, warnings
        
        if 'geometry' not in gdf.columns:
            warnings.append("No geometry column found")
            return False, warnings
        
        if gdf.geometry.isna().all():
            warnings.append("All geometries are null")
            return False, warnings
        
        null_geoms = gdf.geometry.isna().sum()
        if null_geoms > 0:
            warnings.append(f"{null_geoms} features have null geometry")
        
        invalid_geoms = (~gdf.geometry.is_valid).sum()
        if invalid_geoms > 0:
            warnings.append(f"{invalid_geoms} features have invalid geometry")
        
        if len(gdf.columns) == 1:
            warnings.append("No attribute columns found - only geometry present")
        
        return len(warnings) == 0 or null_geoms + invalid_geoms < len(gdf) * 0.5, warnings
