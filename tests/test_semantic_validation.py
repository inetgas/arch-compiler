#!/usr/bin/env python3
"""
Tests for semantic validation in compiler.

Tests logical consistency checks for contradictory spec configurations.
"""

import sys
import subprocess
from pathlib import Path
import tempfile
import yaml

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def run_compiler_on_spec(spec_dict):
    """
    Run compiler on a spec dictionary and return success/error.

    Returns:
        (success: bool, output: str)
    """
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(spec_dict, f)
        spec_file = f.name

    try:
        result = subprocess.run(
            [sys.executable, 'tools/archcompiler.py', spec_file, '-o', '/tmp/test-semantic-validation'],
            capture_output=True,
            text=True,
            timeout=10
        )
        return (result.returncode == 0, result.stdout + result.stderr)
    finally:
        Path(spec_file).unlink()


def test_multi_tenancy_vs_tenant_isolation():
    """
    Test multi_tenancy feature flag vs tenant_isolation value consistency.

    Enforcement is via tenancy-* pattern requires_constraints (not compiler heuristic).
    When tenant_isolation is set, the matching tenancy pattern is selected; its
    requires_constraints: multi_tenancy == true then rejects specs with multi_tenancy=false.
    """

    print("Testing multi_tenancy vs tenant_isolation validation...")

    # Test 1: SHOULD REJECT - multi_tenancy=false + schema-per-tenant
    # tenancy-schema-per-tenant is selected (supports_nfr activation gate matches),
    # then requires_constraints: multi_tenancy == true fails.
    spec = {
        'project': {'name': 'Test', 'domain': 'test'},
        'functional': {'summary': 'Test'},
        'constraints': {
            'platform': 'api',
            'cloud': 'aws',
            'language': 'python',
            'features': {'multi_tenancy': False}
        },
        'nfr': {
            'security': {'tenant_isolation': 'schema-per-tenant'}
        }
    }
    success, output = run_compiler_on_spec(spec)
    assert not success, "Should reject multi_tenancy=false with schema-per-tenant"
    assert "Constraints/NFRs trade-off requirements not met" in output, f"Expected pattern requirements error, got: {output}"
    assert "tenancy-schema-per-tenant" in output, f"Expected tenancy pattern ID in output: {output}"
    assert "multi_tenancy" in output
    print("  ✓ Correctly rejects: multi_tenancy=false + schema-per-tenant")

    # Test 2: SHOULD REJECT - multi_tenancy=false + shared-db-row-level
    spec['nfr']['security']['tenant_isolation'] = 'shared-db-row-level'
    success, output = run_compiler_on_spec(spec)
    assert not success, "Should reject multi_tenancy=false with shared-db-row-level"
    assert "Constraints/NFRs trade-off requirements not met" in output
    assert "tenancy-shared-db-row-level" in output, f"Expected tenancy pattern ID in output: {output}"
    print("  ✓ Correctly rejects: multi_tenancy=false + shared-db-row-level")

    # Test 3: SHOULD REJECT - multi_tenancy=false + per-tenant-db
    spec['nfr']['security']['tenant_isolation'] = 'per-tenant-db'
    success, output = run_compiler_on_spec(spec)
    assert not success, "Should reject multi_tenancy=false with per-tenant-db"
    assert "Constraints/NFRs trade-off requirements not met" in output
    assert "tenancy-database-per-tenant" in output, f"Expected tenancy pattern ID in output: {output}"
    print("  ✓ Correctly rejects: multi_tenancy=false + per-tenant-db")

    # Test 4: SHOULD ACCEPT - multi_tenancy=true + schema-per-tenant
    spec['constraints']['features']['multi_tenancy'] = True
    spec['nfr']['security']['tenant_isolation'] = 'schema-per-tenant'
    success, output = run_compiler_on_spec(spec)
    assert success, f"Should accept multi_tenancy=true with schema-per-tenant. Error: {output}"
    print("  ✓ Correctly accepts: multi_tenancy=true + schema-per-tenant")

    # Test 5: SHOULD ACCEPT - multi_tenancy=false + n/a
    spec['constraints']['features']['multi_tenancy'] = False
    spec['nfr']['security']['tenant_isolation'] = 'n/a'
    success, output = run_compiler_on_spec(spec)
    assert success, f"Should accept multi_tenancy=false with tenant_isolation=n/a. Error: {output}"
    print("  ✓ Correctly accepts: multi_tenancy=false + tenant_isolation=n/a")

    # Test 6: SHOULD ACCEPT - multi_tenancy=false + unknown
    spec['nfr']['security']['tenant_isolation'] = 'unknown'
    success, output = run_compiler_on_spec(spec)
    assert success, f"Should accept multi_tenancy=false with tenant_isolation=unknown. Error: {output}"
    print("  ✓ Correctly accepts: multi_tenancy=false + tenant_isolation=unknown")

    # Test 7: SHOULD ACCEPT - multi_tenancy not specified (defaults to false) + n/a
    del spec['constraints']['features']
    spec['nfr']['security']['tenant_isolation'] = 'n/a'
    success, output = run_compiler_on_spec(spec)
    assert success, f"Should accept when multi_tenancy not specified. Error: {output}"
    print("  ✓ Correctly accepts: multi_tenancy not specified + tenant_isolation=n/a")


