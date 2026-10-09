output "vpc_id" {
  description = "ID of the VPC."
  value       = aws_vpc.this.id
}

output "vpc_cidr_block" {
  description = "CIDR block of the VPC."
  value       = aws_vpc.this.cidr_block
}

output "public_subnet_ids" {
  description = "IDs of the public subnets (one per AZ)."
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "IDs of the private subnets (one per AZ)."
  value       = aws_subnet.private[*].id
}

output "intra_subnet_ids" {
  description = "IDs of the intra (no internet egress) subnets."
  value       = aws_subnet.intra[*].id
}

output "nat_gateway_ids" {
  description = "IDs of NAT gateways (empty when nat_gateway_mode = none)."
  value       = aws_nat_gateway.this[*].id
}

output "nat_public_ips" {
  description = "Public EIPs of the NAT gateways."
  value       = aws_eip.nat[*].public_ip
}

output "public_route_table_id" {
  description = "Route table ID for public subnets."
  value       = aws_route_table.public.id
}

output "private_route_table_ids" {
  description = "Route table IDs for private subnets (one per AZ)."
  value       = aws_route_table.private[*].id
}

output "intra_route_table_id" {
  description = "Route table ID for intra subnets."
  value       = aws_route_table.intra.id
}

output "flow_log_group_name" {
  description = "CloudWatch log group receiving VPC flow logs (null when disabled)."
  value       = var.flow_logs_enabled ? aws_cloudwatch_log_group.flow_logs[0].name : null
}

output "azs" {
  description = "Availability zones in use, index-aligned with subnet outputs."
  value       = var.azs
}
