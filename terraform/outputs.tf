output "cloud_run_url" {
  description = "Public URL of the deployed OmniBlog Cloud Run service"
  value       = google_cloud_run_v2_service.omniblog_service.uri
}

output "artifact_registry_repo" {
  description = "Docker repository URI in Artifact Registry"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.repo.name}"
}

output "storage_bucket_name" {
  description = "Cloud Storage bucket name for blog publication artifacts"
  value       = google_storage_bucket.artifacts.name
}

output "service_account_email" {
  description = "Runtime service account email"
  value       = google_service_account.agent_sa.email
}
