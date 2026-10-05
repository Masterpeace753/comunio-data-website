# AP-14.1: expose the API only through CloudFront. CloudFront's viewer-facing
# default hostname provides HTTPS. The ALB is internal and reachable only through
# a CloudFront VPC origin, so no custom domain or ACM certificate is needed.

locals {
  edge_tags = merge(
    local.common_tags,
    {
      Owner = lookup(var.tags, "Owner", "team-comunio")
    },
  )
}

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

resource "aws_cloudfront_vpc_origin" "api" {
  count = var.api_enabled ? 1 : 0

  vpc_origin_endpoint_config {
    name                   = "${local.name_prefix}-api-alb"
    arn                    = aws_lb.api[0].arn
    http_port              = 80
    https_port             = 443
    origin_protocol_policy = "http-only"

    origin_ssl_protocols {
      items    = ["TLSv1.2"]
      quantity = 1
    }
  }

  tags = local.edge_tags
}

data "aws_security_group" "cloudfront_vpc_origins" {
  count = var.api_enabled ? 1 : 0

  vpc_id = local.vpc_id

  filter {
    name   = "group-name"
    values = ["CloudFront-VPCOrigins-Service-SG"]
  }

  depends_on = [aws_cloudfront_vpc_origin.api]
}

resource "aws_vpc_security_group_ingress_rule" "api_alb_from_cloudfront" {
  count = var.api_enabled ? 1 : 0

  security_group_id            = aws_security_group.api_alb[0].id
  referenced_security_group_id = data.aws_security_group.cloudfront_vpc_origins[0].id
  ip_protocol                  = "tcp"
  from_port                    = 80
  to_port                      = 80
  description                  = "CloudFront VPC origin to internal API ALB"
}

resource "aws_cloudfront_distribution" "api" {
  count = var.api_enabled ? 1 : 0

  enabled         = true
  is_ipv6_enabled = true
  comment         = "${local.name_prefix} API HTTPS ingress"
  http_version    = "http2and3"
  price_class     = "PriceClass_100"

  origin {
    domain_name = aws_lb.api[0].dns_name
    origin_id   = "api-alb"

    vpc_origin_config {
      vpc_origin_id            = aws_cloudfront_vpc_origin.api[0].id
      origin_read_timeout      = 60
      origin_keepalive_timeout = 5
    }
  }

  default_cache_behavior {
    target_origin_id         = "api-alb"
    viewer_protocol_policy   = "redirect-to-https"
    allowed_methods          = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods           = ["GET", "HEAD", "OPTIONS"]
    compress                 = true
    cache_policy_id          = aws_cloudfront_cache_policy.api_no_cache[0].id
    origin_request_policy_id = aws_cloudfront_origin_request_policy.api[0].id
  }

  ordered_cache_behavior {
    path_pattern             = "/auth/*"
    target_origin_id         = "api-alb"
    viewer_protocol_policy   = "redirect-to-https"
    allowed_methods          = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods           = ["GET", "HEAD", "OPTIONS"]
    compress                 = true
    cache_policy_id          = aws_cloudfront_cache_policy.api_no_cache[0].id
    origin_request_policy_id = aws_cloudfront_origin_request_policy.api[0].id
  }

  ordered_cache_behavior {
    path_pattern             = "/api/*"
    target_origin_id         = "api-alb"
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

  depends_on = [aws_vpc_security_group_ingress_rule.api_alb_from_cloudfront]
}

output "api_cloudfront_domain_name" {
  description = "HTTPS CloudFront hostname for the API; use this as the API origin in the Vercel server-side proxy"
  value       = try(aws_cloudfront_distribution.api[0].domain_name, null)
}

output "api_cloudfront_distribution_id" {
  description = "CloudFront distribution ID for the API HTTPS ingress"
  value       = try(aws_cloudfront_distribution.api[0].id, null)
}
