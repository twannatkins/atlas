/**
 * Lake Formation tag policies — persona-scoped data access.
 *
 * Tags are applied to Iceberg table columns and rows. Policies grant
 * access based on the Cognito group claim. This is Layer 3 (Data layer)
 * of the four-layer permission model.
 *
 * Why Lake Formation: Neptune's IAM access control operates at the cluster
 * level. Lake Formation operates at row and column level on the Iceberg
 * tables that Ontop federates. Without it, a Consumer Banker's query
 * returns all customers, not just their assigned book.
 */

import * as cdk from "aws-cdk-lib";
import * as lakeformation from "aws-cdk-lib/aws-lakeformation";
import { Construct } from "constructs";

export interface LakeFormationProps {
  personas: string[];
}

export class LakeFormationConstruct extends Construct {
  constructor(scope: Construct, id: string, props: LakeFormationProps) {
    super(scope, id);

    // LF-Tag: atlas:persona — row-level scoping
    new lakeformation.CfnTag(this, "PersonaTag", {
      tagKey: "atlas:persona",
      tagValues: [
        "consumer-banker",
        "wealth-advisor",
        "bsa-analyst",
        "ontology-steward",
        "auditor",
      ],
    });

    // LF-Tag: atlas:sensitivity — column-level masking
    new lakeformation.CfnTag(this, "SensitivityTag", {
      tagKey: "atlas:sensitivity",
      tagValues: ["public", "pii", "sar-restricted"],
    });

    // Tag associations and permissions would be configured per-table
    // in a production deployment. For the workshop, the tags are created
    // here and associated manually during the pre-flight notebook or
    // via a separate data-engineering pipeline.
    //
    // The key architectural point: these tags exist so that Ontop's
    // SPARQL-to-SQL translation respects persona boundaries. When a
    // Consumer Banker's query arrives at Ontop, the SQL it generates
    // runs against Lake Formation-scoped views that only return rows
    // tagged with their persona.
  }
}
