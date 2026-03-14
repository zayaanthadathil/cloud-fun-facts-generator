import boto3
import random
import json
import uuid

# DynamoDB connection
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("CloudFacts")

# Bedrock client
bedrock = boto3.client("bedrock-runtime")


def lambda_handler(event, context):
    method = event.get("requestContext", {}).get("http", {}).get("method", "GET")
    raw_path = event.get("rawPath", "")
    print("METHOD:", method)
    print("RAW PATH:", raw_path)
    print("EVENT:", event)

    # Health check endpoint
    if method == "GET" and raw_path == "/health":
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type"
            },
            "body": json.dumps({
                "status": "ok",
                "service": "cloud-fun-facts"
            })
        }

    # Get all facts
    if method == "GET" and raw_path == "/facts":
        response = table.scan()
        items = response.get("Items", [])

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type"
            },
            "body": json.dumps({"facts": items})
        }

    # Add a new fact
    if method == "POST":
        print("POST branch reached")

        body = json.loads(event.get("body", "{}"))
        fact_text = body.get("fact", "").strip()

        if len(fact_text) < 5:
            return {
                "statusCode": 400,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                    "Access-Control-Allow-Headers": "Content-Type"
                },
                "body": json.dumps({"error": "Fact must be at least 5 characters"})
            }

        # Check for duplicate facts
        response = table.scan()
        items = response.get("Items", [])

        for item in items:
            if item.get("FactText", "").strip().lower() == fact_text.lower():
                return {
                    "statusCode": 400,
                    "headers": {
                        "Content-Type": "application/json",
                        "Access-Control-Allow-Origin": "*",
                        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                        "Access-Control-Allow-Headers": "Content-Type"
                    },
                    "body": json.dumps({"error": "Fact already exists"})
                }

        table.put_item(
            Item={
                "FactID": str(uuid.uuid4()),
                "FactText": fact_text
            }
        )

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type"
            },
            "body": json.dumps({"message": "Fact added successfully"})
        }

    # Default GET behavior for random fun fact
    response = table.scan()
    items = response.get("Items", [])

    if not items:
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type"
            },
            "body": json.dumps({"fact": "No facts available in DynamoDB."})
        }

    fact = random.choice(items)["FactText"]

    messages = [
        {
            "role": "user",
            "content": f"Take this cloud computing fact and make it fun and engaging in 1-2 sentences maximum. Keep it short and witty: {fact}"
        }
    ]

    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 100,
        "messages": messages,
        "temperature": 0.7
    }

    try:
        resp = bedrock.invoke_model(
            modelId="anthropic.claude-3-haiku-20240307-v1:0",
            body=json.dumps(body),
            accept="application/json",
            contentType="application/json"
        )

        result = json.loads(resp["body"].read())
        witty_fact = ""

        if "content" in result and result["content"]:
            for block in result["content"]:
                if block.get("type") == "text":
                    witty_fact = block["text"].strip()
                    break

        if not witty_fact or len(witty_fact) > 300:
            witty_fact = fact

    except Exception as e:
        print(f"Bedrock error: {e}")
        witty_fact = fact

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type"
        },
        "body": json.dumps({"fact": witty_fact})
    }