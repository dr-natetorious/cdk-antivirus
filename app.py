#!/usr/bin/env python3
from os import environ

from typing import List
import aws_cdk as cdk
from constructs import Construct
from aws_cdk import(
  aws_s3 as s3,
  aws_iam as iam,
  aws_transfer as tfx,
)

class DataStorageConstruct(Construct):
  def __init__(self, scope: Construct, id:str, **kwargs) -> None:
    super().__init__(scope, id, **kwargs)

    self.incoming_bucket = s3.Bucket(self,'Bucket',
      removal_policy= cdk.RemovalPolicy.DESTROY)
    
  def grant_read_write(self,identity:iam.IGrantable)->None:
    self.incoming_bucket.grant_read_write(identity)

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

    # self.__workflow = tfx.CfnWorkflow(self,'Definition',
    #   steps=[
    #     tfx.CfnWorkflow.WorkflowStepProperty(copy_step_details={
    #       "Name":"CopyStep",
    #       "DestinationFileLocation":{
    #         "S3FileLocation":{
    #           'Bucket': storage.incoming_bucket.bucket_name,
    #           'Key':'incoming/'
    #         }
    #       }
    #     })
    #   ])

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