#!/bin/bash
# Script to set up AWS credentials for Terraform
# This extracts credentials from your AWS login session

echo "🔐 Setting up AWS credentials for Terraform..."

# Function to refresh credentials
refresh_credentials() {
    if command -v aws &> /dev/null; then
        # Check if we can get credentials
        if aws sts get-caller-identity &> /dev/null; then
            # Try to export credentials (works with AWS CLI v2)
            CREDS=$(aws configure export-credentials --format env 2>/dev/null)
            if [ $? -eq 0 ] && [ -n "$CREDS" ]; then
                eval "$CREDS"
                export AWS_ACCESS_KEY_ID
                export AWS_SECRET_ACCESS_KEY
                export AWS_SESSION_TOKEN
                export AWS_CREDENTIAL_EXPIRATION
                return 0
            fi
        fi
    fi
    return 1
}

# Try to get credentials from AWS CLI
if command -v aws &> /dev/null; then
    # Check if we can get credentials
    if aws sts get-caller-identity &> /dev/null; then
        echo "✅ AWS credentials are available"
        
        # Try to export credentials (works with AWS CLI v2)
        if refresh_credentials; then
            echo "📝 Exporting credentials to environment variables..."
            
            # Show expiration time if available
            if [ -n "$AWS_CREDENTIAL_EXPIRATION" ]; then
                EXP_TIME=$(echo "$AWS_CREDENTIAL_EXPIRATION" | sed 's/+00:00/Z/')
                EXP_EPOCH=$(date -j -f "%Y-%m-%dT%H:%M:%SZ" "$EXP_TIME" +%s 2>/dev/null || date -d "$EXP_TIME" +%s 2>/dev/null)
                NOW_EPOCH=$(date +%s)
                if [ -n "$EXP_EPOCH" ] && [ "$EXP_EPOCH" -gt "$NOW_EPOCH" ]; then
                    MIN_LEFT=$(( (EXP_EPOCH - NOW_EPOCH) / 60 ))
                    echo "⏰ Credentials expire in ~${MIN_LEFT} minutes"
                fi
            fi
            
            echo "✅ Credentials exported to environment"
            echo ""
            echo "Credentials are now available in this shell session."
            echo "Run 'terraform init' in the terraform directory."
            return 0
        else
            echo "⚠️  Cannot auto-export credentials"
            echo ""
            echo "Please set these environment variables manually:"
            echo "  export AWS_ACCESS_KEY_ID='your-access-key'"
            echo "  export AWS_SECRET_ACCESS_KEY='your-secret-key'"
            echo "  export AWS_SESSION_TOKEN='your-session-token'  # If using temporary credentials"
        fi
    else
        echo "❌ AWS credentials not found. Please run 'aws login' first."
        exit 1
    fi
else
    echo "❌ AWS CLI not found"
    exit 1
fi

