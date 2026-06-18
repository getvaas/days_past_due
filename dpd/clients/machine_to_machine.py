import requests
import logging

from .. import config
from ..utils import aws_boto_session

def get_token():
    if (config.M2M_TOKEN != "") and (config.M2M_TOKEN is not None):
        logging.info("returning cached token")
        return config.M2M_TOKEN
    # get M2M
    logging.info("Generating M2M token")
    ssm_client = aws_boto_session.get_session(config).client('ssm')
    auth0_client_id = ssm_client.get_parameter(Name=config.AUTH0_CLIENT_ID_PARAM)["Parameter"]["Value"]
    auth0_client_secret = ssm_client.get_parameter(Name=config.AUTH0_CLIENT_SECRET_PARAM)["Parameter"]["Value"]

    m2m_token_request = {
        'audience': config.AUTH0_AUDIENCE,
        'grant_type': 'client_credentials',
        'client_id': auth0_client_id,
        'client_secret': auth0_client_secret,
    }

    token_response = requests.post(config.AUTH0_ENDPOINT, m2m_token_request)
    token = token_response.json()["access_token"]
    config.M2M_TOKEN = token
    return token
