#
# Collect summary of:
# 1. Security Hub Findings by severity 
# 2. Security Hub Findings by Standard
# Standards Queried:
# 1. AWS Foundations Security Best Practices - Software and Configuration Checks/Industry and Regulatory Standards
# 2. AWS Foundations Security Best Practices - Effects/Data Exposure
# 3. CIS AWS Foundations Benchmark - Software and Configuration Checks/Industry and Regulatory Standards
#

import os
import sys
import json
import boto3
import csv
#import argparse
import urllib3
import logging
from datetime import date, datetime
import time


session = boto3.Session()

aws_standard_types = 'Software and Configuration Checks/Industry and Regulatory Standards/AWS-Foundational-Security-Best-Practices'
aws_dataexposure_types = 'Effects/Data Exposure/AWS-Foundational-Security-Best-Practices'
cis_standard_types = 'Software and Configuration Checks/Industry and Regulatory Standards/CIS AWS Foundations Benchmark'
standard_types = [
    aws_standard_types,
    aws_dataexposure_types,
    cis_standard_types
]

#parser = argparse.ArgumentParser()
#parser.add_argument('member_account', help='Member Account Id')

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

def create_severity_summary_insight(sh_admin_client, member_account, standard_type):
    insight_name = '{}-severity-insight-{}'.format(member_account, datetime.now().strftime('%Y%m%d%H%M%S'))
    print('Creating Insight for Standard Type: {}'.format(standard_type))
    filters = {
        'AwsAccountId': [
            {
                'Value': member_account,
                'Comparison': 'EQUALS'
            }
        ],
        'ComplianceStatus': [
            {
                'Value': 'FAILED',
                'Comparison': 'EQUALS'
            }
        ],
        'RecordState': [
            {
                'Value': 'ACTIVE',
                'Comparison': 'EQUALS'
            }
        ],
        'Type': [
            {
                'Value': standard_type,
                'Comparison': 'EQUALS'
            }
        ],
        'WorkflowStatus': [
            {
                'Value': 'NEW',
                'Comparison': 'EQUALS'
            }
        ]
    }
    try:
        response = sh_admin_client.create_insight(Name=insight_name, Filters=filters, GroupByAttribute='SeverityLabel')
        LOGGER.info(json.dumps(response, indent=2))
        return response['InsightArn']
    except Exception as e:
        LOGGER.error(f'failed in create_insight(..): {e}')
        LOGGER.error(str(e))

def create_type_findings_insight(sh_admin_client, member_account):
    insight_name = '{}-type-insight-{}'.format(member_account, datetime.now().strftime('%Y%m%d%H%M%S'))
    filters = {
        'AwsAccountId': [
            {
                'Value': member_account,
                'Comparison': 'EQUALS'
            }
        ],
        'ComplianceStatus': [
            {
                'Value': 'FAILED',
                'Comparison': 'EQUALS'
            }
        ],
        'ProductName': [
            {
                'Value': 'Security Hub',
                'Comparison': 'EQUALS'
            }
        ],
        'RecordState': [
            {
                'Value': 'ACTIVE',
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
        ]
    }    
    try:
        response = sh_admin_client.create_insight(Name=insight_name, Filters=filters, GroupByAttribute='Type')
        LOGGER.info(json.dumps(response, indent=2))
        return response['InsightArn']
    except Exception as e:
        LOGGER.error(f'failed in create_insight(..): {e}')
        LOGGER.error(str(e))

def delete_insight(sh_admin_client, insight_arn):
    try:
        sh_admin_client.delete_insight(InsightArn=insight_arn)
        LOGGER.info('Deleted Insight: {}'.format(insight_arn))
    except Exception as e:
        LOGGER.error(f'failed in delete_insight(..): {e}')
        LOGGER.error(str(e))

def get_summary_result(sh_admin_client, insight_arn):
    try:
        response = sh_admin_client.get_insight_results(InsightArn=insight_arn)
        return response['InsightResults']['ResultValues']
    except Exception as e:
        LOGGER.error(f'failed in get_insight_results(..): {e}')
        LOGGER.error(str(e))

def lambda_handler(event, context):
#def main():
    #args = parser.parse_args()
    LOGGER.info(f"REQUEST RECEIVED: {json.dumps(event, default=str)}")
    member_account = event['account_id']
    account_email = event['account_email']
    tech_owner_email = ''
    if 'tech_owner_email' in event:
        tech_owner_email = event['tech_owner_email']
    #member_account = args.member_account
    sh_admin_client = session.client('securityhub')
    member_summary_data = {}
    standard_severity_list = []
    insight_arns = []
    # Get Insight Results Findings count by severity for each of: AWS Foundations, CIS
    for standard_type in standard_types:
        insight_arn = create_severity_summary_insight(sh_admin_client, member_account, standard_type)
        result = get_summary_result(sh_admin_client, insight_arn)
        standard_severity_list.append({
            'standard_type': standard_type,
            'result': result
        })
        insight_arns.append(insight_arn)
    member_summary_data.update({'severity_count': standard_severity_list})
    # Get Insight Results by Standard Type
    insight_arn = create_type_findings_insight(sh_admin_client, member_account)
    insight_arns.append(insight_arn)
    result = get_summary_result(sh_admin_client, insight_arn)
    # removed spaces
    member_summary_data.update({ 'SecurityHub': result })
    # delete insights
    for insight_arn in insight_arns:
        delete_insight(sh_admin_client, insight_arn)
    #print(json.dumps(member_summary_data, indent=2))
    return {
        'account_id': member_account,
        'account_email': account_email,
        'tech_owner_email': tech_owner_email,
        'severity_count': member_summary_data['severity_count'],
        'SecurityHub': member_summary_data['SecurityHub']
    }

#if __name__ == '__main__':
#    main()

