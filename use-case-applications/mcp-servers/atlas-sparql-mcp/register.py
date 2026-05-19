"""
Registration script for atlas-sparql-mcp in AWS Agent Registry.

Reads the JSON descriptor from spec/04-aws-agent-registry/mcp-servers/atlas-sparql-mcp.json
and registers the MCP server with the Agent Registry via boto3.

Usage:
    python register.py --region us-east-1
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import boto3


SPEC_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "spec",
    "04-aws-agent-registry", "mcp-servers", "atlas-sparql-mcp.json"
)


def load_descriptor() -> dict:
    """Load the MCP server JSON descriptor."""
    with open(SPEC_PATH, "r") as f:
        return json.load(f)


def register(region: str, endpoint_override: str | None = None) -> dict:
    """Register atlas-sparql-mcp with the Agent Registry."""
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

    print(f"Registered atlas-sparql-mcp: {response}")
    return response


def main():
    parser = argparse.ArgumentParser(description="Register atlas-sparql-mcp")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--endpoint-override", default=None)
    args = parser.parse_args()

    register(args.region, args.endpoint_override)


if __name__ == "__main__":
    main()
