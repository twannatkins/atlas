/**
 * Networking construct — VPC lookup, security groups, NAT gateway.
 *
 * Does NOT create the VPC (that belongs to Workshop 1). Looks up the
 * existing VPC by ID and adds the security group rules Workshop 2 needs.
 */

import * as cdk from "aws-cdk-lib";
import * as ec2 from "aws-cdk-lib/aws-ec2";
import { Construct } from "constructs";

export interface NetworkingProps {
  vpcId: string;
  privateSubnetIds: string[];
}

export class NetworkingConstruct extends Construct {
  public readonly vpc: ec2.IVpc;
  public readonly lambdaSecurityGroup: ec2.SecurityGroup;
  public readonly ecsSecurityGroup: ec2.SecurityGroup;

  constructor(scope: Construct, id: string, props: NetworkingProps) {
    super(scope, id);

    // Look up the existing VPC from Workshop 1
    this.vpc = ec2.Vpc.fromLookup(this, "Vpc", {
      vpcId: props.vpcId || undefined,
    });

    // Security group for Lambda functions — allows outbound to Neptune (8182)
    // and outbound HTTPS (443) for Bedrock API calls via NAT
    this.lambdaSecurityGroup = new ec2.SecurityGroup(this, "LambdaSG", {
      vpc: this.vpc,
      description: "ATLAS Workshop 2 — Lambda functions",
      allowAllOutbound: true, // NAT for Bedrock; Neptune on 8182
    });

    // Security group for Ontop ECS Fargate — allows inbound from Lambda SG
    this.ecsSecurityGroup = new ec2.SecurityGroup(this, "EcsSG", {
      vpc: this.vpc,
      description: "ATLAS Workshop 2 — Ontop ECS Fargate",
      allowAllOutbound: true,
    });

    // Allow Lambda → Ontop on port 8080
    this.ecsSecurityGroup.addIngressRule(
      this.lambdaSecurityGroup,
      ec2.Port.tcp(8080),
      "Lambda to Ontop SPARQL endpoint",
    );

    // Allow Lambda → Neptune on port 8182
    this.lambdaSecurityGroup.addEgressRule(
      ec2.Peer.anyIpv4(),
      ec2.Port.tcp(8182),
      "Lambda to Neptune SPARQL",
    );
  }
}
