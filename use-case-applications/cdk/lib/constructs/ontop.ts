/**
 * Ontop on ECS Fargate — SPARQL-over-relational translation layer.
 *
 * Translates SPARQL queries into SQL against Lake Formation Iceberg tables.
 * Minimum task count of 1 to avoid cold starts (Ontop caches R2RML mappings
 * and maintains a JDBC connection pool).
 *
 * The internal ALB uses HTTPS with an ACM certificate to encrypt SPARQL
 * queries in transit between Lambda and Ontop.
 */

import * as cdk from "aws-cdk-lib";
import * as ec2 from "aws-cdk-lib/aws-ec2";
import * as ecs from "aws-cdk-lib/aws-ecs";
import * as elbv2 from "aws-cdk-lib/aws-elasticloadbalancingv2";
import * as acm from "aws-cdk-lib/aws-certificatemanager";
import { Construct } from "constructs";

export interface OntopProps {
  vpc: ec2.IVpc;
  securityGroup: ec2.SecurityGroup;
  neptuneEndpoint: string;
  /** ACM certificate ARN for the internal ALB HTTPS listener. */
  certificateArn?: string;
}

export class OntopConstruct extends Construct {
  public readonly endpoint: string;

  constructor(scope: Construct, id: string, props: OntopProps) {
    super(scope, id);

    const cluster = new ecs.Cluster(this, "Cluster", {
      vpc: props.vpc,
      containerInsights: true,
    });

    const taskDef = new ecs.FargateTaskDefinition(this, "TaskDef", {
      memoryLimitMiB: 2048,
      cpu: 1024,
    });

    // Ontop container — uses the official ontop/ontop image.
    // DEFERRED: atlas.obda and atlas.properties mapping files are not yet authored.
    // The service runs with desiredCount:0 (no tasks) so the stack deploys cleanly.
    // Restore desiredCount to 1 and provide mapping files before enabling Ontop queries.
    taskDef.addContainer("Ontop", {
      image: ecs.ContainerImage.fromRegistry("ontop/ontop:5.5.0"),
      portMappings: [{ containerPort: 8080 }],
      environment: {
        ONTOP_MAPPING_FILE: "/opt/ontop/mappings/atlas.obda",
        ONTOP_PROPERTIES_FILE: "/opt/ontop/mappings/atlas.properties",
        JDBC_URL: `jdbc:neptune:sparql://${props.neptuneEndpoint}:8182/sparql`,
      },
      logging: ecs.LogDrivers.awsLogs({ streamPrefix: "ontop" }),
      healthCheck: {
        command: ["CMD-SHELL", "curl -f http://localhost:8080/health || exit 1"],
        interval: cdk.Duration.seconds(30),
        timeout: cdk.Duration.seconds(5),
        retries: 3,
      },
    });

    // Fargate service — desiredCount:0 until atlas.obda + atlas.properties are authored.
    // Set to 1 once mapping files are in place to enable live Ontop queries.
    const service = new ecs.FargateService(this, "Service", {
      cluster,
      taskDefinition: taskDef,
      desiredCount: 0,
      securityGroups: [props.securityGroup],
      assignPublicIp: false,
    });

    // Internal ALB — consumed by atlas-sparql-mcp
    const alb = new elbv2.ApplicationLoadBalancer(this, "ALB", {
      vpc: props.vpc,
      internetFacing: false,
    });

    if (props.certificateArn) {
      // Production / deployed workshop: HTTPS listener with ACM certificate
      const certificate = acm.Certificate.fromCertificateArn(
        this,
        "Cert",
        props.certificateArn,
      );
      const listener = alb.addListener("Listener", {
        port: 443,
        certificates: [certificate],
      });
      listener.addTargets("OntopTarget", {
        port: 8080,
        targets: [service],
        healthCheck: { path: "/health" },
      });
      this.endpoint = `https://${alb.loadBalancerDnsName}`;
    } else {
      // Local development / workshop without a custom domain: HTTP listener.
      // Acceptable only because the ALB is internal (not internet-facing)
      // and traffic stays within the VPC. For production, always provide
      // a certificateArn.
      const listener = alb.addListener("Listener", { port: 80 });
      listener.addTargets("OntopTarget", {
        port: 8080,
        targets: [service],
        healthCheck: { path: "/health" },
      });
      this.endpoint = `http://${alb.loadBalancerDnsName}`;
    }
  }
}
