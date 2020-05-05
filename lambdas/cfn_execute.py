""" this module executes cloudformation"""
import logging
import os
import boto3
from botocore.exceptions import ClientError


LOG_LEVEL = os.environ.get('LOG_LEVEL')
if LOG_LEVEL not in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
    LOG_LEVEL = 'INFO'

LOGGER = logging.getLogger()


def handler(event, _):
    """ the lambbda handler """
    LOGGER.info("Event: %s", event)
    lambda_input = event.get("Input")
    cfn_execute(lambda_input)

def cfn_execute(lambda_input):
    """ executes the cloudformation actions"""
    stack_name = lambda_input.get("StackName")
    input_json = lambda_input.get("Input")
    action = input_json.get("Action")
    LOGGER.info("Action: %s", action)
    try:
        if action == "Delete":
            delete_stack(stack_name)
        else:
            params = lambda_input.get("Parameters")
            parsed_params = get_params(params)
            tags = get_tags()
            update_create_stack(stack_name, parsed_params, tags)
    except Exception as exception:
        LOGGER.error("Issue processing request: %s", exception)
        raise exception

def delete_stack(stack_name):
    """ deletes a cloudformation stack"""
    get_cfn_client().delete_stack(StackName=stack_name)

def update_create_stack(stack_name, params, tags):
    """ if action is update or create"""
    valid_states = [
        'CREATE_COMPLETE',
        'ROLLBACK_COMPLETE',
        'UPDATE_COMPLETE',
        'UPDATE_ROLLBACK_COMPLETE',
    ]
    status = get_stack_status(stack_name)
    if status in valid_states:
        get_cfn_client().update_stack(
            StackName=stack_name,
            TemplateBody=parse_template("templates/lineplanner-rds-instances.yaml"),
            UsePreviousTemplate=False,
            Parameters=params,
            Capabilities=["CAPABILITY_AUTO_EXPAND"],
            Tags=tags
        )
    elif status == "STACK_NOT_EXISTS":
        get_cfn_client().create_stack(
            StackName=stack_name,
            TemplateBody=parse_template("templates/lineplanner-rds-instances.yaml"),
            Parameters=params,
            Capabilities=["CAPABILITY_AUTO_EXPAND"],
            Tags=tags,
            EnableTerminationProtection=False
        )
    else:
        LOGGER.error("Stack in bad state: %s", status)
        raise ClientError(
            {'Error': {
                'Code':'InternalError',
                'Message': f"Stack: {stack_name} in bad state for create/update: {status}"
                }
            },
            'create_stack')

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

def get_tags():
    """ todo get the actual tags"""
    return [{
        "Key": "BakeStack:Test",
        "Value": "test"
    }]

def parse_template(template):
    """ reads a json/yaml and validates in cfn """
    with open(template) as template_fileobj:
        template_data = template_fileobj.read()
    get_cfn_client().validate_template(TemplateBody=template_data)
    return template_data

def get_stack_status(stack_name):
    """ returns the true if exists """
    return_value = "STACK_NOT_EXISTS"
    stacks = []
    try:
        stacks = get_cfn_client().describe_stacks(
            StackName=stack_name
        ).get("Stacks")
    except ClientError as client_error:
        if not client_error.response.get("Error").get("Code") == "ValidationError":
            raise client_error
    LOGGER.info("Stack: %s", stacks)
    if stacks:
        return_value = stacks[0].get("StackStatus")
    LOGGER.info("Stack: %s Status: %s", stack_name, return_value)
    return return_value

def get_cfn_client(region="us-east-1"):
    """ gets the cloudformation client """
    return boto3.client("cloudformation", region)
