#!/usr/bin/env python3
from os import environ
from os import path

from typing import List
import aws_cdk as cdk
from constructs import Construct
from aws_cdk import(
  aws_s3 as s3,
  aws_iam as iam,
  aws_logs as logs,
  aws_transfer as tfx,
  aws_lambda as lambda_,
)

SRC_ROOT_DIR = path.join(path.dirname(__file__),'src')

class DataStorageConstruct(Construct):
  def __init__(self, scope: Construct, id:str, **kwargs) -> None:
    super().__init__(scope, id, **kwargs)

    self.incoming_bucket = s3.Bucket(self,'Bucket',
      removal_policy= cdk.RemovalPolicy.DESTROY)
    
  def grant_read_write(self,identity:iam.IGrantable)->None:
    self.incoming_bucket.grant_read_write(identity)

class FunctionsConstruct(Construct):
  def __init__(self, scope: Construct, id:str, **kwargs) -> None:
    super().__init__(scope, id, **kwargs)

    self.scan_file_function = lambda_.DockerImageFunction(self,'ScanFile',
      description='Scans incoming file from TransferFamily Server',
      timeout= cdk.Duration.seconds(60),
      architecture= lambda_.Architecture.X86_64,
      log_retention= logs.RetentionDays.TWO_WEEKS,
      tracing= lambda_.Tracing.ACTIVE,
      environment={
        'asdf':'jkld'
      },
      code = lambda_.DockerImageCode.from_image_asset(
        directory=path.join(SRC_ROOT_DIR,'scanfile')))    

  def grant_invoke(self,identity:iam.IGrantable)->None:
    self.scan_file_function.grant_invoke(identity)

class TransferWorkflowConstruct(Construct):
  '''
  Creates the AWS Transfer Family Workflow.
  see: https://docs.aws.amazon.com/transfer/latest/userguide/nominal-steps-workflow.html
  '''
  @property
  def execution_role(self)->iam.IRole:
    return self.__execution_role

  @property
  def workflow(self)->tfx.CfnWorkflow:
    return self.__workflow

  def __init__(self, scope: Construct, id:str, **kwargs) -> None:
    super().__init__(scope, id, **kwargs)

    self.__execution_role = iam.Role(self,'ExecutionRole',
      assumed_by=iam.ServicePrincipal(service='transfer'))

    storage = DataStorageConstruct(self,'Storage', **kwargs)
    storage.grant_read_write(self.execution_role)

    functions = FunctionsConstruct(self,'Functions')
    #functions.grant_invoke(self.execution_role)

    self.__workflow = tfx.CfnWorkflow(self,'Definition',
      steps=[
        tfx.CfnWorkflow.WorkflowStepProperty(
          type= "COPY",
          copy_step_details={
            "Name":"CopyStep",
            "DestinationFileLocation":{
              "S3FileLocation":{
                'Bucket': storage.incoming_bucket.bucket_name,
                'Key':'incoming/'
              }
            }}),
        tfx.CfnWorkflow.WorkflowStepProperty(
          type= "CUSTOM",
          custom_step_details={
            "Name":"VirusScan",
            "Target": functions.scan_file_function.function_arn,
            "TimeoutSeconds": functions.scan_file_function.timeout.to_seconds()
          }),
        tfx.CfnWorkflow.WorkflowStepProperty(
          type= "TAG",
          tag_step_details={
            "Name":"MarkApproved",
            "Tags": [{ 
              'Key': "MalwareStatus",
              'Value':"Clean"
            }]
          }),
      ])

  def to_details(self)->tfx.CfnServer.WorkflowDetailProperty:
    return tfx.CfnServer.WorkflowDetailProperty(
      execution_role=self.execution_role.role_arn,
      workflow_id= self.workflow.ref
    )

class TransferServerConstruct(Construct):
  def __init__(self, scope: Construct, id:str, **kwargs) -> None:
    super().__init__(scope, id, **kwargs)

    logging_role = iam.Role(self,'LoggingRole',
      assumed_by=iam.ServicePrincipal(service='transfer'),
      managed_policies=[
        iam.ManagedPolicy.from_aws_managed_policy_name('CloudWatchLogsFullAccess')
      ])

    transfer_workflow = TransferWorkflowConstruct(self,'Workflow', **kwargs)
    self.server = tfx.CfnServer(self,'TransferServer',
      domain='S3',
      endpoint_type='PUBLIC',
      logging_role= logging_role.role_arn,
      protocols=['SFTP'],
      # workflow_details= tfx.CfnServer.WorkflowDetailsProperty(
      #   on_upload=[tfx.CfnServer.WorkflowDetailProperty()] transfer_workflow.workflow.
      # )
      )

class IngestionConstruct(Construct):
  def __init__(self, scope: Construct, id:str, **kwargs) -> None:
    super().__init__(scope, id, **kwargs)
    TransferServerConstruct(self,'TransferServer',**kwargs)
    return

class DefaultStack(cdk.Stack):
  def __init__(self, scope:Construct, id:str, **kwargs)->None:
    super().__init__(scope,id,**kwargs)
    IngestionConstruct(self,'Ingestion')
    return

class AntiVirusApp(cdk.App):
  def __init__(self, **kwargs)->None:
    super().__init__(**kwargs)
    DefaultStack(self,'AntiVirusStack',**kwargs)

app = AntiVirusApp()
app.synth()