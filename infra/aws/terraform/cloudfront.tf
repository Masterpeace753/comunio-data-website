# AP-14.1: expose the API only through CloudFront. CloudFront's viewer-facing
# default hostname provides HTTPS; the custom origin hostname and regional ACM
# certificate are required to keep the CloudFront-to-ALB connection encrypted.

variable "api_origin_domain_name" {
  description = "DNS hostname for the ALB HTTPS origin; must resolve to this ALB and be covered by api_origin_certificate_arn"
  type        = string
  default     = null

  validation {
    condition     = var.api_origin_domain_name == null || can(regex("^([A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?\\.)*[A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?$", var.api_origin_domain_name))
    error_message = "api_origin_domain_name must be a DNS hostname without a scheme or path."
  }
}

variable "api_origin_certificate_arn" {
  description = "ARN of an issued ACM public certificate in aws_region whose SAN covers api_origin_domain_name; required when api_enabled is true"
  type        = string
  default     = null

  validation {
    condition     = var.api_origin_certificate_arn == null || can(regex("^arn:[^:]+:acm:[^:]+:[0-9]{12}:certificate/.+$", var.api_origin_certificate_arn))
    error_message = "api_origin_certificate_arn must be an ACM certificate ARN."
  }
}

locals {
  edge_tags = merge(
    local.common_tags,
    {
      Owner = lookup(var.tags, "Owner", "team-comunio")
    },
  )
}

data "aws_ec2_managed_prefix_list" "cloudfront_origin_facing" {
  count = var.api_enabled ? 1 : 0

  name = "com.amazonaws.global.cloudfront.origin-facing"
}

data "aws_partition" "current" {}

resource "aws_cloudfront_cache_policy" "api_no_cache" {
  count = var.api_enabled ? 1 : 0

  name        = "${local.name_prefix}-api-no-cache"
  comment     = "AP-14.1: zero TTL; Authorization is included only to forward it to the API origin."
  default_ttl = 0
  max_ttl     = 0
  min_ttl     = 0

  parameters_in_cache_key_and_forwarded_to_origin {
    cookies_config {
      cookie_behavior = "none"
    }

    # CloudFront requires Authorization to be included in a cache policy to
    # forward it. Zero TTLs ensure this never creates an authorization cache.
    headers_config {
      header_behavior = "whitelist"

      headers {
        items = ["Authorization"]
      }
    }

    query_strings_config {
      query_string_behavior = "none"
    }

    enable_accept_encoding_brotli = true
    enable_accept_encoding_gzip   = true
  }
}

resource "aws_cloudfront_origin_request_policy" "api" {
  count = var.api_enabled ? 1 : 0

  name    = "${local.name_prefix}-api-origin-request"
  comment = "Forward API session cookies and required request headers without forwarding unrelated viewer headers."

  cookies_config {
    cookie_behavior = "all"
  }

  headers_config {
    header_behavior = "whitelist"

    headers {
      items = ["CloudFront-Viewer-Address", "Content-Type", "Origin"]
    }
  }

  query_strings_config {
    query_string_behavior = "all"
  }
}

resource "aws_lb_listener" "api_https_cloudfront" {
  count = var.api_enabled ? 1 : 0

  load_balancer_arn = aws_lb.api[0].arn
  port              = 443
  protocol          = "HTTPS"
  certificate_arn   = var.api_origin_certificate_arn
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api[0].arn
  }

  lifecycle {
    precondition {
      condition = (
        var.api_origin_certificate_arn != null &&
        startswith(var.api_origin_certificate_arn, "arn:${data.aws_partition.current.partition}:acm:${var.aws_region}:")
      )
      error_message = "AP-14.1 requires api_origin_certificate_arn to be an issued ACM certificate ARN in aws_region. The certificate must cover api_origin_domain_name."
    }
  }
}

resource "aws_cloudfront_distribution" "api" {
  count = var.api_enabled ? 1 : 0

  enabled         = true
  is_ipv6_enabled = true
  comment         = "${local.name_prefix} API HTTPS ingress"
  http_version    = "http2and3"
  price_class     = "PriceClass_100"

  origin {
    domain_name = var.api_origin_domain_name
    origin_id   = "api-alb-https"

    custom_origin_config {
      http_port                = 80
      https_port               = 443
      origin_protocol_policy   = "https-only"
      origin_ssl_protocols     = ["TLSv1.2"]
      origin_read_timeout      = 60
      origin_keepalive_timeout = 5
    }
  }

  default_cache_behavior {
    target_origin_id         = "api-alb-https"
    viewer_protocol_policy   = "redirect-to-https"
    allowed_methods          = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods           = ["GET", "HEAD", "OPTIONS"]
    compress                 = true
    cache_policy_id          = aws_cloudfront_cache_policy.api_no_cache[0].id
    origin_request_policy_id = aws_cloudfront_origin_request_policy.api[0].id
  }

  ordered_cache_behavior {
    path_pattern             = "/auth/*"
    target_origin_id         = "api-alb-https"
    viewer_protocol_policy   = "redirect-to-https"
    allowed_methods          = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods           = ["GET", "HEAD", "OPTIONS"]
    compress                 = true
    cache_policy_id          = aws_cloudfront_cache_policy.api_no_cache[0].id
    origin_request_policy_id = aws_cloudfront_origin_request_policy.api[0].id
  }

  ordered_cache_behavior {
    path_pattern             = "/api/*"
    target_origin_id         = "api-alb-https"
    viewer_protocol_policy   = "redirect-to-https"
    allowed_methods          = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods           = ["GET", "HEAD", "OPTIONS"]
    compress                 = true
    cache_policy_id          = aws_cloudfront_cache_policy.api_no_cache[0].id
    origin_request_policy_id = aws_cloudfront_origin_request_policy.api[0].id
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
    minimum_protocol_version       = "TLSv1.2_2021"
  }

  tags = local.edge_tags

  depends_on = [aws_lb_listener.api_https_cloudfront]

  lifecycle {
    precondition {
      condition = (
        var.api_origin_domain_name != null &&
        can(regex("^[A-Za-z0-9]([A-Za-z0-9.-]*[A-Za-z0-9])?$", var.api_origin_domain_name))
      )
      error_message = "AP-14.1 requires api_origin_domain_name: a DNS hostname covered by the regional ALB certificate and resolving to this ALB."
    }
  }
}

output "api_cloudfront_domain_name" {
  description = "HTTPS CloudFront hostname for the API; use this as the API origin in the Vercel server-side proxy"
  value       = try(aws_cloudfront_distribution.api[0].domain_name, null)
}

output "api_cloudfront_distribution_id" {
  description = "CloudFront distribution ID for the API HTTPS ingress"
  value       = try(aws_cloudfront_distribution.api[0].id, null)
}