def test_tenant_count_vs_multi_tenancy():
    """Test tenantCount vs multi_tenancy flag consistency."""

    print("Testing tenantCount vs multi_tenancy validation...")

    # Test 1: SHOULD REJECT - tenantCount > 1 but multi_tenancy=false
    spec = {
        'project': {'name': 'Test', 'domain': 'test'},
        'functional': {'summary': 'Test'},
        'constraints': {
            'platform': 'api',
            'cloud': 'aws',
            'language': 'python',
            'tenantCount': 100,
            'features': {'multi_tenancy': False}
        }
    }
    success, output = run_compiler_on_spec(spec)
    assert not success, "Should reject tenantCount > 1 with multi_tenancy=false"
    assert "tenantcount" in output.lower()
    print("  ✓ Correctly rejects: tenantCount=100 + multi_tenancy=false")

    # Test 2: SHOULD REJECT - tenantCount = 1 but multi_tenancy=true
    spec = {
        'project': {'name': 'Test', 'domain': 'test'},
        'functional': {'summary': 'Test'},
        'constraints': {
            'platform': 'api',
            'cloud': 'aws',
            'language': 'python',
            'tenantCount': 1,
            'features': {'multi_tenancy': True}
        }
    }
    success, output = run_compiler_on_spec(spec)
    assert not success, "Should reject tenantCount=1 with multi_tenancy=true"
    assert "tenantcount" in output.lower()
    print("  ✓ Correctly rejects: tenantCount=1 + multi_tenancy=true")

    # Test 3: SHOULD ACCEPT - tenantCount > 1 and multi_tenancy=true + tenant_isolation specified
    # multi-tenancy-isolation-required enforces tenant_isolation when multi_tenancy=true
    spec = {
        'project': {'name': 'Test', 'domain': 'test'},
        'functional': {'summary': 'Test'},
        'constraints': {
            'platform': 'api',
            'cloud': 'aws',
            'language': 'python',
            'tenantCount': 100,
            'features': {'multi_tenancy': True}
        },
        'nfr': {
            'security': {'tenant_isolation': 'schema-per-tenant'}
        }
    }
    success, output = run_compiler_on_spec(spec)
    assert success, f"Should accept tenantCount > 1 with multi_tenancy=true + tenant_isolation. Error: {output}"
    print("  ✓ Correctly accepts: tenantCount=100 + multi_tenancy=true + tenant_isolation=schema-per-tenant")

    # Test 4: SHOULD ACCEPT - tenantCount = 1 and multi_tenancy=false
    spec = {
        'project': {'name': 'Test', 'domain': 'test'},
        'functional': {'summary': 'Test'},
        'constraints': {
            'platform': 'api',
            'cloud': 'aws',
            'language': 'python',
            'tenantCount': 1,
            'features': {'multi_tenancy': False}
        }
    }
    success, output = run_compiler_on_spec(spec)
    assert success, f"Should accept tenantCount=1 with multi_tenancy=false. Error: {output}"
    print("  ✓ Correctly accepts: tenantCount=1 + multi_tenancy=false")


