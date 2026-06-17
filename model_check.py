import boto3

client = boto3.client("bedrock", region_name="eu-central-1")
response = client.list_foundation_models()

for m in sorted(response["modelSummaries"], key=lambda x: x["modelId"]):
    print(m["modelId"])
