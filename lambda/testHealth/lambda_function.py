import json

def lambda_handler(event, context):
  
  return {
    "statusCode": 200,
    "headers": {"Content-Type": "application/json"},
    "body": json.dumps(
      {
        "message": "this is commit for test 4",
        "path": event.get("path"),
        "environment": event.get("requestContext", {})
          .get("stage")
      }
    ),
  }

