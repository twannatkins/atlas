"""
Registration script for atlas-registry-mcp in AWS Agent Registry.

Usage:
    python register.py --region us-east-1
"""

from __future__ import annotations

import argparse
import json
import os

import boto3


SPEC_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "spec",
    "04-aws-agent-registry", "mcp-servers", "atlas-registry-mcp.json"
)


def load_descriptor() -> dict:
    with open(SPEC_PATH, "r") as f:
        return json.load(f)


def register(region: str, endpoint_override: str | None = None) -> dict:
    descriptor = load_descriptor()

    kwargs = {"region_name": region}
    if endpoint_override:
        kwargs["endpoint_url"] = endpoint_override

    client = boto3.client("bedrock-agentcore", **kwargs)

    response = client.register_mcp_server(
        mcpServerName=descriptor["mcp_server_name"],
        description=descriptor["description"],
        version=descriptor["version"],
        operations=descriptor["operations"],
        registryMetadata=descriptor.get("registry_metadata", {}),
    )

    print(f"Registered atlas-registry-mcp: {response}")
    return response


def main():
    parser = argparse.ArgumentParser(description="Register atlas-registry-mcp")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--endpoint-override", default=None)
    args = parser.parse_args()

    register(args.region, args.endpoint_override)


if __name__ == "__main__":
    main()
