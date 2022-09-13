#
# Purpose: Create Email Identity in SES
# NOTE:
# - If Email Identity exists and Not Verified, then Add Email Identity to force dispatch of verification email
#

import os
import boto3
import json
import logging
from datetime import date, datetime
import traceback
#import argparse

session = boto3.Session()

LOGGER = logging.getLogger()
if 'log_level' in os.environ:
    LOGGER.setLevel(os.environ['log_level'])
    LOGGER.info('Log level set to %s' % LOGGER.getEffectiveLevel())
else:
    LOGGER.setLevel(logging.ERROR)

#parser = argparse.ArgumentParser()
#parser.add_argument('member_email', help='Member Email Address')

def json_serial(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError('Type %s not serializable' % type(obj))


def get_email_identities(ses_client):
    email_identities = []
    try:
        paginator = ses_client.get_paginator('list_identities')
        iterator = paginator.paginate(
            IdentityType='EmailAddress'
        )
        for page in iterator:
            for identity in page['Identities']:
                email_identities.append(identity)
        return email_identities
    except Exception as e:
        LOGGER.error(f'failed in list_identities(..): {e}')
        LOGGER.error(str(e))
        LOGGER.error(traceback.format_exc())

def get_verification_status(ses_client, identity):
    try:
        response = ses_client.get_identity_verification_attributes(Identities=[ identity ])
        return response
    except Exception as e:
        LOGGER.error(f'failed in get_identity_verification_attributes(..):  {e}')
        LOGGER.error(str(e))
        LOGGER.error(traceback.format_exc())

def add_identity(ses_client, member_email):
    try:
        ses_client.verify_email_identity(EmailAddress=member_email)
        LOGGER.info('SES Identity for Member Email: {} created.'.format(member_email))
    except Exception as e:
        LOGGER.error(f'failed in verify_email_identity(..): {e}')
        LOGGER.error(str(e))
        LOGGER.error(traceback.format_exc())

def submit_email_verification(ses_client, email_address):
    email_identities = get_email_identities(ses_client)
    identity_verified = False
    if email_address in email_identities:
        response = get_verification_status(ses_client, email_address)
        #print(json.dumps(response, indent=2))
        verification_status = response['VerificationAttributes'].get(email_address, {'VerificationStatus': 'NotFound'})['VerificationStatus']
        LOGGER.info('Verification Status: {}'.format(verification_status))
        if verification_status == 'Success':
            LOGGER.info('SES Identity for Email Address: {} exists and verified. No further action required'.format(email_address))
            identity_verified = True
    else:
        LOGGER.info('SES Identity for Member Email: {} not found !')
        add_identity(ses_client, email_address)
    if not identity_verified:
        LOGGER.info('SES Identity for Member Email: {} exists, but Verification incomplete !')
        add_identity(ses_client, email_address)

def lambda_handler(event, context):
#def main():
    LOGGER.info(f"REQUEST RECEIVED: {json.dumps(event, default=str)}")
    account_email = event['account_email']
    #args = parser.parse_args()
    #member_email = args.member_email
    ses_client = session.client('ses')
    submit_email_verification(ses_client, account_email)
    # check if tech_owner_email exists
    if 'tech_owner_email' in event:
        tech_owner_email = event['tech_owner_email']
        submit_email_verification(ses_client, tech_owner_email)

#if __name__ == '__main__':
#    main()