def test_compliance_vs_audit_logging():
    """Test HIPAA/SOX compliance requires audit logging."""

    print("Testing compliance vs audit_logging validation...")

    # Test 1: SHOULD REJECT - HIPAA=true but audit_logging=false
    spec = {
        'project': {'name': 'Test', 'domain': 'test'},
        'functional': {'summary': 'Test'},
        'constraints': {
            'platform': 'api',
            'cloud': 'aws',
            'language': 'python'
        },
        'nfr': {
            'data': {'compliance': {'hipaa': True}},
            'security': {'audit_logging': False}
        }
    }
    success, output = run_compiler_on_spec(spec)
    assert not success, "Should reject HIPAA without audit logging"
    assert "Constraints/NFRs trade-off requirements not met" in output, f"Expected 'Constraints/NFRs trade-off requirements not met' in output: {output}"
    assert "compliance-hipaa" in output, f"Expected 'compliance-hipaa' pattern ID in output: {output}"
    assert "audit" in output.lower()
    print("  ✓ Correctly rejects: HIPAA=true + audit_logging=false")

    # Test 2: SHOULD REJECT - SOX=true but audit_logging=false
    spec = {
        'project': {'name': 'Test', 'domain': 'test'},
        'functional': {'summary': 'Test'},
        'constraints': {
            'platform': 'api',
            'cloud': 'aws',
            'language': 'python'
        },
        'nfr': {
            'data': {'compliance': {'sox': True}},
            'security': {'audit_logging': False}
        }
    }
    success, output = run_compiler_on_spec(spec)
    assert not success, "Should reject SOX without audit logging"
    assert "Constraints/NFRs trade-off requirements not met" in output, f"Expected 'Constraints/NFRs trade-off requirements not met' in output: {output}"
    assert "compliance-sox" in output, f"Expected 'compliance-sox' pattern ID in output: {output}"
    print("  ✓ Correctly rejects: SOX=true + audit_logging=false")

    # Test 3: SHOULD ACCEPT - HIPAA=true and audit_logging=true
    spec = {
        'project': {'name': 'Test', 'domain': 'test'},
        'functional': {'summary': 'Test'},
        'constraints': {
            'platform': 'api',
            'cloud': 'aws',
            'language': 'python'
        },
        'nfr': {
            'data': {'compliance': {'hipaa': True}},
            'security': {'audit_logging': True}
        }
    }
    success, output = run_compiler_on_spec(spec)
    assert success, f"Should accept HIPAA with audit logging. Error: {output}"
    print("  ✓ Correctly accepts: HIPAA=true + audit_logging=true")

    # Test 4: SHOULD REJECT - GDPR=true but audit_logging=false
    # compliance-gdpr-basic requires audit_logging == true (GDPR Article 30 mandates records of processing)
    spec = {
        'project': {'name': 'Test', 'domain': 'test'},
        'functional': {'summary': 'Test'},
        'constraints': {
            'platform': 'api',
            'cloud': 'aws',
            'language': 'python'
        },
        'nfr': {
            'data': {'compliance': {'gdpr': True}, 'pii': True},
            'security': {'audit_logging': False}
        }
    }
    success, output = run_compiler_on_spec(spec)
    assert not success, f"Should reject GDPR without audit logging (GDPR Article 30 requires audit). output: {output}"
    assert "compliance-gdpr-basic" in output, f"Expected 'compliance-gdpr-basic' pattern ID in output: {output}"
    print("  ✓ Correctly rejects: GDPR=true + audit_logging=false (GDPR Article 30 requires audit logging)")


