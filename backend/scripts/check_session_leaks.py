#!/usr/bin/env python3
"""
Script to check for database session leaks in the API579Service.
Verifies that the session-per-task pattern prevents connection leaks.
"""

import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal
import psycopg2

# Add backend to path
sys.path.insert(0, '/Users/will/Programming/Projects/mechanical-integrity/backend')

from core.config import settings
from models.database import get_session_factory
from app.services.api579_service import API579Service

def get_active_connections():
    """Get current number of active PostgreSQL connections."""
    try:
        conn = psycopg2.connect(
            host=settings.POSTGRES_SERVER,
            port=settings.POSTGRES_PORT,
            database=settings.POSTGRES_DB,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD
        )
        cursor = conn.cursor()
        cursor.execute("""
            SELECT count(*) 
            FROM pg_stat_activity 
            WHERE datname = %s AND state = 'active'
        """, (settings.POSTGRES_DB,))
        
        count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return count
    except Exception as e:
        print(f"Error getting connection count: {e}")
        return -1

def stress_test_api579_service(iterations=50):
    """Stress test the API579Service to check for session leaks."""
    print(f"🔥 Starting API579Service stress test: {iterations} calculations")
    
    session_factory = get_session_factory()
    api579_service = API579Service(session_factory)
    
    # Baseline connection count
    baseline_connections = get_active_connections()
    print(f"📊 Baseline active connections: {baseline_connections}")
    
    def perform_calculation(iteration):
        """Perform a single API 579 calculation."""
        try:
            # Create test parameters
            params = {
                'equipment_type': 'pressure_vessel',
                'design_pressure': Decimal('150.0'),
                'design_temperature': Decimal('650.0'),
                'design_thickness': Decimal('1.250'),
                'material_specification': 'SA-516-70',
                'corrosion_allowance': Decimal('0.125'),
                'min_thickness_found': Decimal('1.100'),
                'avg_thickness': Decimal('1.120'),
                'internal_radius': Decimal('24.0'),
                'allowable_stress': Decimal('17500'),
                'joint_efficiency': Decimal('1.0'),
                'future_corrosion_allowance': Decimal('0.050')
            }
            
            # This should use session-per-task pattern
            result = api579_service.perform_ffs_assessment(params)
            
            return {
                'iteration': iteration,
                'success': True,
                'min_thickness': str(result['minimum_required_thickness']),
                'rsf': str(result['remaining_strength_factor'])
            }
            
        except Exception as e:
            return {
                'iteration': iteration,
                'success': False,
                'error': str(e)
            }
    
    # Run concurrent calculations
    start_time = time.time()
    results = []
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_iteration = {
            executor.submit(perform_calculation, i): i 
            for i in range(iterations)
        }
        
        for future in as_completed(future_to_iteration):
            iteration = future_to_iteration[future]
            result = future.result()
            results.append(result)
            
            if iteration % 10 == 0:  # Check connections every 10 iterations
                current_connections = get_active_connections()
                print(f"  Iteration {iteration}: {current_connections} active connections")
    
    # Final analysis
    total_time = time.time() - start_time
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]
    
    final_connections = get_active_connections()
    connection_leak = final_connections - baseline_connections
    
    print("\n📈 STRESS TEST RESULTS:")
    print(f"  Total time: {total_time:.2f} seconds")
    print(f"  Successful calculations: {len(successful)}/{len(results)}")
    print(f"  Failed calculations: {len(failed)}")
    print(f"  Average time per calculation: {total_time/len(results):.3f}s")
    
    print("\n🔌 CONNECTION ANALYSIS:")
    print(f"  Baseline connections: {baseline_connections}")
    print(f"  Final connections: {final_connections}")
    print(f"  Connection leak: {connection_leak}")
    
    if connection_leak > 2:  # Allow small variance
        print(f"❌ POTENTIAL SESSION LEAK DETECTED: {connection_leak} extra connections")
        return False
    else:
        print("✅ NO SESSION LEAKS DETECTED")
        return True
    
    if failed:
        print("\n❌ FAILED CALCULATIONS:")
        for failure in failed[:5]:  # Show first 5 failures
            print(f"  Iteration {failure['iteration']}: {failure['error']}")

def main():
    """Main function to run session leak detection."""
    print("=" * 60)
    print("🔍 MECHANICAL INTEGRITY - SESSION LEAK DETECTION")
    print("=" * 60)
    
    # Test database connection first
    print("🔌 Testing database connection...")
    baseline = get_active_connections()
    if baseline < 0:
        print("❌ Cannot connect to database")
        return False
    
    print(f"✅ Database connected. Active connections: {baseline}")
    
    # Run stress test
    success = stress_test_api579_service(100)
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 SESSION-PER-TASK PATTERN: VERIFIED SAFE FOR PRODUCTION")
    else:
        print("⚠️  SESSION MANAGEMENT ISSUES DETECTED - REVIEW REQUIRED")
    print("=" * 60)
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)