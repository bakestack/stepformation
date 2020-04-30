import os
import logging
import boto3
from botocore.exceptions import ClientError


LOG_LEVEL = os.environ.get('LOG_LEVEL')


if LOG_LEVEL not in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
    LOG_LEVEL = 'INFO'

LOGGER = logging.getLogger()
LOGGER.setLevel(LOG_LEVEL)


def get_cfn_client(region="us-east-1"):
    """ gets the cloudformation client """
    return boto3.client("cloudformation", region)

def handler(event, context):
    """ the lambbda handler """
    LOGGER.info("Event: %s", event)
    lambda_input = event.get("Input")
    stack_name = lambda_input.get("StackName")
    params = lambda_input.get("Parameters")
    parsed_params = get_params(params)
    tags = get_tags()
    status = get_stack_status(stack_name)
    invalid_states = [
        'CREATE_IN_PROGRESS',
        'CREATE_FAILED',
        'ROLLBACK_IN_PROGRESS',
        'ROLLBACK_FAILED',
        'DELETE_IN_PROGRESS',
        'DELETE_FAILED',
        'DELETE_COMPLETE',
        'UPDATE_IN_PROGRESS',
        'UPDATE_COMPLETE_CLEANUP_IN_PROGRESS',
        'UPDATE_ROLLBACK_IN_PROGRESS',
        'UPDATE_ROLLBACK_FAILED',
        'UPDATE_ROLLBACK_COMPLETE_CLEANUP_IN_PROGRESS',
        'REVIEW_IN_PROGRESS',
        'IMPORT_IN_PROGRESS',
        'IMPORT_ROLLBACK_IN_PROGRESS',
        'IMPORT_ROLLBACK_FAILED'
    ]
    if status not in invalid_states:
        get_cfn_client().update_stack(
            StackName=stack_name,
            TemplateBody=parse_template("lineplanner-rds-instances.yaml"),
            UsePreviousTemplate=False,
            Parameters=parsed_params,
            Capabilities=["CAPABILITY_AUTO_EXPAND"],
            Tags=tags,
            EnableTerminationProtection=False
        )
    elif status == "STACK_NOT_EXISTS":
        get_cfn_client().create_stack(
            StackName=stack_name,
            TemplateBody=parse_template("lineplanner-rds-instances.yaml"),
            Parameters=parsed_params,
            Capabilities=["CAPABILITY_AUTO_EXPAND"],
            Tags=tags,
            EnableTerminationProtection=False
        )

def get_params(params):
    """ gets the params"""
    parsed_params = list()
    for key in params:
        parsed_params.append({
            'ParameterKey': key,
            'ParameterValue': params.get(key),
            'UsePreviousValue': False
        })
    return parsed_params

def get_stack_status(stack_name):
    """ returns the true if exists """
    return_value = "STACK_NOT_EXISTS"
    try:
        stacks = get_cfn_client().describe_stacks(
            StackName=stack_name
        ).get("Stacks")
    except ClientError as client_error:
        if not client_error.response.get("Error").get("Code") == "ValidationError":
            raise client_error
    if stacks:
        return_value = stacks[0].get("StackStatus")
    LOGGER.info("Stack: %s Status: %s", stack_name, return_value)
    return return_value


def get_tags():
    """ todo get the actual tags"""
    return [{
        "Key": "Egalitrade:Test",
        "Value": "test"
    }]

def parse_template(template):
    """ reads a json/yaml and validates in cfn """
    with open(template) as template_fileobj:
        template_data = template_fileobj.read()
    get_cfn_client().validate_template(TemplateBody=template_data)
    return template_data