def test_messaging_delivery_guarantee_vs_async():
    """Test messaging_delivery_guarantee patterns enforce async_messaging via requires_constraints.

    The compiler no longer has a heuristic for this combination. Validation is
    now pattern-driven: each delivery-guarantee consumer pattern has
    requires_constraints: async_messaging == true.

    When messaging_delivery_guarantee is set but async_messaging=false, none of
    the three consumer patterns activate (both gates must pass for selection),
    so compilation succeeds with no consumer behavior pattern selected.
    """

    print("Testing messaging_delivery_guarantee vs async_messaging validation...")

    # Test 1: delivery guarantee set but async_messaging=false → SHOULD REJECT.
    # exactly-once-transactional-consumer activates (delivery_guarantee gate passes),
    # then requires_constraints: async_messaging == true fires and fails.
    # Pattern-driven validation replaces the old compiler heuristic.
    spec = {
        'project': {'name': 'Test', 'domain': 'test'},
        'functional': {'summary': 'Test'},
        'constraints': {
            'platform': 'api',
            'cloud': 'aws',
            'language': 'python',
            'features': {
                'messaging_delivery_guarantee': 'exactly-once',
                'async_messaging': False
            }
        }
    }
    success, output = run_compiler_on_spec(spec)
    assert not success, "Should reject: delivery_guarantee set but async_messaging=false"
    assert "async_messaging" in output
    print("  ✓ Correctly rejects via requires_constraints: delivery_guarantee set + async_messaging=false")

    # Test 2: SHOULD ACCEPT - delivery guarantee and async_messaging=true
    # Also provide the other fields requires_nfr/requires_constraints demand:
    # distributed_transactions (requires_constraints), needsReadYourWrites and
    # durability.strict (requires_nfr) for exactly-once-transactional-consumer.
    spec = {
        'project': {'name': 'Test', 'domain': 'test'},
        'functional': {'summary': 'Test'},
        'constraints': {
            'platform': 'api',
            'cloud': 'aws',
            'language': 'python',
            'features': {
                'messaging_delivery_guarantee': 'exactly-once',
                'async_messaging': True,
                'distributed_transactions': True
            }
        },
        'nfr': {
            'consistency': {'needsReadYourWrites': True},
            'durability': {'strict': True}
        }
    }
    success, output = run_compiler_on_spec(spec)
    assert success, f"Should accept delivery guarantee with async messaging. Error: {output}"
    print("  ✓ Correctly accepts: delivery_guarantee set + async_messaging=true")

    # Test 3: SHOULD REJECT - async_messaging=true but no delivery_guarantee specified
    # async-messaging-delivery-guarantee-required enforces that messaging_delivery_guarantee
    # must be explicitly set when async_messaging=true. null fails the in [...] check.
    spec = {
        'project': {'name': 'Test', 'domain': 'test'},
        'functional': {'summary': 'Test'},
        'constraints': {
            'platform': 'api',
            'cloud': 'aws',
            'language': 'python',
            'features': {'async_messaging': True}
        }
    }
    success, output = run_compiler_on_spec(spec)
    assert not success, "Should reject: async_messaging=true but no delivery_guarantee set"
    assert "messaging_delivery_guarantee" in output
    print("  ✓ Correctly rejects: async_messaging=true without explicit delivery_guarantee")


