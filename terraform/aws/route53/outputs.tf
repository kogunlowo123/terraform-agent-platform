output "zone_id" {
  description = "Hosted zone ID."
  value       = aws_route53_zone.this.zone_id
}

output "zone_arn" {
  description = "Hosted zone ARN."
  value       = aws_route53_zone.this.arn
}

output "zone_name" {
  description = "Zone name."
  value       = aws_route53_zone.this.name
}

output "name_servers" {
  description = "Delegation name servers (public zones)."
  value       = aws_route53_zone.this.name_servers
}

output "record_fqdns" {
  description = "Map of record key => FQDN."
  value       = { for k, r in aws_route53_record.this : k => r.fqdn }
}
