#!/bin/bash
set -eux

AWS_REGION=${AWS_REGION:-us-east-2}
BUCKET_NAME="fitnesse-terraform-state"

echo "🔧 Setting up Terraform backend S3 bucket"
echo "Region: ${AWS_REGION}"
echo ""

# Check if bucket exists
if aws s3 ls "s3://${BUCKET_NAME}" 2>&1 | grep 'does not exist'; then
    echo "📦 Creating S3 bucket for Terraform state..."
    aws s3 mb s3://${BUCKET_NAME} --region ${AWS_REGION}
    
    echo "🔒 Enabling versioning..."
    aws s3api put-bucket-versioning \
        --bucket ${BUCKET_NAME} \
        --versioning-configuration Status=Enabled
    
    echo "🔐 Enabling encryption..."
    aws s3api put-bucket-encryption \
        --bucket ${BUCKET_NAME} \
        --server-side-encryption-configuration '{
            "Rules": [{
                "ApplyServerSideEncryptionByDefault": {
                    "SSEAlgorithm": "AES256"
                }
            }]
        }'
    
    echo "🚫 Blocking public access..."
    aws s3api put-public-access-block \
        --bucket ${BUCKET_NAME} \
        --public-access-block-configuration \
        "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
    
    echo "✅ Terraform backend bucket created successfully!"
else
    echo "✅ Terraform backend bucket already exists"
fi

echo ""
echo "📝 Next steps:"
echo "1. Copy terraform.tfvars.example to terraform.tfvars"
echo "2. Edit terraform.tfvars with your configuration"
echo "3. Run 'terraform init' in the terraform directory"
echo "4. Run 'terraform plan' to review changes"
echo "5. Run 'terraform apply' to create infrastructure"


