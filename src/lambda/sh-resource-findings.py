import os
import sys
import json
import boto3
import logging
from datetime import datetime, date

session = boto3.Session()

LOGGER = logging.getLogger()
if 'log_level' in os.environ:
    LOGGER.setLevel(os.environ['log_level'])
    LOGGER.info('Log level set to %s' % LOGGER.getEffectiveLevel())
else:
    LOGGER.setLevel(logging.ERROR)

def json_serial(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError('Type %s not serializable' % type(obj))

def assume_role(org_id, aws_account_number, role_name):
    sts_client = boto3.client('sts')
    partition = sts_client.get_caller_identity()['Arn'].split(":")[1]
    response = sts_client.assume_role(
        RoleArn='arn:%s:iam::%s:role/%s' % (
            partition, aws_account_number, role_name
        ),
        RoleSessionName=str(aws_account_number+'-'+role_name),
        ExternalId=org_id
    )
    sts_session = boto3.Session(
        aws_access_key_id=response['Credentials']['AccessKeyId'],
        aws_secret_access_key=response['Credentials']['SecretAccessKey'],
        aws_session_token=response['Credentials']['SessionToken']
    )
    print("Assumed region_session for Account {}".format(aws_account_number))
    return sts_session

def get_findings(org_id, assume_role_name, account_id, region, resource_id):
    try:
        member_session = assume_role(org_id, account_id, assume_role_name)
        sh_client = member_session.client('securityhub', endpoint_url=f"https://securityhub.{region}.amazonaws.com", region_name=region)
        filters = {
            'ResourceId': [
                {
                    'Value': resource_id,
                    'Comparison': 'EQUALS'
                }
            ],
            'WorkflowStatus': [
                {
                    'Value': 'NEW',
                    'Comparison': 'EQUALS'
                },
                {
                    'Value': 'NOTIFIED',
                    'Comparison': 'EQUALS'
                }
            ],
            'RecordState': [
                {
                    'Value': 'ACTIVE',
                    'Comparison': 'EQUALS'
                }
            ],
            'ComplianceStatus': [
                {
                    'Value': 'FAILED',
                    'Comparison': 'EQUALS'
                }
            ],
            'SeverityLabel': [
                {
                    'Value': 'HIGH',
                    'Comparison': 'EQUALS'
                },
                {
                    'Value': 'CRITICAL',
                    'Comparison': 'EQUALS'
                }
            ]
        }
        lastObservedCriterion = {
            'Field': 'LastObservedAt',
            'SortOrder': 'desc'
        }
        sortCriteria = []
        sortCriteria.append(lastObservedCriterion)
        # Get latest 2 findings per Resource
        response = sh_client.get_findings(Filters=filters, SortCriteria=sortCriteria, MaxResults=2)
        return response['Findings']
    except Exception as e:
        LOGGER.error(f'failed in get_findings(..): {e}')
        LOGGER.error(str(e))

def lambda_handler(event, context):
    LOGGER.info(f"REQUEST RECEIVED: {json.dumps(event, default=str)}")
    member_insight_findings = []
    resProps = event['ResourceProperties']
    org_id = resProps['org_id']
    assume_role_name = resProps['assume_role']
    audit_account = resProps['audit_account']
    insight_arn = resProps['insight_arn']
    insight_name = resProps['insight_name']
    member_account = resProps['member_account']
    member_insight_results = resProps['member_insight_results']
    for result in member_insight_results:
        findings = get_findings(org_id, assume_role_name, member_account, result['ResourceRegion'], result['ResourceId'])
        member_insight_findings.append({
            'org_id': org_id,
            'assume_role': assume_role_name,
            'audit_account': audit_account,
            'insight_arn': insight_arn,
            'insight_name': insight_name,
            'member_account': member_account,
            'resource_findings': findings
        })
    return member_insight_findings