variable "CLOUDINARY_API_KEY" {
  type        = string
  description = "API key for Cloudinary image storage"
  sensitive   = true
}

variable "CLOUDINARY_API_SECRET" {
  type        = string
  description = "API secret for Cloudinary image storage"
  sensitive   = true
}

variable "CLOUDINARY_NAME" {
  type        = string
  description = "Cloudinary storage account name"
  sensitive   = true
}

variable "CLOUDINARY_URL" {
  type        = string
  description = "Cloudinary account base URL"
  sensitive   = true
}

variable "CONTENT_MODERATOR_ENDPOINT" {
  type        = string
  description = "Azure Content Moderator API endpoint"
  sensitive   = true
}

variable "CONTENT_MODERATOR_KEY1" {
  type        = string
  description = "Azure Content Moderator API key"
  sensitive   = true
}

variable "COSMOSDB_CONN_STR" {
  type        = string
  description = "Azure CosmosDB Mongo connection string"
  sensitive   = true
}

variable "CROSS_ORIGIN_DOMAIN" {
  type        = string
  description = "CORS domain filter"
  sensitive   = false
}

variable "TIME_OFFSET_DAYS" {
  type        = string
  description = "Default lifetime of user photos"
  sensitive   = false
}

variable "SCM_DO_BUILD_DURING_DEPLOYMENT" {
  type        = string
  description = "Does the app need to be built before deploying"
  sensitive   = false
}
