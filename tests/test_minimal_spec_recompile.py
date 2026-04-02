#!/usr/bin/env python3
"""Test minimal spec and recompilation support.

Issue 1: Empty top-level sections should not appear in compiled-spec
Issue 2: Compiled-spec should be valid input (recompilable)
"""
import sys

import yaml
import tempfile
import subprocess
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "tools"))


def test_minimal_spec_no_empty_sections():
    """Test that minimal spec (only project) doesn't output empty top-level sections."""
    # Create minimal spec with only project
    minimal_spec = {
        "project": {
            "name": "Minimal Test",
            "domain": "testing"
        }
    }
    
    # Write to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(minimal_spec, f)
        spec_file = f.name
    
    try:
        # Run compiler
        output_dir = tempfile.mkdtemp()
        result = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / 'tools' / 'archcompiler.py'), spec_file, '-o', output_dir],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0, f"Compiler failed: {result.stderr}"
        
        # Read compiled-spec.yaml
        compiled_spec_path = Path(output_dir) / 'compiled-spec.yaml'
        with open(compiled_spec_path, 'r') as f:
            compiled_spec = yaml.safe_load(f)
        
        # Verify no empty top-level sections
        assert "project" in compiled_spec, "project should be present"
        assert "assumptions" in compiled_spec, "assumptions should be present"
        
        # These sections should NOT be present at top level if user didn't provide them
        # (they should only be in assumptions)
        if "constraints" in compiled_spec:
            # If present, must not be empty
            assert compiled_spec["constraints"], "constraints should not be empty dict"
        
        if "nfr" in compiled_spec:
            # If present, must not be empty
            assert compiled_spec["nfr"], "nfr should not be empty dict"
        
        if "operating_model" in compiled_spec:
            # If present, must not be empty
            assert compiled_spec["operating_model"], "operating_model should not be empty dict"
        
        # Assumptions should have defaults
        assert "constraints" in compiled_spec["assumptions"]
        assert "nfr" in compiled_spec["assumptions"]
        assert "operating_model" in compiled_spec["assumptions"]
        
        print("✅ test_minimal_spec_no_empty_sections passed")
        
    finally:
        import os
        if os.path.exists(spec_file):
            os.unlink(spec_file)


def test_compiled_spec_recompilation():
    """Test that compiled-spec can be used as input and produces same output."""
    # Create minimal spec
    minimal_spec = {
        "project": {
            "name": "Recompile Test",
            "domain": "testing"
        }
    }
    
    # Write to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(minimal_spec, f)
        spec_file = f.name
    
    try:
        # First compilation
        output_dir1 = tempfile.mkdtemp()
        result1 = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / 'tools' / 'archcompiler.py'), spec_file, '-o', output_dir1],
            capture_output=True,
            text=True
        )
        
        assert result1.returncode == 0, f"First compilation failed: {result1.stderr}"
        
        # Read first compiled-spec.yaml
        compiled_spec_path1 = Path(output_dir1) / 'compiled-spec.yaml'
        with open(compiled_spec_path1, 'r') as f:
            compiled_spec1 = f.read()
        
        # Second compilation - use first output as input
        output_dir2 = tempfile.mkdtemp()
        result2 = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / 'tools' / 'archcompiler.py'),
             str(compiled_spec_path1), '-o', output_dir2],
            capture_output=True,
            text=True
        )
        
        # Should not have validation errors
        assert result2.returncode == 0, f"Recompilation failed: {result2.stderr}"
        assert "Validation Error" not in result2.stderr, f"Schema validation failed: {result2.stderr}"
        
        # Read second compiled-spec.yaml
        compiled_spec_path2 = Path(output_dir2) / 'compiled-spec.yaml'
        with open(compiled_spec_path2, 'r') as f:
            compiled_spec2 = f.read()
        
        # Both outputs should be identical
        assert compiled_spec1 == compiled_spec2, "Recompilation produced different output"
        
        print("✅ test_compiled_spec_recompilation passed")
        
    finally:
        import os
        if os.path.exists(spec_file):
            os.unlink(spec_file)


