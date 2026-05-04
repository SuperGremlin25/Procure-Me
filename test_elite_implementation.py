"""
Quick Start Test Script

Run this to verify the elite implementation is working correctly.
"""

import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def test_mistral_client():
    """Test Mistral OCR client."""
    print("\n" + "="*60)
    print("Testing Mistral OCR Client")
    print("="*60)
    
    try:
        from src.mistral_ocr_client import MockMistralOCRClient, RemedyReport
        
        # Use mock client for testing
        client = MockMistralOCRClient()
        
        # Test extraction
        import asyncio
        report = asyncio.run(client.extract_remedy_report(b"dummy_pdf", "aep"))
        
        print(f"✅ Utility Company: {report.utility_company}")
        print(f"✅ Total Poles: {report.total_poles}")
        print(f"✅ Actions: {len(report.actions)}")
        
        for action in report.actions[:3]:
            print(f"   - Pole {action.pole_id}: {action.action_type}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed: {str(e)}")
        return False


def test_spatial_join():
    """Test GIS spatial join."""
    print("\n" + "="*60)
    print("Testing GIS Spatial Join")
    print("="*60)
    
    try:
        from src.gis_spatial_join import GISRemedyIntegrator
        
        integrator = GISRemedyIntegrator()
        print("✅ GISRemedyIntegrator initialized")
        
        # Test with mock data
        mock_remedy = {
            'utility_company': 'AEP',
            'report_date': '2024-03-13',
            'total_poles': 3,
            'actions': [
                {
                    'pole_id': 'TEST-001',
                    'action_type': 'COMM_MOVE',
                    'comm_move': True
                }
            ]
        }
        
        report = integrator.load_remedy_report(mock_remedy)
        print(f"✅ Loaded remedy report: {report.total_poles} poles")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed: {str(e)}")
        return False


def test_action_mapper():
    """Test remedy action mapper."""
    print("\n" + "="*60)
    print("Testing Remedy Action Mapper")
    print("="*60)
    
    try:
        from src.remedy_action_mapper import RemedyActionMapper
        
        mapper = RemedyActionMapper()
        print("✅ RemedyActionMapper initialized")
        
        # Test action mapping
        materials, labor = mapper.map_action_to_requirements(
            'COMM_MOVE',
            attachment_height=25.5
        )
        
        print(f"✅ COMM_MOVE mapped to:")
        print(f"   - {len(materials)} materials")
        print(f"   - {len(labor)} labor tasks")
        
        if materials:
            print(f"   - Example material: {materials[0].description}")
        if labor:
            print(f"   - Example labor: {labor[0].description} ({labor[0].hours} hrs)")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed: {str(e)}")
        return False


def test_database_connections():
    """Test database connections."""
    print("\n" + "="*60)
    print("Testing Database Connections")
    print("="*60)
    
    try:
        from src.materials_db import MaterialsDatabase
        from src.labor_db import LaborDatabase
        
        materials_db = MaterialsDatabase()
        print(f"✅ Materials DB: {len(materials_db.materials)} items")
        
        labor_db = LaborDatabase()
        print(f"✅ Labor DB loaded")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed: {str(e)}")
        return False


def main():
    """Run all tests."""
    print("\n" + "="*70)
    print("ELITE IMPLEMENTATION - QUICK START TEST")
    print("="*70)
    print("\nThis tests the Vision-to-Vector pipeline components.")
    print("Make sure you have installed: pip install -r requirements_gis.txt")
    
    tests = [
        ("Mistral OCR Client", test_mistral_client),
        ("GIS Spatial Join", test_spatial_join),
        ("Remedy Action Mapper", test_action_mapper),
        ("Database Connections", test_database_connections),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ {name} crashed: {str(e)}")
            results.append((name, False))
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! The elite implementation is ready.")
        print("\nNext steps:")
        print("1. Get Mistral API key from mistral.ai")
        print("2. Deploy Cloudflare Worker: cd cloudflare-worker && wrangler deploy")
        print("3. Deploy Python backend: railway up")
        print("4. Test with real AEP PDF")
    else:
        print("\n⚠️  Some tests failed. Check the errors above.")
        print("\nCommon issues:")
        print("- Missing dependencies: pip install -r requirements_gis.txt")
        print("- GIS libraries: pip install geopandas shapely fiona")
        print("- Database files: Ensure materials_data.json exists")
    
    print("\n" + "="*70)


if __name__ == "__main__":
    main()
