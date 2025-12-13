#!/bin/bash
# Wrapper script that refreshes credentials and monitors expiration during terraform operations
# Usage: ./terraform-with-refresh.sh <terraform-command> [args...]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Function to refresh credentials silently
refresh_creds() {
    if command -v aws &> /dev/null && aws sts get-caller-identity &> /dev/null; then
        CREDS=$(aws configure export-credentials --format env 2>/dev/null)
        if [ $? -eq 0 ] && [ -n "$CREDS" ]; then
            eval "$CREDS" 2>/dev/null
            export AWS_ACCESS_KEY_ID
            export AWS_SECRET_ACCESS_KEY
            export AWS_SESSION_TOKEN
            export AWS_CREDENTIAL_EXPIRATION
            return 0
        fi
    fi
    return 1
}

# Initial credential setup
echo "🔐 Refreshing AWS credentials..."
if ! refresh_creds; then
    echo "❌ Failed to get AWS credentials. Please run 'aws login' first."
    exit 1
fi

# For long-running operations (apply, destroy), set up a background refresh
if [[ "$1" == "apply" ]] || [[ "$1" == "destroy" ]]; then
    echo "⏰ Setting up credential refresh for long-running operation..."
    
    # Background process to refresh credentials every 30 minutes
    (
        while true; do
            sleep 1800  # 30 minutes
            if refresh_creds; then
                echo "🔄 Credentials refreshed (background)"
            fi
        done
    ) &
    REFRESH_PID=$!
    
    # Cleanup on exit
    trap "kill $REFRESH_PID 2>/dev/null || true" EXIT
fi

# Run terraform
terraform "$@"

