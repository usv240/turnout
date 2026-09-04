"""Create or update the turnout App Runner service, idempotently.

One long running container, so the demo's in-memory state is shared by everyone who opens the link.
That is the reason this is App Runner and not Lambda: with Lambda, two judges pressing the same step
would land on different instances holding different days.

The service is pinned to the image digest that is in ECR right now, not to the :latest tag. Pushing
a new image to the same tag does not change the service's image identifier, so App Runner treats the
update as a no-op and silently keeps serving the old build. Pinning the digest makes the deploy
real, and start_deployment forces the rollout either way.

    python -m deploy.apprunner        (from the repository root, with AWS credentials)
"""


import sys
import time

import boto3

REGION = "us-east-1"
ACCOUNT = "957325809861"
ACCESS_ROLE = f"arn:aws:iam::{ACCOUNT}:role/AppRunnerECRAccessRole"
INSTANCE_ROLE = f"arn:aws:iam::{ACCOUNT}:role/AgentsForHumansBedrockRole"
REGISTRY = f"{ACCOUNT}.dkr.ecr.{REGION}.amazonaws.com"

ar = boto3.client("apprunner", region_name=REGION)

SERVICES = {
    "turnout": {
        "env": {"AWS_REGION": REGION, "TURNOUT_USE_A2A": "1", "TURNOUT_USE_AGENTCORE": "1",
                "TURNOUT_REASONING_MODEL": "us.anthropic.claude-sonnet-4-6",
                "TURNOUT_FAST_MODEL": "us.anthropic.claude-haiku-4-5-20251001-v1:0"},
        "cpu": "1 vCPU", "memory": "2 GB",
    },
}


def image_digest(repo: str, tag: str = "latest") -> str:
    """Pin to the digest that is actually in ECR right now."""
    ecr = boto3.client("ecr", region_name=REGION)
    r = ecr.describe_images(repositoryName=repo, imageIds=[{"imageTag": tag}])
    return r["imageDetails"][0]["imageDigest"]


def existing(name: str):
    token = None
    while True:
        kw = {"NextToken": token} if token else {}
        page = ar.list_services(**kw)
        for s in page["ServiceSummaryList"]:
            if s["ServiceName"] == name:
                return s
        token = page.get("NextToken")
        if not token:
            return None


def source_config(image: str, spec: dict) -> dict:
    return {
        "ImageRepository": {
            "ImageIdentifier": image,
            "ImageRepositoryType": "ECR",
            "ImageConfiguration": {"Port": "8080", "RuntimeEnvironmentVariables": spec["env"]},
        },
        "AutoDeploymentsEnabled": False,
        "AuthenticationConfiguration": {"AccessRoleArn": ACCESS_ROLE},
    }


def wait_ready(arn: str, name: str, minutes: int = 20) -> str:
    deadline = time.time() + minutes * 60
    last = ""
    while time.time() < deadline:
        s = ar.describe_service(ServiceArn=arn)["Service"]
        status = s["Status"]
        if status != last:
            print(f"  {name}: {status}")
            last = status
        if status == "RUNNING":
            return s["ServiceUrl"]
        if status in ("CREATE_FAILED", "DELETE_FAILED"):
            return ""
        time.sleep(20)
    print(f"  {name}: still {last} after {minutes} minutes")
    return ""


def deploy(name: str, spec: dict) -> tuple[str, str]:
    digest = image_digest(name)
    image = f"{REGISTRY}/{name}@{digest}"
    print(f"  {name}: {digest[:19]}")

    found = existing(name)
    if found and found["Status"] not in ("DELETED", "DELETE_FAILED"):
        arn = found["ServiceArn"]
        wait_ready(arn, name)  # cannot update a service mid-operation
        ar.update_service(ServiceArn=arn, SourceConfiguration=source_config(image, spec))
        print(f"  {name}: updating")
        wait_ready(arn, name)
        try:
            ar.start_deployment(ServiceArn=arn)
            print(f"  {name}: deployment started")
        except Exception as exc:
            print(f"  {name}: start_deployment said {type(exc).__name__}")
        return arn, name

    r = ar.create_service(
        ServiceName=name,
        SourceConfiguration=source_config(image, spec),
        InstanceConfiguration={"Cpu": spec["cpu"], "Memory": spec["memory"],
                               "InstanceRoleArn": INSTANCE_ROLE},
        HealthCheckConfiguration={"Protocol": "HTTP", "Path": "/api/health", "Interval": 20,
                                  "Timeout": 15, "HealthyThreshold": 1, "UnhealthyThreshold": 5},
        NetworkConfiguration={"IngressConfiguration": {"IsPubliclyAccessible": True}},
        Tags=[{"Key": "project", "Value": "agents-for-humans-hackathon"}],
    )
    print(f"  {name}: creating")
    return r["Service"]["ServiceArn"], name


if __name__ == "__main__":
    only = sys.argv[1] if len(sys.argv) > 1 else None
    arns = {}
    for name, spec in SERVICES.items():
        if only and name != only:
            continue
        arn, _ = deploy(name, spec)
        arns[name] = arn

    print("\nwaiting for the rollout")
    for name, arn in arns.items():
        url = wait_ready(arn, name)
        if url:
            print(f"  {name}: https://{url}")
