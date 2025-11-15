resource "aws_api_gateway_resource" "test_ping" {
 path_part  = "test-ping"
 parent_id  = aws_api_gateway_rest_api.BeaconApi.root_resource_id
 rest_api_id = aws_api_gateway_rest_api.BeaconApi.id
}

resource "aws_api_gateway_method" "test_ping_get" {
 rest_api_id  = aws_api_gateway_rest_api.BeaconApi.id
 resource_id  = aws_api_gateway_resource.test_ping.id
 http_method  = "GET"
 authorization = var.beacon-enable-auth ? "COGNITO_USER_POOLS" : "NONE"
 authorizer_id = var.beacon-enable-auth ? aws_api_gateway_authorizer.BeaconUserPool-authorizer.id : null
}

resource "aws_api_gateway_method_response" "test_ping_get" {
 rest_api_id = aws_api_gateway_method.test_ping_get.rest_api_id
 resource_id = aws_api_gateway_method.test_ping_get.resource_id
 http_method = aws_api_gateway_method.test_ping_get.http_method
 status_code = "200"
 response_parameters = {
  "method.response.header.Access-Control-Allow-Origin" = true
 }
 response_models = {
  "application/json" = "Empty"
 }
}

module "cors-test_ping" {
 source = "squidfunk/api-gateway-enable-cors/aws"
 version = "0.3.3"
 
 api_id     = aws_api_gateway_rest_api.BeaconApi.id
 api_resource_id = aws_api_gateway_resource.test_ping.id
}

resource "aws_api_gateway_integration" "test_ping_get" {
 rest_api_id       = aws_api_gateway_rest_api.BeaconApi.id
 resource_id       = aws_api_gateway_resource.test_ping.id
 http_method       = aws_api_gateway_method.test_ping_get.http_method
 integration_http_method = "POST"
 type          = "AWS_PROXY"
 uri           = module.lambda-test_ping.lambda_function_invoke_arn
}

resource "aws_api_gateway_integration_response" "test_ping_get" {
 rest_api_id = aws_api_gateway_method.test_ping_get.rest_api_id
 resource_id = aws_api_gateway_method.test_ping_get.resource_id
 http_method = aws_api_gateway_method.test_ping_get.http_method
 status_code = aws_api_gateway_method_response.test_ping_get.status_code
 response_templates = {
  "application/json" = ""
 }
 depends_on = [aws_api_gateway_integration.test_ping_get]
}

resource "aws_lambda_permission" "api_test_ping" {
 statement_id = "AllowAPITestPingInvoke"
 action    = "lambda:InvokeFunction"
 function_name = module.lambda-test_ping.lambda_function_name
 principal   = "apigateway.amazonaws.com"
 source_arn  = "${aws_api_gateway_rest_api.BeaconApi.execution_arn}/*/*/${aws_api_gateway_resource.test_ping.path_part}"
}