"""
Stress tests for concurrent inspection processing.

Tests system behavior under high load with multiple simultaneous 
inspection data entries, calculations, and database operations.
Critical for ensuring data integrity in production environments.
"""
import pytest
import asyncio
import threading
import time
from decimal import Decimal
from datetime import datetime, timedelta
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any
import random
import psutil
import gc
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError, OperationalError

from models.base import Base
from models.equipment import Equipment, EquipmentType
from models.inspection import InspectionRecord, ThicknessReading, API579Calculation
from app.calculations.dual_path_calculator import API579Calculator
from app.services.api579_service import API579Service
from core.config import settings


class TestConcurrentInspectionProcessing:
    """Stress tests for concurrent inspection data processing."""
    
    @pytest.fixture(scope="function")
    def stress_test_db(self):
        """Set up database with connection pooling for stress testing."""
        # Use PostgreSQL-like settings for realistic testing
        engine = create_engine(
            "sqlite:///:memory:",
            echo=False,
            pool_pre_ping=True,
            pool_recycle=3600,
            pool_size=10
        )
        Base.metadata.create_all(engine)
        
        # Create test equipment
        TestSession = sessionmaker(bind=engine)
        session = TestSession()
        
        # Create multiple test vessels
        for i in range(10):
            equipment = Equipment(
                tag_number=f"V-{i+100:03d}-STRESS",
                description=f"Stress Test Vessel {i+1}",
                equipment_type=EquipmentType.PRESSURE_VESSEL,
                design_pressure=1000.0 + (i * 100),
                design_temperature=600.0 + (i * 10),
                design_thickness=1.250,
                material_specification="SA-516-70",
                corrosion_allowance=0.125,
                service_description="Stress Test Service",
                installation_date=datetime(2010, 1, 1)
            )
            session.add(equipment)
        
        session.commit()
        session.close()
        
        yield engine
    
    def create_random_inspection_data(self, vessel_number: int) -> Dict[str, Any]:
        """Generate random but realistic inspection data."""
        base_thickness = Decimal('1.250')
        metal_loss = Decimal(str(random.uniform(0.001, 0.150)))  # 0.1-15% metal loss
        current_thickness = base_thickness - metal_loss
        
        num_readings = random.randint(5, 20)  # Variable number of CMLs
        
        thickness_readings = []
        for j in range(num_readings):
            # Add some variation around the base thickness
            variation = Decimal(str(random.uniform(-0.020, 0.020)))
            reading_thickness = current_thickness + variation
            
            thickness_readings.append({
                "cml_number": f"CML-{j+1:02d}",
                "location_description": f"Location {j+1} - Stress Test",
                "thickness_measured": reading_thickness,
                "design_thickness": base_thickness,
                "previous_thickness": base_thickness - (metal_loss * Decimal('0.5')),
                "measurement_confidence": Decimal('95.00')
            })
        
        return {
            "equipment_tag": f"V-{vessel_number+100:03d}-STRESS",
            "inspection_date": datetime.utcnow() - timedelta(days=1),
            "inspection_type": "UT",
            "inspector_name": f"Stress Tester {threading.current_thread().ident}",
            "inspector_certification": "UT-III-STRESS",
            "report_number": f"STRESS-{uuid4().hex[:8]}",
            "thickness_readings": thickness_readings,
            "findings": "Automated stress test inspection",
            "recommendations": "Continue stress testing"
        }
    
    def process_single_inspection(self, session_factory, vessel_number: int, iteration: int) -> Dict[str, Any]:
        """Process a single inspection in a separate thread."""
        session = session_factory()
        start_time = time.time()
        
        try:
            # Generate inspection data
            inspection_data = self.create_random_inspection_data(vessel_number)
            
            # Find equipment
            equipment = session.query(Equipment).filter(
                Equipment.tag_number == inspection_data["equipment_tag"]
            ).first()
            
            if not equipment:
                raise ValueError(f"Equipment {inspection_data['equipment_tag']} not found")
            
            # Create inspection record
            min_thickness = min(r["thickness_measured"] for r in inspection_data["thickness_readings"])
            avg_thickness = sum(r["thickness_measured"] for r in inspection_data["thickness_readings"]) / len(inspection_data["thickness_readings"])
            
            inspection = InspectionRecord(
                equipment_id=equipment.id,
                inspection_date=inspection_data["inspection_date"],
                inspection_type=inspection_data["inspection_type"],
                inspector_name=inspection_data["inspector_name"],
                inspector_certification=inspection_data["inspector_certification"],
                report_number=inspection_data["report_number"],
                thickness_readings={},  # JSON field
                min_thickness_found=min_thickness,
                avg_thickness=avg_thickness,
                findings=inspection_data["findings"],
                recommendations=inspection_data["recommendations"]
            )
            
            session.add(inspection)
            session.flush()  # Get ID without committing
            
            # Add thickness readings
            for reading_data in inspection_data["thickness_readings"]:
                reading = ThicknessReading(
                    inspection_record_id=inspection.id,
                    **reading_data
                )
                session.add(reading)
            
            session.commit()
            
            # Perform API 579 calculations
            calculator = API579Calculator()
            
            # Calculate minimum required thickness
            t_min_result = calculator.calculate_minimum_required_thickness(
                pressure=Decimal(str(equipment.design_pressure)),
                radius=Decimal('24.0'),  # Assume standard vessel
                stress=Decimal('17500.0'),
                efficiency=Decimal('1.0')
            )
            
            # Calculate RSF
            rsf_result = calculator.calculate_remaining_strength_factor(
                current_thickness=min_thickness,
                minimum_thickness=t_min_result.value,
                nominal_thickness=Decimal(str(equipment.design_thickness))
            )
            
            # Store calculation results
            calculation = API579Calculation(
                inspection_record_id=inspection.id,
                calculation_type="Level 1 - Stress Test",
                calculation_method="Automated Stress Testing",
                performed_by=f"Stress Test Thread {threading.current_thread().ident}",
                input_parameters={
                    "design_pressure": str(equipment.design_pressure),
                    "current_thickness": str(min_thickness),
                    "calculation_timestamp": datetime.utcnow().isoformat()
                },
                minimum_required_thickness=t_min_result.value,
                remaining_strength_factor=rsf_result.value,
                maximum_allowable_pressure=Decimal('1000.0'),  # Mock value
                remaining_life_years=Decimal('20.0'),  # Mock value
                fitness_for_service="FIT" if rsf_result.value > Decimal('0.9') else "CONDITIONAL",
                risk_level="MEDIUM",
                recommendations="Stress test completed successfully",
                confidence_score=Decimal('95.0')
            )
            
            session.add(calculation)
            session.commit()
            
            processing_time = time.time() - start_time
            
            return {
                "success": True,
                "vessel_number": vessel_number,
                "iteration": iteration,
                "thread_id": threading.current_thread().ident,
                "processing_time": processing_time,
                "inspection_id": inspection.id,
                "calculation_id": calculation.id,
                "rsf_value": float(rsf_result.value),
                "memory_usage_mb": psutil.Process().memory_info().rss / 1024 / 1024
            }
            
        except Exception as e:
            session.rollback()
            return {
                "success": False,
                "vessel_number": vessel_number,
                "iteration": iteration,
                "thread_id": threading.current_thread().ident,
                "error": str(e),
                "error_type": type(e).__name__
            }
        finally:
            session.close()
    
    @pytest.mark.stress
    def test_concurrent_inspection_creation(self, stress_test_db):
        """Test creating multiple inspections concurrently."""
        SessionFactory = sessionmaker(bind=stress_test_db)
        
        num_threads = 20
        inspections_per_thread = 5
        total_inspections = num_threads * inspections_per_thread
        
        print(f"\n🔥 Stress Test: {total_inspections} inspections across {num_threads} threads")
        
        start_time = time.time()
        results = []
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            # Submit all tasks
            future_to_params = {}
            for thread_idx in range(num_threads):
                for iteration in range(inspections_per_thread):
                    vessel_number = thread_idx % 10  # Distribute across 10 vessels
                    future = executor.submit(
                        self.process_single_inspection,
                        SessionFactory,
                        vessel_number,
                        iteration
                    )
                    future_to_params[future] = (thread_idx, iteration)
            
            # Collect results
            for future in as_completed(future_to_params):
                result = future.result()
                results.append(result)
                
                if result["success"]:
                    print(f"✅ Thread {result['thread_id']}: Vessel {result['vessel_number']}, "
                          f"Iteration {result['iteration']}, Time: {result['processing_time']:.2f}s")
                else:
                    print(f"❌ Thread {result['thread_id']}: {result['error_type']}: {result['error']}")
        
        total_time = time.time() - start_time
        
        # Analyze results
        successful_results = [r for r in results if r["success"]]
        failed_results = [r for r in results if not r["success"]]
        
        success_rate = len(successful_results) / len(results) * 100
        avg_processing_time = sum(r["processing_time"] for r in successful_results) / len(successful_results)
        
        print(f"\n📊 Stress Test Results:")
        print(f"   Total Time: {total_time:.2f}s")
        print(f"   Success Rate: {success_rate:.1f}% ({len(successful_results)}/{len(results)})")
        print(f"   Average Processing Time: {avg_processing_time:.3f}s")
        print(f"   Throughput: {len(successful_results)/total_time:.1f} inspections/second")
        
        if failed_results:
            print(f"   Failures:")
            error_counts = {}
            for result in failed_results:
                error_type = result["error_type"]
                error_counts[error_type] = error_counts.get(error_type, 0) + 1
            
            for error_type, count in error_counts.items():
                print(f"     {error_type}: {count}")
        
        # Assertions for stress test
        assert success_rate >= 95.0, f"Success rate {success_rate}% below acceptable threshold"
        assert avg_processing_time < 5.0, f"Average processing time {avg_processing_time}s too high"
        
        # Check for database consistency
        session = SessionFactory()
        try:
            inspection_count = session.query(InspectionRecord).count()
            calculation_count = session.query(API579Calculation).count()
            thickness_reading_count = session.query(ThicknessReading).count()
            
            print(f"   Database Records Created:")
            print(f"     Inspections: {inspection_count}")
            print(f"     Calculations: {calculation_count}")
            print(f"     Thickness Readings: {thickness_reading_count}")
            
            assert inspection_count == len(successful_results), "Inspection count mismatch"
            assert calculation_count == len(successful_results), "Calculation count mismatch"
            
        finally:
            session.close()
    
    @pytest.mark.stress
    def test_memory_usage_under_load(self, stress_test_db):
        """Test memory usage during sustained inspection processing."""
        SessionFactory = sessionmaker(bind=stress_test_db)
        
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
        print(f"\n💾 Initial Memory Usage: {initial_memory:.1f} MB")
        
        memory_samples = []
        num_iterations = 50
        
        for i in range(num_iterations):
            # Process inspection
            result = self.process_single_inspection(SessionFactory, i % 10, i)
            
            if result["success"]:
                memory_samples.append(result["memory_usage_mb"])
            
            # Force garbage collection every 10 iterations
            if i % 10 == 0:
                gc.collect()
                current_memory = psutil.Process().memory_info().rss / 1024 / 1024
                print(f"   Iteration {i}: {current_memory:.1f} MB")
        
        final_memory = psutil.Process().memory_info().rss / 1024 / 1024
        memory_growth = final_memory - initial_memory
        
        print(f"   Final Memory Usage: {final_memory:.1f} MB")
        print(f"   Memory Growth: {memory_growth:.1f} MB")
        print(f"   Memory Per Inspection: {memory_growth/num_iterations:.2f} MB")
        
        # Check for memory leaks
        assert memory_growth < 100, f"Excessive memory growth: {memory_growth:.1f} MB"
        
        # Check memory usage consistency
        if len(memory_samples) > 10:
            avg_memory = sum(memory_samples) / len(memory_samples)
            max_memory = max(memory_samples)
            memory_variance = max_memory - avg_memory
            
            print(f"   Average Memory: {avg_memory:.1f} MB")
            print(f"   Peak Memory: {max_memory:.1f} MB")
            print(f"   Memory Variance: {memory_variance:.1f} MB")
            
            assert memory_variance < 50, f"High memory variance: {memory_variance:.1f} MB"
    
    @pytest.mark.stress 
    def test_database_connection_pool_exhaustion(self, stress_test_db):
        """Test behavior when database connection pool is exhausted."""
        # Create engine with small connection pool
        small_pool_engine = create_engine(
            "sqlite:///:memory:",
            echo=False,
            pool_size=2  # Very small pool
        )
        Base.metadata.create_all(small_pool_engine)
        
        # Add test equipment
        SessionFactory = sessionmaker(bind=small_pool_engine)
        session = SessionFactory()
        equipment = Equipment(
            tag_number="V-101-POOL-TEST",
            description="Pool Test Vessel",
            equipment_type=EquipmentType.PRESSURE_VESSEL,
            design_pressure=1000.0,
            design_temperature=600.0,
            design_thickness=1.250,
            material_specification="SA-516-70",
            corrosion_allowance=0.125,
            service_description="Pool Test",
            installation_date=datetime(2010, 1, 1)
        )
        session.add(equipment)
        session.commit()
        session.close()
        
        # Test with more threads than pool can handle
        num_threads = 10  # Much more than pool size (3 total)
        results = []
        
        def long_running_inspection(session_factory, thread_id):
            """Simulate a long-running inspection that holds connections."""
            session = session_factory()
            try:
                # Hold connection for extended time
                time.sleep(0.5)  # Simulate slow processing
                
                result = self.process_single_inspection(session_factory, 0, thread_id)
                return result
            except Exception as e:
                return {
                    "success": False,
                    "thread_id": thread_id,
                    "error": str(e),
                    "error_type": type(e).__name__
                }
            finally:
                session.close()
        
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [
                executor.submit(long_running_inspection, SessionFactory, i)
                for i in range(num_threads)
            ]
            
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
        
        total_time = time.time() - start_time
        
        successful_results = [r for r in results if r["success"]]
        failed_results = [r for r in results if not r["success"]]
        
        print(f"\n🔗 Connection Pool Test Results:")
        print(f"   Total Time: {total_time:.2f}s")
        print(f"   Successful: {len(successful_results)}")
        print(f"   Failed: {len(failed_results)}")
        
        # Should handle pool exhaustion gracefully
        assert len(successful_results) > 0, "No successful operations with limited pool"
        
        # Check for timeout errors (expected with small pool)
        timeout_errors = [r for r in failed_results if "timeout" in r.get("error", "").lower()]
        if timeout_errors:
            print(f"   Timeout errors (expected): {len(timeout_errors)}")
    
    @pytest.mark.stress
    def test_calculation_precision_under_concurrent_load(self, stress_test_db):
        """Test that calculation precision is maintained under concurrent load."""
        SessionFactory = sessionmaker(bind=stress_test_db)
        calculator = API579Calculator()
        
        # Test parameters
        test_pressure = Decimal('1000.0')
        test_radius = Decimal('24.0')
        test_stress = Decimal('17500.0')
        test_efficiency = Decimal('1.0')
        
        # Expected result (calculated once for reference)
        expected_result = calculator.calculate_minimum_required_thickness(
            test_pressure, test_radius, test_stress, test_efficiency
        )
        expected_value = expected_result.value
        
        print(f"\n🔢 Precision Test - Expected Result: {expected_value}")
        
        def concurrent_calculation(thread_id):
            """Perform calculation in separate thread."""
            try:
                result = calculator.calculate_minimum_required_thickness(
                    test_pressure, test_radius, test_stress, test_efficiency
                )
                
                return {
                    "success": True,
                    "thread_id": thread_id,
                    "calculated_value": result.value,
                    "primary_value": result.primary_value,
                    "secondary_value": result.secondary_value,
                    "difference_from_expected": abs(result.value - expected_value)
                }
            except Exception as e:
                return {
                    "success": False,
                    "thread_id": thread_id,
                    "error": str(e)
                }
        
        # Run concurrent calculations
        num_threads = 50
        results = []
        
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [
                executor.submit(concurrent_calculation, i)
                for i in range(num_threads)
            ]
            
            for future in as_completed(futures):
                results.append(future.result())
        
        # Analyze precision consistency
        successful_results = [r for r in results if r["success"]]
        failed_results = [r for r in results if not r["success"]]
        
        print(f"   Successful calculations: {len(successful_results)}")
        print(f"   Failed calculations: {len(failed_results)}")
        
        assert len(failed_results) == 0, f"Calculation failures under load: {failed_results}"
        
        # Check precision consistency
        max_difference = max(r["difference_from_expected"] for r in successful_results)
        avg_difference = sum(r["difference_from_expected"] for r in successful_results) / len(successful_results)
        
        print(f"   Maximum difference from expected: {max_difference}")
        print(f"   Average difference from expected: {avg_difference}")
        
        # All calculations should be identical (deterministic)
        assert max_difference == Decimal('0'), f"Calculation precision varies under load: {max_difference}"
        
        # Verify dual-path consistency
        for result in successful_results:
            primary_secondary_diff = abs(result["primary_value"] - result["secondary_value"])
            relative_diff = primary_secondary_diff / result["primary_value"] if result["primary_value"] != 0 else 0
            
            assert relative_diff <= calculator.THICKNESS_TOLERANCE, (
                f"Dual-path verification failed under load: {relative_diff} > {calculator.THICKNESS_TOLERANCE}"
            )