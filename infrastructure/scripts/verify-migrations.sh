#!/bin/bash
# Script to verify database migrations were applied correctly

set -e

AWS_REGION=${AWS_REGION:-us-east-2}
CLUSTER_NAME="fitnesse-cluster"
SECRET_NAME="fitnesse-database-url"

echo "🔍 Verifying database migrations..."
echo ""

# Get database URL from Secrets Manager
echo "📦 Retrieving database URL from Secrets Manager..."
DATABASE_URL=$(aws secretsmanager get-secret-value \
    --secret-id ${SECRET_NAME} \
    --region ${AWS_REGION} \
    --query SecretString \
    --output text)

if [ -z "$DATABASE_URL" ]; then
    echo "❌ Failed to retrieve database URL"
    exit 1
fi

# Get subnet and security group from the ECS service
echo "📦 Getting network configuration from ECS service..."
SERVICE_INFO=$(aws ecs describe-services \
    --cluster ${CLUSTER_NAME} \
    --services fitnesse-backend-service \
    --region ${AWS_REGION} \
    --query 'services[0].{Subnets:networkConfiguration.awsvpcConfiguration.subnets[0],SecurityGroups:networkConfiguration.awsvpcConfiguration.securityGroups[0]}' \
    --output json)

SUBNET_ID=$(echo $SERVICE_INFO | jq -r '.Subnets')
SECURITY_GROUP_ID=$(echo $SERVICE_INFO | jq -r '.SecurityGroups')

# Get the task definition ARN
TASK_DEF_ARN=$(aws ecs describe-services \
    --cluster ${CLUSTER_NAME} \
    --services fitnesse-backend-service \
    --region ${AWS_REGION} \
    --query 'services[0].taskDefinition' \
    --output text)

# Create verification script
VERIFICATION_SCRIPT=$(cat <<'PYTHON_EOF'
import os
import sys
from sqlalchemy import create_engine, text, inspect

DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    print("❌ DATABASE_URL not set")
    sys.exit(1)

engine = create_engine(DATABASE_URL)
inspector = inspect(engine)

print("📊 Checking database schema...")
print("")

# Check if tables exist
required_tables = ['user_profiles', 'goals', 'alembic_version']
missing_tables = []

for table in required_tables:
    if inspector.has_table(table):
        print(f"✅ Table '{table}' exists")
    else:
        print(f"❌ Table '{table}' is missing")
        missing_tables.append(table)

if missing_tables:
    print(f"\n❌ Missing tables: {', '.join(missing_tables)}")
    sys.exit(1)

print("")
print("📋 Checking table structures...")
print("")

# Check user_profiles columns
if inspector.has_table('user_profiles'):
    profile_columns = [col['name'] for col in inspector.get_columns('user_profiles')]
    required_profile_columns = [
        'id', 'user_id', 'height_cm', 'weight_kg', 'age', 'sex',
        'activity_level', 'dietary_preferences', 'workout_preferences',
        'conditions', 'additional_context'
    ]
    print("User Profiles columns:")
    for col in required_profile_columns:
        if col in profile_columns:
            print(f"  ✅ {col}")
        else:
            print(f"  ❌ {col} (missing)")
    
    # Check activity_level is Float
    activity_col = next((c for c in inspector.get_columns('user_profiles') if c['name'] == 'activity_level'), None)
    if activity_col and str(activity_col['type']) == 'REAL' or 'FLOAT' in str(activity_col['type']):
        print("  ✅ activity_level is Float type")
    else:
        print(f"  ⚠️  activity_level type: {activity_col['type'] if activity_col else 'not found'}")

print("")
# Check goals columns
if inspector.has_table('goals'):
    goal_columns = [col['name'] for col in inspector.get_columns('goals')]
    required_goal_columns = [
        'id', 'user_id', 'goal_type', 'description', 'target', 'target_value',
        'target_date', 'success_metrics', 'is_active'
    ]
    print("Goals columns:")
    for col in required_goal_columns:
        if col in goal_columns:
            print(f"  ✅ {col}")
        else:
            print(f"  ❌ {col} (missing)")
    
    # Check target is required (not nullable)
    target_col = next((c for c in inspector.get_columns('goals') if c['name'] == 'target'), None)
    if target_col and not target_col['nullable']:
        print("  ✅ target is required (not nullable)")
    else:
        print(f"  ⚠️  target nullable: {target_col['nullable'] if target_col else 'not found'}")

print("")
print("📌 Checking Alembic version...")
with engine.connect() as conn:
    result = conn.execute(text("SELECT version_num FROM alembic_version"))
    version = result.fetchone()
    if version:
        print(f"✅ Current Alembic version: {version[0]}")
        if version[0] == 'c694110f0ea9':
            print("✅ Latest migration (user_profiles_and_goals) is applied!")
        else:
            print(f"⚠️  Expected version 'c694110f0ea9', got '{version[0]}'")
    else:
        print("❌ No Alembic version found")

print("")
print("✅ Migration verification complete!")
PYTHON_EOF
)

