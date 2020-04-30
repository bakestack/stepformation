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

def handler(event, _):
    """ entry point """
    LOGGER.info("Event: %s", event)
    lambda_input = event.get("Input")
    stack_name = lambda_input.get("StackName")
    return [{"done": get_handle_state(stack_name)}]


def get_handle_state(stack_name):
    """ handles the state """
    return_status = "Failure"
    waiting_statuses = [
        "CREATE_IN_PROGRESS",
        "UPDATE_IN_PROGRESS",
        "UPDATE_COMPLETE_CLEANUP_IN_PROGRESS",
        "REVIEW_IN_PROGRESS"]
    valid_statuses = ["CREATE_COMPLETE", "UPDATE_COMPLETE"]
    status = get_stack_status(stack_name)
    if status in waiting_statuses:
        return_status = "Wait"
    elif status in valid_statuses:
        return_status = "Success"
    return return_status


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
