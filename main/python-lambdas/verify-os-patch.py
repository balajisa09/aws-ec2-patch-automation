import json
import boto3
from pprint import pprint
import datetime

ssm_client = boto3.client('ssm')
lambda_client = boto3.client('lambda')
event_client = boto3.client('events')

#send email with msg and subject
def send_email(event):
    invoke_response = lambda_client.invoke(FunctionName="send-patch-status-mail",
                                         InvocationType='Event',
                                         Payload=json.dumps(event))

#Construct email str                                         
def construct_mail_str(instance_patch_status):
    final_msg = ''
    success_instances_info = []
    pending_instances_info = []
    instances_count = 0
    for info in instance_patch_status:
        line = "Instance Id: "+info['instance_id']+"\n"+"Instance Name: "+info['instance_name']+"\n"+"Patch Status: "+info['patch_status']+"\n\n"
        if(info['patch_status'] == 'success'):
            success_instances_info.append(line)
        else:
            pending_instances_info.append(line)
    if(len(pending_instances_info) > 0):
        final_msg = final_msg + "The Trimble Forestry OS Patching Process os patching has failed/timed out for the following "+str(len(pending_instances_info))+" instances.\n"
    for instance_info in pending_instances_info:
        final_msg = final_msg + instance_info
    if(len(pending_instances_info) > 0 and len(success_instances_info) > 0):
        final_msg = final_msg +"The Trimble Forestry OS Patching Process has successfully patched the following "+str(len(success_instances_info))+" instances\n"
    for instance_info in success_instances_info:
        final_msg = final_msg + instance_info
    return final_msg

#Get instance name  
def get_instance_name(instance):
    for tag in instance.tags:
            if(tag['Key'] == 'Name'):
                return tag['Value']
                
def lambda_handler(event, context):
    #Get input from previous state in stepfunctions
    regions = event['regions']
    if 'command_ids' in event:
        command_ids = event['command_ids']
    else:
        event['status'] = "success"
        event['message'] = 'No Instances to patch'
        event['subject'] = 'Pending Image Creation'
        return event
    patch_key = event['autopatch_key']
    #Increment OS patch verification attempts
    event['os_patch_attempts'] =event['os_patch_attempts']+1
    #Check if all OS patches are success
    patch_pending = 0
    patch_by_region = 1
    instance_patch_status = []
    instances_count = 0
    #Iterate for each region
    for region in regions:
        patch_by_region = 1
        #Create session for the region
        current_session = boto3.Session(region_name = region)
        ec2_res = current_session.resource('ec2')
        ssm_client_region = current_session.client('ssm')
        
        #Get instances with successful image creation
        ami_success_instance_ids = []
        for ami_status_info in event['instance_ami_status']:
            if(ami_status_info['region'] == region and ami_status_info['ami_creation'] == 'success'):
                ami_success_instance_ids.append(ami_status_info['instance_id'])
                
        instance_ids = []
        instances = ec2_res.instances.filter(InstanceIds= ami_success_instance_ids)
        for instance in instances:
            instance_ids.append(instance.id)
            
        #Check patch status for each instance
        for instance in instances:
            instances_count = instances_count+1
            patch_status_info = {'instance_id':instance.id,'instance_name':get_instance_name(instance),
                        'region':region,'patch_status':None}
            response = ssm_client_region.get_command_invocation(
            CommandId= command_ids[region],
            InstanceId=instance.id
            )
            cmd_status = response['Status']
            if(cmd_status == 'Success'):
                patch_status_info['patch_status'] = 'success'
            else:
                patch_pending += 1
                patch_status_info['patch_status'] = 'pending'
                patch_by_region = 0
                
            instance_patch_status.append(patch_status_info)
        if(patch_by_region == 0):
            break
    event['instance_details'] = construct_mail_str(instance_patch_status)
    if(patch_pending > 0 ):
        event['status'] = 'pending'
        event['message'] = "Please manually verify the OS patching command with IDs "+json.dumps(command_ids)+" under SSM > Run Command.\n"
        event['subject'] = 'OS Patching Incomplete'
    else:
        event['status'] = 'success'
        event['message'] = "The Trimble Forestry OS Patching Process has successfully patched the following "+str(instances_count) +" instances\n"
        event['subject'] = 'OS Patching Successful'

    return event
