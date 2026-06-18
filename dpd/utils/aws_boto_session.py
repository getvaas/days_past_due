import boto3
import logging


def get_session(config):
    logging.info("Getting session")
    if config.LOCAL_ENV and config.AWS_PROFILE_NAME:
        return boto3.session.Session(profile_name=config.AWS_PROFILE_NAME)
    else:
        return boto3.session.Session()


def get_s3_client(config):
    return get_session(config).client("s3")


def get_secrets_client(config):
    return get_session(config).client("secretsmanager")


def get_sns_client(config):
    return get_session(config).client("sns")
