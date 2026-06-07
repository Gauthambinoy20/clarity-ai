variable "region" {
  description = "AWS region to deploy into."
  type        = string
  default     = "eu-west-1"
}

variable "instance_type" {
  description = <<-EOT
    EC2 instance size. The full detector ensemble loads several
    transformer models and needs ~4 GB of RAM (t4g.medium / t3.medium).
    A free-tier micro (1 GB) can only serve fast mode reliably.
  EOT
  type        = string
  default     = "t4g.medium"
}

variable "admin_cidr" {
  description = "CIDR allowed to reach SSH (your IP /32). No default on purpose."
  type        = string
}

variable "ssh_public_key" {
  description = "Public key material for the instance key pair."
  type        = string
}

variable "root_volume_gb" {
  description = "Root EBS volume size. Models + images need headroom."
  type        = number
  default     = 30
}

variable "project" {
  description = "Tag applied to every resource."
  type        = string
  default     = "clarity-ai"
}
