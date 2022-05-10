import json
import boto3

transfer = boto3.client('transfer')

def lambda_handler(event, context):
    print(json.dumps(event))

    # call the SendWorkflowStepState API to notify the worfklow about the step's SUCCESS or FAILURE status
    response = transfer.send_workflow_step_state(
      WorkflowId=event['serviceMetadata']['executionDetails']['workflowId'],
      ExecutionId=event['serviceMetadata']['executionDetails']['executionId'],
      Token=event['token'],
      Status='SUCCESS|FAILURE'
    )

    print(json.dumps(response))

    return {
      'statusCode': 200,
      'body': json.dumps(response)
    }