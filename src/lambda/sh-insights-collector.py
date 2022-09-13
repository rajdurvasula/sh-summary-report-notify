import os
import sys
import json
import boto3
import urllib3
import logging
from datetime import date, datetime
import time
from arnparse import arnparse

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
    LOGGER.info("Assumed region_session for Account {}".format(aws_account_number))
    return sts_session

def get_members(sh_admin_client):
    member_list = []
    try:
        paginator = sh_admin_client.get_paginator('list_members')
        iterator = paginator.paginate(OnlyAssociated=True)
        for page in iterator:
            for member in page['Members']:
                member_list.append({
                    'AccountId': member['AccountId'],
                    'Email': member['Email'],
                    'MemberStatus': member['MemberStatus']
                })
        return member_list
    except Exception as e:
        LOGGER.error(f'failed in list_members(..): {e}')
        LOGGER.error(str(e))

def get_insight_data(sh_admin_client, insight_arn_suffix):
    sh_insight_arn = 'arn:aws:securityhub:::insight/securityhub/default/{}'.format(insight_arn_suffix)
    try:
        paginator = sh_admin_client.get_paginator('get_insights')
        iterator = paginator.paginate(
            InsightArns=[sh_insight_arn]
        )
        for page in iterator:
            for insight in page['Insights']:
                return insight
    except Exception as e:
        LOGGER.error(f'failed in get_insights(..): {e}')
        LOGGER.error(str(e))

def member_insight_results(sh_admin_client, insight_data, member_account):
    account_insight_results = []
    try:
        response = sh_admin_client.get_insight_results(InsightArn=insight_data['InsightArn'])
        for result in response['InsightResults']['ResultValues']:
            #print(json.dumps(result, indent=2))
            # parse resource arn
            #arn:aws:ec2:us-west-2:863224780407:instance/i-0575030ea9e05460d
            resource_arn = arnparse(result['GroupByAttributeValue'])
            if resource_arn.account_id is not None and resource_arn.account_id == member_account:
                print('Resource Id: %s' % resource_arn.resource)
                print('Resource Region: %s' % resource_arn.region)
                print('Number of Findings: %d' % result['Count'])
                account_insight_results.append({
                    'AccountId': resource_arn.account_id,
                    'ResourceId': result['GroupByAttributeValue'],
                    'ResourceRegion': resource_arn.region
                })
        return account_insight_results
    except Exception as e:
        LOGGER.error(f'failed in get_insight_results(..): {e}')
        LOGGER.error(str(e))

def lambda_handler(event, context):
    LOGGER.info(f"REQUEST RECEIVED: {json.dumps(event, default=str)}")
    resProps = event['ResourceProperties']
    org_id = resProps['org_id']
    assume_role_name = resProps['assume_role']
    audit_account = resProps['audit_account']
    insight_arn_suffix = resProps['insight_arn_suffix']
    sh_admin_session = assume_role(org_id, audit_account, assume_role_name)
    sh_admin_client = sh_admin_session.client('securityhub')
    insight_data = get_insight_data(sh_admin_client, insight_arn_suffix)
    member_list = get_members(sh_admin_client)
    members_insights_results = []
    for member_json in member_list:
        member_account = member_json['AccountId']
        print('Insights for Member: %s' % member_account)
        member_results = member_insight_results(sh_admin_client, insight_data, member_account)
        if len(member_results) > 0:
            members_insights_results.append({
                'org_id': org_id,
                'assume_role': assume_role_name,
                'audit_account': audit_account,
                'insight_arn': insight_data['InsightArn'],
                'insight_name': insight_data['Name'],
                'member_account': member_account,
                'member_insight_results': member_results
            })
    return members_insights_results
