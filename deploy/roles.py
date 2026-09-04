"""Create the two IAM roles App Runner needs, idempotently.

- An access role, so App Runner may pull the image from ECR.
- An instance role per service, so the running container may call Amazon Bedrock. Scoped to
  InvokeModel on the specific foundation models and inference profiles each app uses, rather than
  a wildcard, because a demo credential that can call anything is a bad example to ship.
"""

import json
import time

import boto3

iam = boto3.client("iam")
ACCOUNT = boto3.client("sts").get_caller_identity()["Account"]
REGION = "us-east-1"

ACCESS_ROLE = "AppRunnerECRAccessRole"
INSTANCE_ROLE = "AgentsForHumansBedrockRole"

MODELS = [
    "anthropic.claude-sonnet-4-6",
    "anthropic.claude-haiku-4-5-20251001-v1:0",
    "amazon.nova-2-lite-v1:0",
    "amazon.nova-pro-v1:0",
]


def ensure_role(name: str, principal: str, description: str) -> str:
    trust = {
        "Version": "2012-10-17",
        "Statement": [{"Effect": "Allow", "Principal": {"Service": principal},
                       "Action": "sts:AssumeRole"}],
    }
    try:
        r = iam.get_role(RoleName=name)
        print(f"  role exists: {name}")
        return r["Role"]["Arn"]
    except iam.exceptions.NoSuchEntityException:
        r = iam.create_role(RoleName=name, AssumeRolePolicyDocument=json.dumps(trust),
                            Description=description)
        print(f"  created role: {name}")
        return r["Role"]["Arn"]


def put_policy(role: str, name: str, doc: dict) -> None:
    iam.put_role_policy(RoleName=role, PolicyName=name, PolicyDocument=json.dumps(doc))
    print(f"  policy {name} on {role}")


access_arn = ensure_role(ACCESS_ROLE, "build.apprunner.amazonaws.com",
                         "Lets App Runner pull images from ECR")
try:
    iam.attach_role_policy(
        RoleName=ACCESS_ROLE,
        PolicyArn="arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess")
    print("  attached ECR access policy")
except Exception as exc:
    print(f"  ECR access policy: {exc}")

instance_arn = ensure_role(INSTANCE_ROLE, "tasks.apprunner.amazonaws.com",
                           "Lets Turnout and Tally call Amazon Bedrock")

resources = []
for m in MODELS:
    resources.append(f"arn:aws:bedrock:{REGION}::foundation-model/{m}")
    resources.append(f"arn:aws:bedrock:*::foundation-model/{m}")
    resources.append(f"arn:aws:bedrock:{REGION}:{ACCOUNT}:inference-profile/us.{m}")

put_policy(INSTANCE_ROLE, "InvokeBedrockModels", {
    "Version": "2012-10-17",
    "Statement": [{
        "Sid": "InvokeTheModelsTheseAppsUse",
        "Effect": "Allow",
        "Action": ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
        "Resource": sorted(set(resources)),
    }],
})

print(f"\nACCESS_ROLE_ARN={access_arn}")
print(f"INSTANCE_ROLE_ARN={instance_arn}")
time.sleep(8)  # IAM is eventually consistent; App Runner rejects a role it cannot yet see
print("done")
