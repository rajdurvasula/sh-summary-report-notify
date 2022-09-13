import { CfnParameter, Duration, Stack, StackProps } from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as cdk from 'aws-cdk-lib';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as ses from 'aws-cdk-lib/aws-ses';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import * as sf from 'aws-cdk-lib/aws-stepfunctions';
import * as tasks from 'aws-cdk-lib/aws-stepfunctions-tasks';
import * as dyndb from 'aws-cdk-lib/aws-dynamodb';
import * as ev from 'aws-cdk-lib/aws-events';
import * as evt from 'aws-cdk-lib/aws-events-targets';
import * as path from 'path';

export class ShFindingIntimationsStack extends Stack {
  constructor(scope: Construct, id: string, props?: StackProps) {
    super(scope, id, props);

    const accountId = cdk.Stack.of(this).account;
    const region = cdk.Stack.of(this).region;
    // Context Keys
    // SenderEmail

    // parameters
    const template_name  = new CfnParameter(this, 'TemplateName', {
      type: 'String',
      description: 'Email Template Name',
      default: 'SHSummaryReportMember'
    });
    const dyndb_table_name = new CfnParameter(this, 'DynamoDBTableName', {
      type: 'String',
      description: 'DynamoDB Table name to import account-emails.csv data',
      default: 'account-emails'
    });

    // sts policy
    /*
    const stsPolicy = new iam.Policy(this, 'sts-policy', {
      statements: [
        new iam.PolicyStatement({
          actions: [
            'sts:AssumeRole'
          ],
          effect: iam.Effect.ALLOW,
          resources: [
            "arn:aws:iam::*:role/AWSControlTowerExecution"
          ]
        }),
        new iam.PolicyStatement({
          actions: [
            "sts:GetSessionToken",
            "sts:GetAccessKeyInfo",
            "sts:GetCallerIdentity"
          ],
          effect: iam.Effect.ALLOW,
          resources: [ "*" ]
        })
      ]
    });
    */
    // securityhub policy
    const shPolicy = new iam.Policy(this, 'sh-policy', {
      statements: [
        new iam.PolicyStatement({
          actions: [
            "securityhub:ListInvitations",
            "securityhub:DescribeHub",
            "securityhub:GetMasterAccount",
            "securityhub:ListEnabledProductsForImport",
            "securityhub:GetFreeTrialEndDate",
            "securityhub:GetInvitationsCount",
            "securityhub:DescribeOrganizationConfiguration",
            "securityhub:GetInsightFindingTrend",
            "securityhub:GetFindingAggregator",
            "securityhub:GetFindings",
            "securityhub:SendInsightEvents",
            "securityhub:DescribeProducts",
            "securityhub:GetInsights",
            "securityhub:GetAdministratorAccount",
            "securityhub:ListOrganizationAdminAccounts",
            "securityhub:GetMembers",
            "securityhub:DescribeActionTargets",
            "securityhub:GetEnabledStandards",
            "securityhub:ListControlEvaluationSummaries",
            "securityhub:GetInsightResults",
            "securityhub:GetFreeTrialUsage",
            "securityhub:ListMembers",
            "securityhub:GetControlFindingSummary",
            "securityhub:DescribeStandards",
            "securityhub:GetUsage",
            "securityhub:GetAdhocInsightResults",
            "securityhub:DescribeStandardsControls",
            "securityhub:SendFindingEvents",
            "securityhub:DeleteInsight",
            "securityhub:CreateInsight",
          ],
          effect: iam.Effect.ALLOW,
          resources: [
            `arn:aws:securityhub:*:${accountId}:finding-aggregator/*`,
            `arn:aws:securityhub:*:${accountId}:hub/default`
          ]
        }),
        new iam.PolicyStatement({
          actions: [
            "securityhub:BatchGetStandardsControlAssociations",
            "securityhub:ListSecurityControlDefinitions",
            "securityhub:ListFindingAggregators"
          ],
          effect: iam.Effect.ALLOW,
          resources: [ "*" ]
        })
      ]
    });
    // lambda policy
    const lambdaPolicy = new iam.Policy(this, 'lambda-policy', {
      statements: [
        new iam.PolicyStatement({
          actions: [
            'lambda:CreateFunction',
            'lambda:TagResource',
            'lambda:InvokeFunction',
            'lambda:GetFunction',
            'lambda:InvokeAsync',
            'lambda:DeleteFunction',
            'lambda:UntagResource'
          ],
          effect: iam.Effect.ALLOW,
          resources: [
            `arn:aws:lambda:${region}:${accountId}:function:*SHSummaryCollector`,
            `arn:aws:lambda:${region}:${accountId}:function:*SHEmailNotify`,
            `arn:aws:lambda:${region}:${accountId}:function:*AddSESIdentity`,
            `arn:aws:lambda:${region}:${accountId}:function:*GetSHMembers`,
          ]
        })
      ]
    });
    // sns policy
    /*
    const snsPolicy = new iam.Policy(this, 'sns-policy', {
      statements: [
        new iam.PolicyStatement({
          actions: [
            "sns:TagResource",
            "sns:ListSubscriptionsByTopic",
            "sns:Publish",
            "sns:GetTopicAttributes",
            "sns:DeleteTopic",
            "sns:CreateTopic",
            "sns:SetTopicAttributes",
            "sns:Subscribe",
            "sns:ConfirmSubscription",
            "sns:UntagResource"
          ],
          effect: iam.Effect.ALLOW,
          resources: [
            `arn:aws:sns:*:${accountId}:*`
          ]
        }),
        new iam.PolicyStatement({
          actions: [
            "sns:SetSubscriptionAttributes",
            "sns:ListTopics",
            "sns:Unsubscribe",
            "sns:GetSubscriptionAttributes",
            "sns:ListSubscriptions"
          ],
          effect: iam.Effect.ALLOW,
          resources: [ "*" ]
        })
      ]
    });
    */
    // cw policy
    const cwPolicy = new iam.Policy(this, 'cw-policy', {
      statements: [
        new iam.PolicyStatement({
          actions: [
            "logs:CreateLogGroup",
            "logs:CreateLogStream",
            "logs:PutLogEvents"
          ],
          effect: iam.Effect.ALLOW,
          resources: [
            `arn:aws:logs:${region}:${accountId}:log-group:/aws/lambda/*`
          ]
        })
      ]
    });
    // ses policy
    const sesPolicy = new iam.Policy(this, 'ses-policy', {
      statements: [
        new iam.PolicyStatement({
          actions: [
            "ses:SendEmail",
            "ses:SendBulkEmail",
            "ses:SendTemplatedEmail",
            "ses:SendBulkTemplatedEmail"
          ],
          effect: iam.Effect.ALLOW,
          resources: [
            "*"
          ]
        }),
        new iam.PolicyStatement({
          actions: [
            "ses:ListTemplates",
            "ses:GetAccountSendingEnabled",
            "ses:DeleteTemplate",
            "ses:GetIdentityPolicies",
            "ses:GetSendQuota",
            "ses:GetIdentityVerificationAttributes",
            "ses:GetIdentityNotificationAttributes",
            "ses:ListVerifiedEmailAddresses",
            "ses:GetTemplate",
            "ses:ListIdentities",
            "ses:VerifyEmailIdentity",
            "ses:DeleteIdentity",
            "ses:DeleteVerifiedEmailAddress",
            "ses:VerifyEmailAddress"
          ],
          effect: iam.Effect.ALLOW,
          resources: [
            "*"
          ]
        })
      ]
    });
    const xrayPolicy = new iam.Policy(this, 'xray-policy', {
      statements: [
        new iam.PolicyStatement({
          actions: [
            "xray:PutTraceSegments",
            "xray:PutTelemetryRecords",
            "xray:GetSamplingRules",
            "xray:GetSamplingTargets"
          ],
          effect: iam.Effect.ALLOW,
          resources: [ "*" ]
        })
      ]
    });
    const dyndbPolicy = new iam.Policy(this, 'dyndb-policy', {
      statements: [
        new iam.PolicyStatement({
          actions: [
            "dynamodb:GetItem",
            "dynamodb:Scan",
            "dynamodb:Query"
          ],
          effect: iam.Effect.ALLOW,
          resources: [
            `arn:aws:dynamodb:${region}:${accountId}:table/${dyndb_table_name.valueAsString}`,
            `arn:aws:dynamodb:${region}:${accountId}:table/${dyndb_table_name.valueAsString}/index/*`
          ]
        }),
        new iam.PolicyStatement({
          actions: [
            "dynamodb:ListGlobalTables",
            "dynamodb:ListTables"
          ],
          effect: iam.Effect.ALLOW,
          resources: [ "*" ]
        })
      ]
    });
    // Role for sh-insights-collector lambda
    /*
    const shInsightsCollectorRole = new iam.Role(this, 'SHInsightsCollectorRole',  {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      description: 'Role for SHInsightsCollector Lambda'
    });
    shInsightsCollectorRole.attachInlinePolicy(cwPolicy);
    shInsightsCollectorRole.attachInlinePolicy(stsPolicy);
    shInsightsCollectorRole.attachInlinePolicy(shPolicy);
    // sh-insights-collector
    const shInsightsCollector = new lambda.Function(this, 'SHInsightsCollector', {
      code: lambda.Code.fromAsset('src/lambda/sh-insights-collector.zip'),
      description: 'Lambda to find Security Hub Insight Results for Member Accounts',
      environment: {
        'log_level': 'INFO'
      },
      functionName: 'SHInsightsCollector',
      handler: 'sh-insights-collector.lambda_handler',
      memorySize: 512,
      role: shInsightsCollectorRole,
      runtime: lambda.Runtime.PYTHON_3_9,
      timeout: Duration.seconds(900)
    });
    */
    // Role for sh-resource-findings
    /*
    const shResourceFindingsRole = new iam.Role(this, 'SHResourceFindingsRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      description: 'Role for SHResourceFindings Lambda'
    });
    shResourceFindingsRole.attachInlinePolicy(cwPolicy);
    shResourceFindingsRole.attachInlinePolicy(stsPolicy);
    shResourceFindingsRole.attachInlinePolicy(shPolicy);
    // sh-resource-findings
    const shResourceFindings = new lambda.Function(this, 'SHResourceFindings', {
      code: lambda.Code.fromAsset('src/lambda/sh-resource-findings.zip'),
      description: 'Lambda to get Security Hub Findings for Member Account Resource',
      environment: {
        'log_level': 'INFO'
      },
      functionName: 'SHResourceFindings',
      handler: 'sh-resource-findings.lambda_handler',
      role: shResourceFindingsRole,
      runtime: lambda.Runtime.PYTHON_3_9,
      timeout: Duration.seconds(900)
    });
    */
    // Role for sh-summary-collector
    const shSummaryCollectorRole = new iam.Role(this, 'SHSummaryCollectorRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      description: 'Role for SHSummaryCollector Lambda'
    });
    shSummaryCollectorRole.attachInlinePolicy(cwPolicy);
    shSummaryCollectorRole.attachInlinePolicy(shPolicy);
    // sh-summary-collector
    const shSummaryCollector = new lambda.Function(this, 'SHSummaryCollector', {
      code: lambda.Code.fromAsset('src/lambda/sh-summary-collector.zip'),
      description: 'Lambda to get Security Hub summary data for Member Account',
      environment: {
        'log_level': 'INFO'
      },
      functionName: 'SHSummaryCollector',
      handler: 'sh-summary-collector.lambda_handler',
      role: shSummaryCollectorRole,
      runtime: lambda.Runtime.PYTHON_3_9,
      timeout: Duration.seconds(900)
    });
    // Role for sh-email-notify
    const shEmailNotifyRole = new iam.Role(this, 'SHEmailNotifyRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      description: 'Role for SHEmailNotify Lambda'
    });
    shEmailNotifyRole.attachInlinePolicy(cwPolicy);
    shEmailNotifyRole.attachInlinePolicy(sesPolicy);
    // sh-email-notify
    const shEmailNotify = new lambda.Function(this, 'SHEmailNotify', {
      code: lambda.Code.fromAsset('src/lambda/sh-email-notify.zip'),
      description: 'Lambda to send email notifications',
      environment: {
        'log_level': 'INFO',
        'sender_email': this.node.tryGetContext("SenderEmail"),
        'template_name': template_name.valueAsString
      },
      functionName: 'SHEmailNotify',
      handler: 'sh-email-notify.lambda_handler',
      role: shEmailNotifyRole,
      runtime: lambda.Runtime.PYTHON_3_9,
      timeout: Duration.seconds(900)
    });
    // Role for add-ses-identity
    const addSesIdentityRole = new iam.Role(this, 'AddSESIdentityRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      description: 'Role for AddSESIdentity Lambda'
    });
    addSesIdentityRole.attachInlinePolicy(cwPolicy);
    addSesIdentityRole.attachInlinePolicy(sesPolicy);
    // add-ses-identity
    const addSesIdentity = new lambda.Function(this, 'AddSESIdentity', {
      code: lambda.Code.fromAsset('src/lambda/add-ses-identity.zip'),
      description: 'Lambda to add SES Email Identity',
      environment: {
        'log_level': 'INFO'
      },
      functionName: 'AddSESIdentity',
      handler: 'add-ses-identity.lambda_handler',
      role: addSesIdentityRole,
      runtime: lambda.Runtime.PYTHON_3_9,
      timeout: Duration.seconds(60)
    });
    // Role for get-sh-members
    const getShMembersRole = new iam.Role(this, 'GetSHMembersRole', {
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      description: 'Role for GetSHMembers'
    });
    getShMembersRole.attachInlinePolicy(cwPolicy);
    getShMembersRole.attachInlinePolicy(shPolicy);
    getShMembersRole.attachInlinePolicy(dyndbPolicy);
    // get-sh-members
    const getShMembers = new lambda.Function(this, 'GetSHMembers', {
      code: lambda.Code.fromAsset('src/lambda/get-sh-members.zip'),
      description: 'Lambda to get SecurityHub Members',
      environment: {
        'log_level': 'INFO',
        'table_name': dyndb_table_name.valueAsString
      },
      functionName: 'GetSHMembers',
      handler: 'get-sh-members.lambda_handler',
      role: getShMembersRole,
      runtime: lambda.Runtime.PYTHON_3_9,
      timeout: Duration.seconds(300)
    });
    // Role for SESIdentitiesSM statemachine
    const sesIdentitiesSMRole = new iam.Role(this, 'SESIdentitiesSMRole', {
      assumedBy: new iam.ServicePrincipal('states.amazonaws.com'),
      description: 'Role for SESIdentitiesSM StateMachine'
    });
    sesIdentitiesSMRole.attachInlinePolicy(lambdaPolicy);
    sesIdentitiesSMRole.attachInlinePolicy(xrayPolicy);
    // Task for get-sh-members
    const getShMembersTask = new tasks.LambdaInvoke(this, 'Get Members', {
      lambdaFunction: getShMembers,
      comment: "Get Security Hub enabled Member Accounts",
      outputPath: "$.Payload"
    });
    // Task for add-ses-identity
    const addSesIdentityTask = new tasks.LambdaInvoke(this, 'Add Identity', {
      lambdaFunction: addSesIdentity,
      comment: 'Check and Add SES Identity for Member Email',
      outputPath: "$.Payload"
    });
    // For each Member
    const eachMember = new sf.Map(this, 'Each Member', {
      comment: "Process each Member",
      itemsPath: "$.member_list",
      maxConcurrency: 1
    });
    eachMember.iterator(addSesIdentityTask);
    // chain tasks and nodes
    const smDefinition = getShMembersTask.next(eachMember)
    // state machine
    const sesIdentitiesSM = new sf.StateMachine(this, 'SESIdentitiesSM', {
      definition: smDefinition,
      role: sesIdentitiesSMRole,
      stateMachineName: 'SESIdentitiesSM',
      stateMachineType: sf.StateMachineType.STANDARD
    });

    // Role for EmailNotifySHSummaryReportSM statemachine
    const emailNotifySHSummaryReportSMRole = new iam.Role(this, 'EmailNotifySHSummaryReportSMRole', {
      assumedBy: new iam.ServicePrincipal('states.amazonaws.com'),
      description: 'Role for EmailNotifySHSummaryReportSM statemachine'
    });
    emailNotifySHSummaryReportSMRole.attachInlinePolicy(lambdaPolicy);
    emailNotifySHSummaryReportSMRole.attachInlinePolicy(xrayPolicy);
    // Unique Task for get-sh-members
    const getShMembers1Task = new tasks.LambdaInvoke(this, 'Get SH Members', {
      lambdaFunction: getShMembers,
      comment: "Get Security Hub enabled Member Accounts",
      outputPath: "$.Payload"
    });
    // Task for sh-summary-collector
    const shSummaryCollectorTask = new tasks.LambdaInvoke(this, 'Collect Summary Report', {
      lambdaFunction: shSummaryCollector,
      comment: 'Collect Security Hub Insight Summary data',
      outputPath: '$.Payload'
    });
    // Task for sh-email-notify
    const shEmailNotifyTask = new tasks.LambdaInvoke(this, 'Send Email', {
      lambdaFunction: shEmailNotify,
      comment: 'Send Email with Security Hub Summary Report',
      outputPath: '$.Payload'
    });
    // link tasks
    shSummaryCollectorTask.next(shEmailNotifyTask);
    // For each Account
    const eachAccount = new sf.Map(this, 'Each Account', {
      comment: "Process each Member",
      itemsPath: "$.member_list",
      maxConcurrency: 1
    });
    eachAccount.iterator(shSummaryCollectorTask);
    // link tasks and nodes
    const smDefinition1 = getShMembers1Task.next(eachAccount);
    // state machine
    const emailNotifySHSummaryReportSM = new sf.StateMachine(this, 'EmailNotifySHSummaryReportSM', {
      definition: smDefinition1,
      role: emailNotifySHSummaryReportSMRole,
      stateMachineName: 'EmailNotifySHSummaryReportSM',
      stateMachineType: sf.StateMachineType.STANDARD
    });
    // DLQ for Scheduled Event Rule
    const shSummaryReportNotificationRuleDLQ = new sqs.Queue(this, 'SHSummaryReportNotificationRuleDLQ');
    // Policies to manage EventBridge Rule
    const evPolicy = new iam.Policy(this, 'ev-policy', {
      statements: [
        new iam.PolicyStatement({
          actions: [
            "events:PutEvents",
            "events:PutTargets",
            "events:EnableRule",
            "events:PutRule"
          ],
          effect: iam.Effect.ALLOW,
          resources: [
            `arn:aws:events:${region}:${accountId}:rule/default/*`,
            `arn:aws:events:${region}:${accountId}:event-bus/default`
          ]
        }),
        new iam.PolicyStatement({
          actions: [
            "events:PutTargets",
            "events:EnableRule",
            "events:PutRule"
          ],
          effect: iam.Effect.ALLOW,
          resources: [
            `arn:aws:events:${region}:${accountId}:rule/*`
          ]
        })
      ]
    });
    // Policies to launch StateMachine
    const smPolicy = new iam.Policy(this, 'sm-policy', {
      statements: [
        new iam.PolicyStatement({
          actions: [
            "states:StartExecution"
          ],
          effect: iam.Effect.ALLOW,
          resources: [
            `arn:aws:states:${region}:${accountId}:stateMachine:*EmailNotifySHSummaryReportSM`
          ]
        })
      ]
    });
    // Role for Scheduled Event Rule
    const shSummaryReportNotificationRuleRole = new iam.Role(this, 'SHSummaryReportNotificationRuleRole', {
      assumedBy: new iam.ServicePrincipal('events.amazonaws.com'),
      description: 'Role to launch EmailNotifySHSummaryReportSM statemachine'
    });
    shSummaryReportNotificationRuleRole.attachInlinePolicy(evPolicy);
    shSummaryReportNotificationRuleRole.attachInlinePolicy(smPolicy)
    // Scheduled Event Rule
    const shSummaryReportNotificationRule = new ev.Rule(this, 'SHSummaryReportNotificationRule', {
      description: 'Scheduled Event Rule for SecurityHub Summary Report Notification',
      enabled: true,
      ruleName: 'SHSummaryReportNotificationRule',
      schedule: ev.Schedule.cron({
        hour: '9',
        minute: '0',
        month: '*',
        weekDay: '2',
        year: '*'
      }),
      targets: [
        new evt.SfnStateMachine(emailNotifySHSummaryReportSM, {
          deadLetterQueue: shSummaryReportNotificationRuleDLQ,
          role: shSummaryReportNotificationRuleRole
        })
      ]
    });
  };
}
