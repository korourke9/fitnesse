# Fitnesse Infrastructure

This directory contains the infrastructure as code for deploying Fitnesse to AWS.

## Architecture

```
┌─────────────────┐
│   CloudFront    │ (Frontend CDN)
└────────┬────────┘
         │
    ┌────▼────┐
    │   S3    │ (Static Frontend)
    └─────────┘

┌─────────────────┐
│      ALB        │ (Load Balancer)
└────────┬────────┘
         │
    ┌────▼────┐
    │   ECS   │ (Backend API)
    └─────────┘
         │
    ┌────▼────┐
    │   RDS   │ (PostgreSQL)
    └─────────┘
```

## Quick Start

1. **Set up AWS credentials** (required for each terminal session):
   ```bash
   cd terraform
   source setup-credentials.sh
   ```

2. **Set up Terraform backend**:
   ```bash
   cd ../scripts
   ./setup-terraform-backend.sh
   ```

3. **Configure variables**:
   ```bash
   cd ../terraform
   cp terraform.tfvars.example terraform.tfvars
   # Edit terraform.tfvars with your settings
   ```

4. **Deploy infrastructure**:
   ```bash
   source setup-credentials.sh  # Export credentials
   terraform init
   terraform plan
   terraform apply
   ```

**Note**: You must run `source setup-credentials.sh` before Terraform commands in each new terminal session.

4. **Deploy backend**:
   ```bash
   ./scripts/deploy-backend.sh
   ```

5. **Deploy frontend**:
   ```bash
   ./scripts/deploy-frontend.sh
   ```

See [DEPLOYMENT.md](../DEPLOYMENT.md) for detailed instructions.

## Infrastructure Components

### Networking
- **VPC**: Isolated network environment
- **Public Subnets**: For ALB and ECS tasks
- **Private Subnets**: For RDS database
- **NAT Gateway**: For private subnet internet access
- **Internet Gateway**: For public subnet internet access

### Compute
- **ECS Fargate**: Serverless container hosting
- **Application Load Balancer**: Routes traffic to ECS tasks

### Database
- **RDS PostgreSQL**: Managed database service
- **Multi-AZ**: Available in production (not in dev)

### Storage
- **S3**: Static frontend hosting
- **ECR**: Docker image registry

### CDN
- **CloudFront**: Global content delivery

### Security
- **Secrets Manager**: Database credentials
- **Security Groups**: Network access control
- **IAM Roles**: Service permissions

## Costs

Estimated monthly costs (dev environment):
- RDS db.t3.micro: ~$15/month
- ECS Fargate (0.25 vCPU, 0.5GB): ~$10-20/month
- ALB: ~$16/month
- NAT Gateway: ~$32/month
- CloudFront: ~$1-5/month
- S3: ~$1/month
- Data transfer: Variable

**Total: ~$75-90/month for dev environment**

**Note**: NAT Gateway is the biggest cost. Consider removing it if you don't need private subnet internet access.

## Variables

See `terraform/variables.tf` for all available variables.

Key variables:
- `aws_region`: AWS region (default: us-east-1)
- `environment`: Environment name (dev/staging/prod)
- `database_password`: Database master password (required)
- `allowed_cidr_blocks`: IP ranges allowed to access (default: 0.0.0.0/0)

## Outputs

After `terraform apply`:
- `alb_dns_name`: Backend API URL
- `cloudfront_url`: Frontend URL
- `database_endpoint`: Database connection endpoint
- `ecr_repository_url`: ECR repository for backend images
- `s3_bucket_name`: S3 bucket for frontend

## Maintenance

### Update Backend
```bash
./scripts/deploy-backend.sh
```

### Update Frontend
```bash
./scripts/deploy-frontend.sh
```

### Database Migrations
See [DEPLOYMENT.md](../DEPLOYMENT.md) for migration instructions.

## Troubleshooting

### Terraform Issues
- Ensure AWS credentials are configured
- Check IAM permissions
- Verify region availability

### Deployment Issues
- Check CloudWatch logs
- Verify security groups
- Check ECS service status

## Cleanup

```bash
terraform destroy
```

**Warning**: This deletes all resources including the database!
