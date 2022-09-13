import os
import sys
import json
import boto3
import logging
from datetime import datetime, date
import traceback

# env variables
# sender_email = 'kd-audit@kyndryl.com'
# template_name = <set by stack>

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

def send_notification(ses_client, sender_email_address, to_email_address, cc_email_addresses, template_name, member_summary_data):
    destination = {
        'ToAddresses': [ to_email_address ]
    }
    # If cc_email_addresses has an email address, then add cc
    if len(cc_email_addresses) > 0:
        destination = {
            'ToAddresses': [ to_email_address ],
            'CcAddresses': [ cc_email_addresses ]
        }
    try:
        response = ses_client.send_templated_email(
            Source=sender_email_address,
            Destination=destination,
            Template=template_name,
            TemplateData=json.dumps(member_summary_data)
        )
        print(json.dumps(response, indent=2))
    except Exception as e:
        LOGGER.error(f'failed in send_templated_email(..): {e}')
        LOGGER.error(str(e))
        print(traceback.format_exc())

def lambda_handler(event, context):
    LOGGER.info(f"REQUEST RECEIVED: {json.dumps(event, default=str)}")
    member_account = event['account_id']
    to_address = event['account_email']
    cc_addresses = ''
    if 'tech_owner_email' in event:
        cc_addresses = event['tech_owner_email']
    severity_count = event['severity_count']
    security_hub = event['SecurityHub']
    member_summary_data = {
        'member_account': member_account,
        'severity_count': severity_count,
        'SecurityHub': security_hub
    }
    sender_email_address = os.environ['sender_email']
    template_name = os.environ['template_name']
    ses_client = session.client('ses')
    LOGGER.info("Sending Summary Report Data ..")
    status = send_notification(ses_client, sender_email_address, to_address, cc_addresses, template_name, member_summary_data)
    if len(cc_addresses) > 0:
        return {
            'account_id': member_account,
            'to_address': to_address,
            'cc_addresses': cc_addresses,
            'member_summary': member_summary_data,
            'email_template': template_name
        }
    else:
        return {
            'account_id': member_account,
            'to_address': to_address,
            'member_summary': member_summary_data,
            'email_template': template_name
        }

