"""
ReflectSort — Unit Tests for Sensor Simulator
Test Module: tests.test_sensor_simulator

Author: Ajitesh Karan (2500032236)
Team: ML-ESD-TEAM-117
"""

import pytest
from reflectsort_member4.schemas import ValidationError
from reflectsort_member4.sensor_simulator import (
    DEMO_FIXTURE_PROFILES,
    SensorSimulator,
    SensorSimulatorConfig,
)


def test_reproducible_output_with_fixed_seed() -> None:
    """Verify that identical random seeds produce exact bit-for-bit identical sensor records."""
    sim1 = SensorSimulator(SensorSimulatorConfig(random_seed=42, noise_std_dev=20.0))
    sim2 = SensorSimulator(SensorSimulatorConfig(random_seed=42, noise_std_dev=20.0))

    r1 = sim1.generate_reading("SEED-100", "RUN-01", profile_name="LIGHT_GRAIN")
    r2 = sim2.generate_reading("SEED-100", "RUN-01", profile_name="LIGHT_GRAIN")

    assert r1.sample_LDR == r2.sample_LDR
    assert r1.ambient_LDR == r2.ambient_LDR
    assert r1.reference_value == r2.reference_value
    assert r1.derived_features == r2.derived_features


def test_zero_noise_yields_nominal_fixture_values() -> None:
    """Verify that setting noise to zero produces exactly the nominal profile baseline values."""
    sim = SensorSimulator(SensorSimulatorConfig(noise_std_dev=0.0))

    for profile_name, fixture in DEMO_FIXTURE_PROFILES.items():
        rec = sim.generate_reading("SEED-001", "RUN-01", profile_name=profile_name)
        assert rec.sample_LDR == pytest.approx(fixture.nominal_sample_adc)
        assert rec.ambient_LDR == pytest.approx(fixture.nominal_ambient_adc)
        assert rec.reference_value == pytest.approx(fixture.nominal_reference_adc)
        assert rec.data_source == "simulated"


def test_all_demo_profiles_generate_valid_records() -> None:
    """Verify all standard demo profiles produce valid records within 12-bit ADC range."""
    sim = SensorSimulator(SensorSimulatorConfig(random_seed=123, noise_std_dev=15.0))
    for profile_name in DEMO_FIXTURE_PROFILES:
        rec = sim.generate_reading("SEED-001", "RUN-01", profile_name=profile_name)
        assert 0.0 <= rec.sample_LDR <= 4095.0
        assert 0.0 <= rec.ambient_LDR <= 4095.0
        assert 0.0 <= rec.reference_value <= 4095.0
        assert rec.data_source == "simulated"


def test_generate_batch() -> None:
    """Verify batch generation count, prefixing, and deterministic sampling."""
    sim = SensorSimulator(SensorSimulatorConfig(random_seed=999))
    batch = sim.generate_batch(count=10, run_id="BATCH-001", specimen_prefix="GRAIN")

    assert len(batch) == 10
    for idx, rec in enumerate(batch, start=1):
        assert rec.specimen_id == f"GRAIN-{idx:04d}"
        assert rec.run_id == "BATCH-001"
        assert rec.data_source == "simulated"
        assert 0.0 <= rec.sample_LDR <= 4095.0


def test_invalid_batch_count() -> None:
    """Verify that batch count <= 0 raises ValidationError."""
    sim = SensorSimulator()
    with pytest.raises(ValidationError):
        sim.generate_batch(count=0, run_id="BATCH-001")
    with pytest.raises(ValidationError):
        sim.generate_batch(count=-5, run_id="BATCH-001")


def test_invalid_simulator_config() -> None:
    """Verify rejection of invalid configuration parameters."""
    with pytest.raises(ValidationError):
        SensorSimulatorConfig(min_adc_value=5000, max_adc_value=1000).validate()
    with pytest.raises(ValidationError):
        SensorSimulatorConfig(noise_std_dev=-10.0).validate()


def test_model_feature_export() -> None:
    """Verify that sensor record produces the expected feature dictionary for ML model."""
    sim = SensorSimulator(SensorSimulatorConfig(random_seed=77))
    rec = sim.generate_reading("SEED-005", "RUN-01", profile_name="DARK_GRAIN")
    features = rec.to_model_features()

    assert "sample_LDR" in features
    assert "ambient_LDR" in features
    assert "reference_value" in features
    assert "differential_LDR" in features
    assert "contrast_ratio" in features
