resource "aws_api_gateway_resource" "test_health" {
  path_part   = "test-health"
  parent_id   = aws_api_gateway_rest_api.BeaconApi.root_resource_id
  rest_api_id = aws_api_gateway_rest_api.BeaconApi.id
}

resource "aws_api_gateway_method" "test_health_get" {
  rest_api_id   = aws_api_gateway_rest_api.BeaconApi.id
  resource_id   = aws_api_gateway_resource.test_health.id
  http_method   = "GET"
  authorization = var.beacon-enable-auth ? "COGNITO_USER_POOLS" : "NONE"
  authorizer_id = var.beacon-enable-auth ? aws_api_gateway_authorizer.BeaconUserPool-authorizer.id : null
}

resource "aws_api_gateway_method_response" "test_health_get" {
  rest_api_id = aws_api_gateway_method.test_health_get.rest_api_id
  resource_id = aws_api_gateway_method.test_health_get.resource_id
  http_method = aws_api_gateway_method.test_health_get.http_method
  status_code = "200"
  response_parameters = {
    "method.response.header.Access-Control-Allow-Origin" = true
  }
  response_models = {
    "application/json" = "Empty"
  }
}

module "cors-test_health" {
  source  = "squidfunk/api-gateway-enable-cors/aws"
  version = "0.3.3"

  api_id          = aws_api_gateway_rest_api.BeaconApi.id
  api_resource_id = aws_api_gateway_resource.test_health.id
}

resource "aws_api_gateway_integration" "test_health_get" {
  rest_api_id             = aws_api_gateway_rest_api.BeaconApi.id
  resource_id             = aws_api_gateway_resource.test_health.id
  http_method             = aws_api_gateway_method.test_health_get.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = module.lambda-test_health.lambda_function_invoke_arn
}

resource "aws_api_gateway_integration_response" "test_health_get" {
  rest_api_id = aws_api_gateway_method.test_health_get.rest_api_id
  resource_id = aws_api_gateway_method.test_health_get.resource_id
  http_method = aws_api_gateway_method.test_health_get.http_method
  status_code = aws_api_gateway_method_response.test_health_get.status_code
  response_templates = {
    "application/json" = ""
  }
  depends_on = [aws_api_gateway_integration.test_health_get]
}

resource "aws_lambda_permission" "api_test_health" {
  statement_id  = "AllowAPITestHealthInvoke"
  action        = "lambda:InvokeFunction"
  function_name = module.lambda-test_health.lambda_function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.BeaconApi.execution_arn}/*/*/${aws_api_gateway_resource.test_health.path_part}"
}