def test_assumptions_properties_allowed():
    """Test that assumptions sections accept properties from defaults."""
    # Create minimal spec
    minimal_spec = {
        "project": {
            "name": "Assumptions Test",
            "domain": "testing"
        }
    }
    
    # Write to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(minimal_spec, f)
        spec_file = f.name
    
    try:
        # Run compiler
        output_dir = tempfile.mkdtemp()
        result = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / 'tools' / 'archcompiler.py'), spec_file, '-o', output_dir],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0, f"Compiler failed: {result.stderr}"
        
        # Read compiled-spec.yaml
        compiled_spec_path = Path(output_dir) / 'compiled-spec.yaml'
        with open(compiled_spec_path, 'r') as f:
            compiled_spec = yaml.safe_load(f)
        
        # Verify assumptions have expected properties
        assumptions = compiled_spec["assumptions"]
        
        # assumptions.constraints should have properties
        assert "cloud" in assumptions["constraints"]
        assert "language" in assumptions["constraints"]
        assert "platform" in assumptions["constraints"]
        
        # assumptions.nfr should have properties
        assert "availability" in assumptions["nfr"]
        assert "latency" in assumptions["nfr"]
        
        # assumptions.operating_model should have properties
        assert "on_call" in assumptions["operating_model"]
        assert "deploy_freq" in assumptions["operating_model"]
        assert "ops_team_size" in assumptions["operating_model"]
        assert "single_resource_monthly_ops_usd" in assumptions["operating_model"]
        assert "amortization_months" in assumptions["operating_model"]
        
        # assumptions.cost should have properties
        assert "intent" in assumptions["cost"]
        assert "ceilings" in assumptions["cost"]
        
        print("✅ test_assumptions_properties_allowed passed")
        
    finally:
        import os
        if os.path.exists(spec_file):
            os.unlink(spec_file)


def test_partial_assumptions_preserved_during_recompile():
    """Test that partial assumptions with custom values are preserved during recompilation."""
    # Create spec with partial assumptions (only operating_model with custom values)
    partial_spec = {
        "project": {"name": "Partial Test", "domain": "testing"},
        "assumptions": {
            "operating_model": {
                "on_call": True,  # Custom: differs from default (False)
                "deploy_freq": "daily",  # Custom: differs from default (weekly)
                "ops_team_size": 5  # Custom: differs from default (0)
            }
        }
    }

    # Write to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(partial_spec, f)
        spec_file = f.name

    try:
        # Compile the spec
        output_dir = tempfile.mkdtemp()
        result = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / 'tools' / 'archcompiler.py'), spec_file, '-o', output_dir],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0, f"Compilation failed: {result.stderr}"

        # Read compiled-spec.yaml
        compiled_spec_path = Path(output_dir) / 'compiled-spec.yaml'
        with open(compiled_spec_path, 'r') as f:
            compiled_spec = yaml.safe_load(f)

        # Verify user-provided custom values are preserved (not overwritten with defaults)
        operating_model = compiled_spec["assumptions"]["operating_model"]
        assert operating_model["on_call"] == True, "on_call should be preserved as True (not overwritten with default False)"
        assert operating_model["deploy_freq"] == "daily", "deploy_freq should be preserved as daily (not overwritten with default weekly)"
        assert operating_model["ops_team_size"] == 5, "ops_team_size should be preserved as 5 (not overwritten with default 0)"

        # Verify missing fields were added from defaults
        assert "single_resource_monthly_ops_usd" in operating_model, "Missing field single_resource_monthly_ops_usd should be added"
        assert operating_model["single_resource_monthly_ops_usd"] == 10000, "single_resource_monthly_ops_usd should have default value"
        assert "amortization_months" in operating_model, "Missing field amortization_months should be added"
        assert operating_model["amortization_months"] == 24, "amortization_months should have default value"

        # Verify other assumption sections were added (per user feedback: add missing sections)
        assert "constraints" in compiled_spec["assumptions"], "Missing section constraints should be added"
        assert "nfr" in compiled_spec["assumptions"], "Missing section nfr should be added"
        assert "cost" in compiled_spec["assumptions"], "Missing section cost should be added"

        print("✅ test_partial_assumptions_preserved_during_recompile passed")

    finally:
        import os
        if os.path.exists(spec_file):
            os.unlink(spec_file)


if __name__ == "__main__":
    test_minimal_spec_no_empty_sections()
    test_compiled_spec_recompilation()
    test_assumptions_properties_allowed()
    test_partial_assumptions_preserved_during_recompile()
    print("\n✅ All tests passed!")
