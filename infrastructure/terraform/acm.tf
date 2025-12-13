# ACM Certificate for ALB HTTPS
# Note: For production, you should use a custom domain name
# This certificate can be validated via DNS or email
resource "aws_acm_certificate" "alb" {
  count = var.domain_name != "" ? 1 : 0

  domain_name       = var.domain_name
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }

  tags = merge(local.common_tags, {
    Name = "${var.project_name}-alb-certificate"
  })
}

# Certificate validation
resource "aws_acm_certificate_validation" "alb" {
  count = var.domain_name != "" ? 1 : 0

  certificate_arn = aws_acm_certificate.alb[0].arn

  timeouts {
    create = "5m"
  }
}

