output "api_url" {
  value       = module.serverless_beacon.api_url
  description = "URL used to invoke the API."
}

output "cognito_client_id" {
  value       = module.serverless_beacon.cognito_client_id
  description = "Cognito client Id for user registration and login."
}

output "admin_login_command" {
  value       = module.serverless_beacon.admin_login_command
  description = "Command to sign in an admin"
}

output "guest_login_command" {
  value       = module.serverless_beacon.guest_login_command
  description = "Command to sign in a guest"
}

