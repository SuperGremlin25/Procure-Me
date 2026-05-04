"""
GIS Spatial Join Module

Integrates remedy data with GIS design files through spatial joins.
"""

import geopandas as gpd
import pandas as pd
from typing import Dict, Any, Optional, List
from dataclasses import dataclass


@dataclass
class RemedyReport:
    """Lightweight remedy report for spatial join processing."""
    utility_company: str
    report_date: str
    total_poles: int
    actions: List[Dict[str, Any]]


class GISRemedyIntegrator:
    """Integrates remedy reports with GIS design files."""

    def __init__(self):
        self.design_gdf: Optional[gpd.GeoDataFrame] = None
        self.remedy_report: Optional[RemedyReport] = None
        self.joined_gdf: Optional[gpd.GeoDataFrame] = None

    def load_design_file(self, filepath: str, pole_id_field: str = "pole_id") -> gpd.GeoDataFrame:
        self.design_gdf = gpd.read_file(filepath)
        if pole_id_field not in self.design_gdf.columns:
            for col in ["pole_id", "PoleID", "POLE_ID", "id", "ID"]:
                if col in self.design_gdf.columns:
                    self.design_gdf["pole_id"] = self.design_gdf[col]
                    break
            else:
                self.design_gdf["pole_id"] = [f"POLE-{i+1:04d}" for i in range(len(self.design_gdf))]
        return self.design_gdf

    def load_remedy_report(self, remedy_data: Dict[str, Any]) -> RemedyReport:
        actions = remedy_data.get("actions", [])
        self.remedy_report = RemedyReport(
            utility_company=remedy_data.get("utility_company", "Unknown"),
            report_date=remedy_data.get("report_date", ""),
            total_poles=remedy_data.get("total_poles", len(actions)),
            actions=actions
        )
        return self.remedy_report

    def perform_spatial_join(self, match_method: str = "pole_id") -> gpd.GeoDataFrame:
        if self.design_gdf is None or self.remedy_report is None:
            raise ValueError("Must load design file and remedy report first")
        remedy_df = pd.DataFrame(self.remedy_report.actions)
        if match_method == "pole_id" and "pole_id" in remedy_df.columns:
            self.joined_gdf = self.design_gdf.merge(remedy_df, on="pole_id", how="left")
        else:
            self.joined_gdf = self.design_gdf.copy()
            self.joined_gdf["action_type"] = None
        self.joined_gdf["has_remediation"] = self.joined_gdf.get("action_type").notna()
        return self.joined_gdf

    def get_summary_statistics(self) -> Dict[str, Any]:
        if self.design_gdf is None:
            return {"error": "No design data loaded"}
        total = len(self.design_gdf)
        remediated = int(self.joined_gdf["has_remediation"].sum()) if self.joined_gdf is not None and "has_remediation" in self.joined_gdf.columns else 0
        return {
            "total_poles": total,
            "poles_with_remediation": remediated,
            "poles_without_remediation": total - remediated,
            "remediation_percentage": round(remediated / total * 100, 1) if total > 0 else 0
        }

    def export_to_kmz(self, output_path: str, include_normal: bool = False) -> str:
        if self.joined_gdf is None:
            raise ValueError("Must perform spatial join first")
        self.joined_gdf.to_file(output_path, driver="KML")
        return output_path
