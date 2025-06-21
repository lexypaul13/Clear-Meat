#!/bin/bash

# Clear-Meat API Deployment Verification Script
# This script runs comprehensive tests to verify all endpoints work before deployment

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Default values
API_URL="${API_URL:-http://localhost:8000}"
VERBOSE=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --url)
            API_URL="$2"
            shift 2
            ;;
        --verbose|-v)
            VERBOSE="--verbose"
            shift
            ;;
        --help|-h)
            echo "Clear-Meat API Deployment Verification"
            echo ""
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --url URL       API base URL (default: http://localhost:8000)"
            echo "  --verbose, -v   Enable verbose output"
            echo "  --help, -h      Show this help message"
            echo ""
            echo "Environment Variables:"
            echo "  API_URL         Set the API URL (same as --url)"
            echo ""
            echo "Examples:"
            echo "  $0                                    # Test local development server"
            echo "  $0 --url http://localhost:8000       # Test specific URL"
            echo "  $0 --url https://api.yourdomain.com  # Test production server"
            echo "  API_URL=http://localhost:8000 $0     # Using environment variable"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

print_info "Clear-Meat API Deployment Verification"
echo "======================================"
echo ""

print_info "Testing API at: $API_URL"
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is required but not installed"
    exit 1
fi

# Check if requests library is available
if ! python3 -c "import requests" 2>/dev/null; then
    print_error "Python 'requests' library is required"
    print_info "Install with: pip install requests"
    exit 1
fi

# Check if the API is responding
print_info "Checking if API is reachable..."
if curl -s --connect-timeout 5 "$API_URL/health" > /dev/null 2>&1; then
    print_success "API is reachable"
else
    print_error "API is not reachable at $API_URL"
    print_info "Make sure the Clear-Meat API is running:"
    print_info "  • For local development: uvicorn app.main:app --reload"
    print_info "  • For Docker: docker-compose up"
    exit 1
fi

echo ""
print_info "Starting comprehensive endpoint tests..."
echo ""

# Run the comprehensive test suite
if python3 tests/deployment_verification_test.py --url "$API_URL" $VERBOSE; then
    echo ""
    print_success "🎉 ALL TESTS PASSED!"
    print_success "🚀 Clear-Meat API is ready for deployment!"
    echo ""
    print_info "Next steps:"
    echo "  1. Review any warnings in the test output"
    echo "  2. Test with production environment variables"
    echo "  3. Deploy with confidence!"
    echo ""
    exit 0
else
    echo ""
    print_error "⚠️  SOME TESTS FAILED"
    print_warning "Please review the test results and fix issues before deployment"
    echo ""
    print_info "Common issues to check:"
    echo "  • Database connection and migrations"
    echo "  • Environment variables configuration"
    echo "  • External API keys (Gemini, etc.)"
    echo "  • Network connectivity for citations"
    echo ""
    exit 1
fi