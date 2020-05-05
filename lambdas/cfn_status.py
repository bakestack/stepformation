"""this module checks the status of cfn stack being deleted"""
import json
import logging
import os
import boto3
from botocore.vendored import requests

from botocore.exceptions import ClientError


LOG_LEVEL = os.environ.get('LOG_LEVEL')
if LOG_LEVEL not in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
    LOG_LEVEL = 'INFO'

LOGGER = logging.getLogger()
def handler(event, _):
    """ entry point """
    LOGGER.info("Event: %s", event)
    lambda_input = event.get("Input")
    stack_name = lambda_input.get("StackName")
    is_error = lambda_input.get("IsError")
    input_json = lambda_input.get("Input")
    if is_error:
        send(input_json.get("Url"), input_json.get("Data"), "FAILED")
    action = input_json.get("Action")
    status = get_handle_state(stack_name, action)
    if status != "WAIT":
        if status == "FAILED":
            send(input_json.get("Url"), input_json.get("Data"), "FAILED")
        else:
            send(input_json.get("Url"), input_json.get("Data"), "SUCCESS")
    return {"Status": status}

def get_handle_state(stack_name, action):
    """ handles the state """
    return_status = "FAILED"
    statuses = get_statuses_for_action(action)
    status = get_stack_status(stack_name)
    if status in statuses.get("Wait"):
        return_status = "WAIT"
    elif status in statuses.get("Complete"):
        return_status = "SUCCESS"
    return return_status

def send(response_url, response_body, status):
    """
    sends data back to custom resource
    this should only be used for errors or delete
    """
    response_body['Status'] = status
    response_body_str = json.dumps(response_body)
    LOGGER.info("Response body: %s", response_body_str)
    headers = {
        'content-type': '',
        'content-length': str(len(response_body_str))
    }
    try:
        response = requests.put(response_url, #pylint: disable=no-member
                                data=response_body_str,
                                headers=headers)
        LOGGER.info("Status code: %s", response.reason)
    except Exception as exception:  # pylint: disable=broad-except
        LOGGER.error(
            "send(..) failed executing requests.put(..): %s", str(exception))
        raise exception

def get_statuses_for_action(action):
    """ returns the appropriate wait or complete statuses
    for checking below"""
    delete_statuses = [
        "DELETE_IN_PROGRESS",
    ]
    delete_complete_statuses = [
        "STACK_NOT_EXISTS",
        "DELETE_COMPLETE"
    ]
    create_update_statuses = [
        "CREATE_IN_PROGRESS",
        "UPDATE_IN_PROGRESS",
        "UPDATE_COMPLETE_CLEANUP_IN_PROGRESS",
        "REVIEW_IN_PROGRESS"]
    create_update_complete_statuses = ["CREATE_COMPLETE", "UPDATE_COMPLETE"]

    statuses = {
        "Create": {
            "Complete": create_update_complete_statuses,
            "Wait": create_update_statuses
        },
        "Update": {
            "Complete": create_update_complete_statuses,
            "Wait": create_update_statuses
        },
        "Delete": {
            "Complete": delete_complete_statuses,
            "Wait": delete_statuses
        }
    }
    return statuses.get(action)

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
