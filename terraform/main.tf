terraform {
  required_version = ">= 1.5.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.30"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# 1. Enable Required GCP APIs
resource "google_project_service" "enabled_apis" {
  for_each = toset([
    "aiplatform.googleapis.com",     # Vertex AI & Agent Engine
    "run.googleapis.com",            # Cloud Run
    "artifactregistry.googleapis.com", # Artifact Registry
    "cloudtrace.googleapis.com",     # Cloud Trace
    "logging.googleapis.com",        # Cloud Logging
    "storage.googleapis.com",        # Cloud Storage
  ])

  service            = each.key
  disable_on_destroy = false
}

# 2. Artifact Registry for Container Images
resource "google_artifact_registry_repository" "repo" {
  depends_on    = [google_project_service.enabled_apis]
  location      = var.region
  repository_id = "omniblog"
  description   = "Docker repository for OmniBlog ADK Agent containers"
  format        = "DOCKER"
}

# 3. Google Cloud Storage Bucket for Article Artifacts
resource "google_storage_bucket" "artifacts" {
  depends_on                  = [google_project_service.enabled_apis]
  name                        = "${var.project_id}-omniblog-artifacts"
  location                    = var.region
  uniform_bucket_level_access = true
  versioning {
    enabled = true
  }
}

# 4. Service Account for Cloud Run / Agent Engine Runtime
resource "google_service_account" "agent_sa" {
  account_id   = "omniblog-runner"
  display_name = "OmniBlog ADK Agent Runtime Service Account"
}

# 5. IAM Bindings (Least Privilege)
resource "google_project_iam_member" "vertex_ai_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.agent_sa.email}"
}

resource "google_project_iam_member" "cloud_trace_agent" {
  project = var.project_id
  role    = "roles/cloudtrace.agent"
  member  = "serviceAccount:${google_service_account.agent_sa.email}"
}

resource "google_project_iam_member" "log_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.agent_sa.email}"
}

resource "google_storage_bucket_iam_member" "artifact_storage_admin" {
  bucket = google_storage_bucket.artifacts.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.agent_sa.email}"
}

# 6. Google Cloud Run Service Deployment
resource "google_cloud_run_v2_service" "omniblog_service" {
  depends_on = [
    google_project_service.enabled_apis,
    google_project_iam_member.vertex_ai_user,
  ]

  name     = var.service_name
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    service_account = google_service_account.agent_sa.email

    scaling {
      min_instance_count = 0
      max_instance_count = 5
    }

    containers {
      image = var.container_image

      resources {
        limits = {
          cpu    = "1000m"
          memory = "2Gi"
        }
      }

      ports {
        container_port = 8000
      }

      env {
        name  = "GOOGLE_GENAI_USE_ENTERPRISE"
        value = "1"
      }
      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.project_id
      }
      env {
        name  = "GOOGLE_CLOUD_LOCATION"
        value = var.region
      }
      env {
        name  = "MODEL_NAME"
        value = var.model_name
      }
      env {
        name  = "ENABLE_CLOUD_TRACE"
        value = "true"
      }
      env {
        name  = "ARTIFACT_SERVICE_URI"
        value = "gs://${google_storage_bucket.artifacts.name}"
      }
      env {
        name  = "SESSION_SERVICE_URI"
        value = "sqlite:///.adk/sessions.db"
      }

      startup_probe {
        http_get {
          path = "/healthz"
          port = 8000
        }
        initial_delay_seconds = 5
        timeout_seconds       = 3
        period_seconds        = 10
        failure_threshold     = 3
      }

      liveness_probe {
        http_get {
          path = "/healthz"
          port = 8000
        }
        period_seconds = 30
      }
    }
  }
}

# 7. Unauthenticated Public Ingress for REST API (or configure authenticated)
resource "google_cloud_run_service_iam_member" "public_access" {
  location = google_cloud_run_v2_service.omniblog_service.location
  service  = google_cloud_run_v2_service.omniblog_service.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