# Run verification task
echo "🚀 Starting verification task..."
TASK_ARN=$(aws ecs run-task \
    --cluster ${CLUSTER_NAME} \
    --task-definition ${TASK_DEF_ARN} \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[${SUBNET_ID}],securityGroups=[${SECURITY_GROUP_ID}],assignPublicIp=ENABLED}" \
    --overrides "{
        \"containerOverrides\": [{
            \"name\": \"backend\",
            \"command\": [\"python\", \"-c\", $(echo "$VERIFICATION_SCRIPT" | python3 -c "import sys, json; print(json.dumps(sys.stdin.read()))")],
            \"environment\": [{\"name\": \"DATABASE_URL\", \"value\": \"${DATABASE_URL}\"}]
        }]
    }" \
    --region ${AWS_REGION} \
    --query 'tasks[0].taskArn' \
    --output text)

if [ -z "$TASK_ARN" ] || [ "$TASK_ARN" == "None" ]; then
    echo "❌ Failed to start verification task"
    exit 1
fi

echo "✅ Verification task started: ${TASK_ARN}"
# Extract task ID from ARN (format: arn:aws:ecs:region:account:task/cluster/task-id)
TASK_ID=$(echo ${TASK_ARN} | cut -d'/' -f3)
echo "⏳ Waiting for task to complete (Task ID: ${TASK_ID})..."

# Wait for task to complete
aws ecs wait tasks-stopped \
    --cluster ${CLUSTER_NAME} \
    --tasks ${TASK_ARN} \
    --region ${AWS_REGION}

# Get logs - find log stream for this specific task
echo ""
echo "📋 Verification results:"
# Log stream format is typically: ecs/container-name/task-id
# Try multiple possible log stream name formats
LOG_STREAM=$(aws logs describe-log-streams \
    --log-group-name /ecs/fitnesse \
    --log-stream-name-prefix "ecs/backend/${TASK_ID}" \
    --region ${AWS_REGION} \
    --query 'logStreams[0].logStreamName' \
    --output text 2>/dev/null)

# If not found, try without the ecs/ prefix
if [ -z "$LOG_STREAM" ] || [ "$LOG_STREAM" == "None" ]; then
    LOG_STREAM=$(aws logs describe-log-streams \
        --log-group-name /ecs/fitnesse \
        --log-stream-name-prefix "backend/${TASK_ID}" \
        --region ${AWS_REGION} \
        --query 'logStreams[0].logStreamName' \
        --output text 2>/dev/null)
fi

if [ -n "$LOG_STREAM" ] && [ "$LOG_STREAM" != "None" ]; then
    echo "📄 Log stream: ${LOG_STREAM}"
    aws logs get-log-events \
        --log-group-name /ecs/fitnesse \
        --log-stream-name "${LOG_STREAM}" \
        --region ${AWS_REGION} \
        --query 'events[*].message' \
        --output text 2>/dev/null
else
    # Fallback: get most recent logs and filter for verification output
    echo "📄 Showing recent logs (filtering for verification output)..."
    aws logs tail /ecs/fitnesse --since 2m --region ${AWS_REGION} --format short 2>/dev/null | \
        grep -i -E "(Checking|Table|column|Alembic|version|✅|❌)" | tail -50 || \
    aws logs tail /ecs/fitnesse --since 2m --region ${AWS_REGION} --format short 2>/dev/null | tail -50
fi

# Get task exit code
EXIT_CODE=$(aws ecs describe-tasks \
    --cluster ${CLUSTER_NAME} \
    --tasks ${TASK_ARN} \
    --region ${AWS_REGION} \
    --query 'tasks[0].containers[0].exitCode' \
    --output text)

if [ "$EXIT_CODE" == "0" ]; then
    echo ""
    echo "✅ Verification passed!"
else
    echo ""
    echo "❌ Verification failed with exit code: ${EXIT_CODE}"
    exit 1
fi
