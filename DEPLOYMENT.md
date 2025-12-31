# Deployment Guide

This guide will help you deploy Fitnesse to AWS.

## Prerequisites

1. **AWS Account**: Account ID
2. **AWS CLI**: Installed and configured with credentials
3. **Terraform**: Version >= 1.0 installed
4. **Docker**: Installed and running
5. **Node.js**: Version 24+ installed

## Quick Start

### 1. Set Up AWS Credentials

Since you're using AWS login, you need to export credentials for Terraform:

```bash
cd infrastructure/terraform
source setup-credentials.sh
```

This exports your AWS credentials as environment variables that Terraform can use.

**Note**: You'll need to run `source setup-credentials.sh` in each new terminal session before running Terraform commands.

### 2. Set Up Terraform Backend

```bash
cd infrastructure/scripts
./setup-terraform-backend.sh
```

### 3. Configure Terraform Variables

```bash
cd infrastructure/terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` and set:
- `database_password` - A strong password (at least 16 characters)
- `aws_region` - Your preferred region (default: us-east-1)
- Other variables as needed

### 4. Initialize and Apply Infrastructure

```bash
cd infrastructure/terraform
source setup-credentials.sh  # Export AWS credentials
terraform init
terraform plan
terraform apply
```

**Important**: Always run `source setup-credentials.sh` before Terraform commands in a new terminal session.

This will create:
- VPC with public/private subnets
- RDS PostgreSQL database
- ECS Fargate cluster
- Application Load Balancer
- ECR repository
- S3 bucket for frontend
- CloudFront distribution

**Note**: This will take 10-15 minutes to complete.

### 4. Deploy Backend

```bash
cd infrastructure/scripts
./deploy-backend.sh
```

This will:
- Build the Docker image
- Push to ECR
- Update the ECS service

### 5. Deploy Frontend

```bash
cd infrastructure/scripts
./deploy-frontend.sh
```

This will:
- Build the React app
- Upload to S3
- Invalidate CloudFront cache

### 6. Update Frontend Environment

After deployment, update the frontend to point to the backend API:

1. Get the ALB DNS name from Terraform outputs:
```bash
cd infrastructure/terraform
terraform output alb_dns_name
```

2. Update `frontend/.env`:
```
VITE_API_BASE_URL=http://<alb-dns-name>
```

3. Rebuild and redeploy frontend:
```bash
cd infrastructure/scripts
./deploy-frontend.sh
```

## Accessing Your Application

After deployment:

- **Frontend**: CloudFront URL (from `terraform output cloudfront_url`)
- **Backend API**: ALB DNS name (from `terraform output alb_dns_name`)
- **API Docs**: `http://<alb-dns-name>/docs`

## Database Migrations

Run migrations on the deployed backend:

```bash
# Get ECS task ID
TASK_ID=$(aws ecs list-tasks --cluster fitnesse-cluster --service-name fitnesse-backend-service --query 'taskArns[0]' --output text | cut -d/ -f3)

# Execute migration
aws ecs execute-command \
  --cluster fitnesse-cluster \
  --task $TASK_ID \
  --container backend \
  --command "alembic upgrade head" \
  --interactive
```

Or SSH into the ECS task and run migrations manually.

## Monitoring

- **CloudWatch Logs**: `/ecs/fitnesse`
- **ECS Console**: View service status and tasks
- **RDS Console**: Monitor database performance

## Troubleshooting

### Backend not responding
1. Check ECS service status
2. Check CloudWatch logs
3. Verify security groups allow traffic
4. Check database connectivity

### Frontend not loading
1. Check S3 bucket contents
2. Verify CloudFront distribution status
3. Check cache invalidation status

### Database connection issues
1. Verify security groups
2. Check RDS instance status
3. Verify database credentials in Secrets Manager

## Cost Optimization

- Use `db.t3.micro` for dev (free tier eligible)
- Stop ECS services when not in use
- Use CloudFront caching to reduce S3 requests
- Monitor CloudWatch metrics

## Cleanup

To destroy all resources:

```bash
cd infrastructure/terraform
terraform destroy
```

**Warning**: This will delete everything including the database!

## Next Steps

- Set up CI/CD pipeline (GitHub Actions, AWS CodePipeline)
- Add SSL/TLS certificates (ACM)
- Set up CloudWatch alarms
- Configure auto-scaling
- Add WAF rules
- Set up backup automation

