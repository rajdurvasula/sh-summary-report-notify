import os
import json
import traceback
import boto3
from datetime import date, datetime
import logging

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

def get_members(sh_admin_client):
    member_list = []
    try:
        paginator = sh_admin_client.get_paginator('list_members')
        iterator = paginator.paginate(OnlyAssociated=True)
        for page in iterator:
            for member in page['Members']:
                member_list.append({
                    'account_id': member['AccountId'],
                    'account_email': member['Email'],
                    'sh_status': member['MemberStatus']
                })
        return member_list
    except Exception as e:
        LOGGER.error(f'failed in list_members(..): {e}')
        LOGGER.error(str(e))

# TODO: add any other email addresses as needed using query
def get_dyndb_account_emails(db_client, table_name, member):
    account_id = member['account_id']
    LOGGER.info('Query Additional Email addresses associated with Account: {} ..'.format(account_id))
    dyn_expr_value = {
        ':ac_id': {
            'S': account_id
        }
    }
    try:
        response = db_client.query(
            TableName=table_name,
            Select='ALL_ATTRIBUTES',
            KeyConditionExpression='account_id = :ac_id',
            ExpressionAttributeValues=dyn_expr_value
        )
        #print(json.dumps(response, indent=2))
        if len(response['Items']) == 1:
            member.update({
                'tech_owner_email': response['Items'][0]['tech_owner_email']['S']
            })
            return member
        else:
            return None
    except Exception as e:
        LOGGER.error(f'Failed in query(..): {e}')
        LOGGER.error(str(e))
        LOGGER.error(traceback.format_exc())

#def main():
def lambda_handler(event, context):
    LOGGER.info(f"REQUEST RECEIVED: {json.dumps(event, default=str)}")
    table_name = os.environ['table_name']
    sh_admin_client = session.client('securityhub')
    db_client = session.client('dynamodb')
    member_emails_list = []
    member_list = get_members(sh_admin_client)
    for member in member_list:
        member_emails = get_dyndb_account_emails(db_client, table_name, member)
        if member_emails != None:
            member_emails_list.append(member_emails)
    LOGGER.info('Member Count: %s' % str(len(member_emails_list)))
    return {
        'member_list': member_emails_list
    }

#if __name__ == '__main__':
#    main()
