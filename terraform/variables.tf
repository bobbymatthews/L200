variable "project_id" {
  description = "The Google Cloud Project ID"
  type        = string
  default     = "msk-fde"
}

variable "region" {
  description = "The Google Cloud Region for Cloud Run and Vertex AI"
  type        = string
  default     = "us-central1"
}

variable "service_name" {
  description = "Name of the Cloud Run service"
  type        = string
  default     = "omniblog-agent"
}

variable "container_image" {
  description = "Container image URI for deployment"
  type        = string
  default     = "us-central1-docker.pkg.dev/msk-fde/omniblog/omniblog-agent:latest"
}

variable "model_name" {
  description = "The Gemini model used by the ADK agent"
  type        = string
  default     = "gemini-2.5-flash"
}
