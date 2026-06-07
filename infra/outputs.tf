output "public_ip" {
  description = "Elastic IP of the app instance."
  value       = aws_eip.app.public_ip
}

output "live_domain" {
  description = "sslip.io hostname Caddy serves with a Let's Encrypt cert."
  value       = "${replace(aws_eip.app.public_ip, ".", "-")}.sslip.io"
}

output "live_url" {
  description = "The HTTPS link that goes in the README."
  value       = "https://${replace(aws_eip.app.public_ip, ".", "-")}.sslip.io"
}

output "ssh_command" {
  description = "Convenience SSH line for the admin."
  value       = "ssh ubuntu@${aws_eip.app.public_ip}"
}
