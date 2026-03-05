#!/bin/bash
# Validação local do v46 Rollout Dashboard + Approval UX

set -e

echo "=============================================="
echo "=== v46 Rollout Dashboard Validation ==="
echo "=============================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track overall status
OVERALL_STATUS=0

# Function to print section headers
print_header() {
    echo ""
    echo "----------------------------------------------"
    echo "=== $1 ==="
    echo "----------------------------------------------"
}

# Function to print success
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# Function to print error
print_error() {
    echo -e "${RED}✗ $1${NC}"
    OVERALL_STATUS=1
}

# Function to print warning
print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# 1. Backend API Tests
print_header "1. Backend API Tests"
echo "Running: pytest 09-tools/tests/test_vm_webapp_api_rollout_dashboard.py -v"

if PYTHONPATH=09-tools python3 -m pytest 09-tools/tests/test_vm_webapp_api_rollout_dashboard.py -v --tb=short 2>&1; then
    print_success "Backend API tests passed"
else
    print_error "Backend API tests failed"
fi

# 2. E2E Integration Tests
print_header "2. E2E Integration Tests"
echo "Running: pytest 09-tools/tests/test_vm_webapp_rollout_dashboard_e2e.py -v"

if PYTHONPATH=09-tools python3 -m pytest 09-tools/tests/test_vm_webapp_rollout_dashboard_e2e.py -v --tb=short 2>&1; then
    print_success "E2E integration tests passed"
else
    print_error "E2E integration tests failed"
fi

# 3. Frontend Build Check
print_header "3. Frontend Build Check"
echo "Checking vm-ui build..."

if [ -d "09-tools/web/vm-ui" ]; then
    cd 09-tools/web/vm-ui
    
    # Check if node_modules exists
    if [ ! -d "node_modules" ]; then
        print_warning "node_modules not found, skipping frontend build test"
    else
        echo "Running: npm run build"
        if npm run build 2>&1 | tail -20; then
            print_success "Frontend build successful"
        else
            print_error "Frontend build failed"
        fi
    fi
    
    cd "$PROJECT_ROOT"
else
    print_warning "vm-ui directory not found, skipping frontend build"
fi

# 4. Frontend Tests (Rollout Components)
print_header "4. Frontend Tests (Rollout Components)"
echo "Running rollout component tests..."

if [ -d "09-tools/web/vm-ui" ]; then
    cd 09-tools/web/vm-ui
    
    if [ ! -d "node_modules" ]; then
        print_warning "node_modules not found, skipping frontend tests"
    else
        echo "Running: npm run test -- --run src/components/rollout/__tests__/"
        if npm run test -- --run src/components/rollout/__tests__/ 2>&1; then
            print_success "Frontend rollout tests passed"
        else
            print_error "Frontend rollout tests failed"
        fi
    fi
    
    cd "$PROJECT_ROOT"
else
    print_warning "vm-ui directory not found, skipping frontend tests"
fi

# 5. Contract Validation
print_header "5. Contract Validation"
echo "Validating API contract compliance..."

PYTHON_CONTRACT_CHECK='
import sys
sys.path.insert(0, "09-tools")

try:
    from vm_webapp.api_rollout_dashboard import (
        RolloutPolicyResponse,
        ApproveRequest,
        RejectRequest,
        RollbackRequest,
        ActionResponse,
        DashboardResponse,
        HistoryResponse,
    )
    
    # Validate ApproveRequest schema
    req = ApproveRequest(
        operator_id="test",
        reason="Valid reason for testing",
        variant="variant-a"
    )
    assert req.operator_id == "test"
    assert req.reason == "Valid reason for testing"
    
    # Validate RejectRequest schema
    reject = RejectRequest(
        operator_id="test",
        reason="Valid rejection reason"
    )
    assert reject.operator_id == "test"
    
    # Validate RollbackRequest schema  
    rollback = RollbackRequest(
        operator_id="test",
        reason="Valid rollback reason"
    )
    assert rollback.operator_id == "test"
    
    print("✓ All contract validations passed")
    sys.exit(0)
    
except Exception as e:
    print(f"✗ Contract validation failed: {e}")
    sys.exit(1)
'

if python3 -c "$PYTHON_CONTRACT_CHECK" 2>&1; then
    print_success "Contract validation passed"
else
    print_error "Contract validation failed"
fi

# 6. v45 Compatibility Check
print_header "6. v45 Compatibility Check"
echo "Verifying v45 Auto-Rollout Policy compatibility..."

PYTHON_COMPAT_CHECK='
import sys
sys.path.insert(0, "09-tools")

try:
    from vm_webapp.onboarding_rollout_policy import (
        RolloutMode,
        RolloutPolicy,
        BenchmarkMetrics,
        PromotionResult,
        evaluate_promotion,
        evaluate_rollback,
        check_promotion_gates,
        GATE_THRESHOLDS,
    )
    
    # Verify v45 enums still work
    assert RolloutMode.AUTO == "auto"
    assert RolloutMode.MANUAL == "manual"
    assert RolloutMode.SUPERVISED == "supervised"
    
    # Verify v45 gates still exist
    assert "gain_gate" in str(list(GATE_THRESHOLDS.keys()))
    assert "stability_gate" in str(list(GATE_THRESHOLDS.keys()))
    
    # Verify promotion evaluation works
    control = BenchmarkMetrics(
        ttfv=120.0,
        completion_rate=0.75,
        abandonment_rate=0.15,
        score=0.80,
        sample_size=100,
    )
    variant = BenchmarkMetrics(
        ttfv=110.0,
        completion_rate=0.80,
        abandonment_rate=0.12,
        score=0.85,
        sample_size=50,
    )
    
    result = evaluate_promotion(
        "test-exp",
        {"control": control, "variant-a": variant}
    )
    
    assert isinstance(result, PromotionResult)
    assert result.success is True
    assert result.variant_id == "variant-a"
    
    print("✓ v45 compatibility verified")
    sys.exit(0)
    
except Exception as e:
    print(f"✗ v45 compatibility check failed: {e}")
    sys.exit(1)
'

if python3 -c "$PYTHON_COMPAT_CHECK" 2>&1; then
    print_success "v45 compatibility verified"
else
    print_error "v45 compatibility check failed"
fi

# Summary
print_header "Validation Summary"

if [ $OVERALL_STATUS -eq 0 ]; then
    echo -e "${GREEN}=============================================="
    echo -e "=== All validations passed! ==="
    echo -e "==============================================${NC}"
    echo ""
    echo "v46 Rollout Dashboard + Approval UX is ready for deployment."
else
    echo -e "${RED}=============================================="
    echo -e "=== Some validations failed ==="
    echo -e "==============================================${NC}"
    echo ""
    echo "Please review the errors above before proceeding."
fi

exit $OVERALL_STATUS