def test_batch_processing_nfr_enforcement():
    """Test batch-processing-required enforces explicit NFR fields when batch_processing=true.

    batch-processing-required activates when batch_processing=true and requires:
    - peak_jobs_per_hour (must be set, >= 1)
    - jobStartP95Seconds (must be set, >= 0)
    - jobStartP99Seconds (must be set, >= 0)
    - availability <= 0.9999
    - rto_minutes >= 15
    - rpo_minutes >= 5
    """

    print("Testing batch_processing NFR enforcement...")

    # Test 1: SHOULD REJECT - batch_processing=true but no batch NFRs specified
    spec = {
        'project': {'name': 'Test', 'domain': 'test'},
        'functional': {'summary': 'Test'},
        'constraints': {
            'platform': 'batch',
            'cloud': 'aws',
            'language': 'python',
            'features': {'batch_processing': True}
        }
    }
    success, output = run_compiler_on_spec(spec)
    assert not success, "Should reject: batch_processing=true without batch NFRs"
    assert "batch-processing-required" in output
    assert "peak_jobs_per_hour" in output
    print("  ✓ Correctly rejects: batch_processing=true without batch NFRs")

    # Test 2: SHOULD REJECT - peak_jobs_per_hour missing (only job start latency provided)
    spec = {
        'project': {'name': 'Test', 'domain': 'test'},
        'functional': {'summary': 'Test'},
        'constraints': {
            'platform': 'batch',
            'cloud': 'aws',
            'language': 'python',
            'features': {'batch_processing': True}
        },
        'nfr': {
            'latency': {
                'jobStartP95Seconds': 30,
                'jobStartP99Seconds': 60
            }
        }
    }
    success, output = run_compiler_on_spec(spec)
    assert not success, "Should reject: peak_jobs_per_hour not set"
    assert "peak_jobs_per_hour" in output
    print("  ✓ Correctly rejects: missing peak_jobs_per_hour")

    # Test 3: SHOULD REJECT - jobStartP95Seconds and jobStartP99Seconds missing
    spec = {
        'project': {'name': 'Test', 'domain': 'test'},
        'functional': {'summary': 'Test'},
        'constraints': {
            'platform': 'batch',
            'cloud': 'aws',
            'language': 'python',
            'features': {'batch_processing': True}
        },
        'nfr': {
            'throughput': {'peak_jobs_per_hour': 10000}
        }
    }
    success, output = run_compiler_on_spec(spec)
    assert not success, "Should reject: jobStartP95Seconds and jobStartP99Seconds not set"
    assert "jobStart" in output
    print("  ✓ Correctly rejects: missing jobStartP95Seconds and jobStartP99Seconds")

    # Test 4: SHOULD ACCEPT - all required batch NFRs specified
    spec = {
        'project': {'name': 'Test', 'domain': 'test'},
        'functional': {'summary': 'Test'},
        'constraints': {
            'platform': 'batch',
            'cloud': 'aws',
            'language': 'python',
            'features': {'batch_processing': True}
        },
        'nfr': {
            'throughput': {'peak_jobs_per_hour': 10000},
            'latency': {
                'jobStartP95Seconds': 30,
                'jobStartP99Seconds': 60
            }
        }
    }
    success, output = run_compiler_on_spec(spec)
    assert success, f"Should accept: all required batch NFRs specified. Error: {output}"
    print("  ✓ Correctly accepts: all required batch NFRs specified")

    # Test 5: SHOULD ACCEPT - batch_processing=false, no enforcement triggered
    spec = {
        'project': {'name': 'Test', 'domain': 'test'},
        'functional': {'summary': 'Test'},
        'constraints': {
            'platform': 'api',
            'cloud': 'aws',
            'language': 'python',
            'features': {'batch_processing': False}
        }
    }
    success, output = run_compiler_on_spec(spec)
    assert success, f"Should accept: batch_processing=false, no enforcement. Error: {output}"
    assert "batch-processing-required" not in output
    print("  ✓ Correctly accepts: batch_processing=false — enforcement not triggered")


def main():
    print("Running semantic validation tests...\n")

    try:
        test_multi_tenancy_vs_tenant_isolation()
        print()
        test_tenant_count_vs_multi_tenancy()
        print()
        test_compliance_vs_audit_logging()
        print()
        test_messaging_delivery_guarantee_vs_async()
        print("\n✅ All semantic validation tests passed!")
        return 0
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
