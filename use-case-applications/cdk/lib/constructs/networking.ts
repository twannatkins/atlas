/**
 * Networking construct — VPC lookup, security groups, NAT gateway.
 *
 * Does NOT create the VPC (that belongs to Workshop 1). Looks up the
 * existing VPC by ID and adds the security group rules Workshop 2 needs.
 *
 * Security groups follow least-privilege egress: Lambda functions can
 * reach Neptune (8182), Ontop (8080), and HTTPS (443 for Bedrock via NAT).
 * ECS tasks can reach Neptune (8182) and ECR/S3 (443 for image pulls).
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
  /** The private subnets as ISubnet objects, for constructs that need ec2.SubnetSelection. */
  public readonly privateSubnets: ec2.ISubnet[];

  constructor(scope: Construct, id: string, props: NetworkingProps) {
    super(scope, id);

    // Look up the existing VPC from Workshop 1
    this.vpc = ec2.Vpc.fromLookup(this, "Vpc", {
      vpcId: props.vpcId || undefined,
    });

    // Import private subnets as ISubnet objects so downstream constructs
    // (e.g. AgentCore runtimes) can pass them as ec2.SubnetSelection.
    //
    // AgentCore VPC mode constraint: only subnets in supported AZs can be used.
    // In us-east-1, AgentCore supports use1-az1 (us-east-1c), use1-az2 (us-east-1d),
    // and use1-az4 (us-east-1a). It does NOT support use1-az6 (us-east-1b).
    // The privateSubnetIds context value must exclude any subnet in an unsupported AZ.
    // In this account: subnet-028d75e13e01a02ef (us-east-1b/use1-az6) is excluded.
    this.privateSubnets = props.privateSubnetIds.map((id) =>
      ec2.Subnet.fromSubnetId(this, `PrivateSubnet-${id}`, id),
    );

    // Security group for Lambda functions — restricted egress
    this.lambdaSecurityGroup = new ec2.SecurityGroup(this, "LambdaSG", {
      vpc: this.vpc,
      description: "ATLAS Workshop 2 - Lambda functions",
      allowAllOutbound: false,
    });

    // Security group for Ontop ECS Fargate — restricted egress
    this.ecsSecurityGroup = new ec2.SecurityGroup(this, "EcsSG", {
      vpc: this.vpc,
      description: "ATLAS Workshop 2 - Ontop ECS Fargate",
      allowAllOutbound: false,
    });

    // --- Lambda egress rules ---

    // Lambda → Neptune on port 8182 (SPARQL queries)
    this.lambdaSecurityGroup.addEgressRule(
      ec2.Peer.anyIpv4(),
      ec2.Port.tcp(8182),
      "Lambda to Neptune SPARQL",
    );

    // Lambda → Ontop on port 8080 (SPARQL-over-relational federation)
    this.lambdaSecurityGroup.addEgressRule(
      this.ecsSecurityGroup,
      ec2.Port.tcp(8080),
      "Lambda to Ontop SPARQL endpoint",
    );

    // Lambda → HTTPS (443) for Bedrock API calls via NAT and AWS service endpoints
    this.lambdaSecurityGroup.addEgressRule(
      ec2.Peer.anyIpv4(),
      ec2.Port.tcp(443),
      "Lambda to Bedrock and AWS APIs via NAT",
    );

    // --- ECS egress rules ---

    // ECS → Neptune on port 8182 (Ontop queries Neptune for R2RML federation)
    this.ecsSecurityGroup.addEgressRule(
      ec2.Peer.anyIpv4(),
      ec2.Port.tcp(8182),
      "Ontop to Neptune SPARQL",
    );

    // ECS → HTTPS (443) for ECR image pulls and S3 access
    this.ecsSecurityGroup.addEgressRule(
      ec2.Peer.anyIpv4(),
      ec2.Port.tcp(443),
      "Ontop to ECR and S3 for image pulls",
    );

    // --- ECS ingress rules ---

    // Allow Lambda → Ontop on port 8080
    this.ecsSecurityGroup.addIngressRule(
      this.lambdaSecurityGroup,
      ec2.Port.tcp(8080),
      "Lambda to Ontop SPARQL endpoint",
    );
  }
}
