variable "subscription_id" {
  description = "Suscripción de Azure. Si es null se toma de ARM_SUBSCRIPTION_ID."
  type        = string
  default     = null
}

variable "proyecto" {
  description = "Prefijo corto de los recursos (solo minúsculas y números)."
  type        = string
  default     = "saludcerca"
  validation {
    condition     = can(regex("^[a-z0-9]{3,12}$", var.proyecto))
    error_message = "Use de 3 a 12 caracteres en minúsculas o números."
  }
}

variable "entorno" {
  description = "dev o prod."
  type        = string
  default     = "dev"
  validation {
    condition     = contains(["dev", "prod"], var.entorno)
    error_message = "El entorno debe ser dev o prod."
  }
}

variable "location" {
  description = "Región principal. México Central: la más cercana al Perú con Functions Flex Consumption entre las que permite Azure for Students (Chile Central aún no ofrece Flex)."
  type        = string
  default     = "mexicocentral"
}

variable "apim_publisher_email" {
  description = "Correo de contacto de API Management."
  type        = string
}

variable "paises_permitidos" {
  description = "Códigos ISO de los países desde los que el WAF de Front Door admite tráfico."
  type        = list(string)
  default     = ["PE"]
}

variable "fn_max_instancias" {
  description = "Tope de instancias de Azure Functions: limita el gasto si hay un pico anómalo."
  type        = number
  default     = 40
}

variable "fn_memoria_mb" {
  description = "Memoria por instancia en Flex Consumption (512, 2048 o 4096)."
  type        = number
  default     = 2048
}

# ponytail: "dev" solo para probar la demo en Azure sin tenant de Entra; cualquiera con la URL entra con usuarios ficticios.
variable "auth_mode" {
  description = "entra (producción) o dev (demo con usuarios ficticios y datos de ejemplo)."
  type        = string
  default     = "entra"
  validation {
    condition     = contains(["entra", "dev"], var.auth_mode)
    error_message = "auth_mode debe ser entra o dev."
  }
}

# ---------- Microsoft Entra External ID (se crea manualmente; ver README) ----------
variable "entra_tenant_subdomain" {
  description = "Subdominio del tenant externo (<subdominio>.ciamlogin.com)."
  type        = string
}

variable "entra_tenant_id" {
  description = "ID del tenant externo de Entra External ID."
  type        = string
}

variable "entra_api_client_id" {
  description = "Client ID del registro de aplicación de la API (audiencia de los tokens)."
  type        = string
}

# ---------- Communication Services ----------
variable "acs_data_location" {
  description = "Ubicación de datos de Communication Services y Email (deben coincidir)."
  type        = string
  default     = "United States"
}

variable "acs_sms_from" {
  description = "Remitente de SMS habilitado (para Perú, vía Messaging Connect). Vacío = sin SMS."
  type        = string
  default     = ""
}

# ---------- Costos ----------
variable "presupuesto_mensual_usd" {
  description = "Presupuesto mensual del grupo de recursos."
  type        = number
  default     = 50
}

variable "presupuesto_inicio" {
  description = "Primer día del periodo del presupuesto (RFC 3339)."
  type        = string
  default     = "2026-11-01T00:00:00Z"
}

variable "correos_alerta" {
  description = "Correos que reciben las alertas de presupuesto."
  type        = list(string)
  default     = []
}

variable "campana" {
  description = "Etiqueta de campaña de salud para atribuir costos (p. ej. 'vacunacion-2026')."
  type        = string
  default     = "base"
}

variable "habilitar_front_door" {
  description = "Crea Azure Front Door Standard con WAF (+ USD 35/mes de tarifa base)."
  type        = bool
  default     = true
}

variable "integration_keys_sha256" {
  description = "Hash SHA-256 (hex) de las claves de integración FHIR de los socios, separados por comas."
  type        = string
  default     = ""
  sensitive   = true
}
