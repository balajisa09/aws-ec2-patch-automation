import json
import boto3
import json
from pprint import pprint

ssm_client = boto3.client('ssm')
event_client = boto3.client('events')
lambda_client = boto3.client('lambda')
s3_res = boto3.resource('s3')
s3_client = boto3.client('s3')
#Send email with msg and subject
def send_email(event):
    invoke_response = lambda_client.invoke(FunctionName="send-patch-status-mail",
                                         InvocationType='Event',
                                         Payload=json.dumps(event))
                                         
def lambda_handler(event, context):
    #Get input from the previous state in stepfunction
    regions = event['regions']
    patch_key = event['autopatch_key']
    command_ids = {}
    
    #Get patch Baseline
    baseline_session = boto3.Session(region_name = regions[0])
    ssm_client = baseline_session.client('ssm')
    s3_res =  baseline_session.resource('s3')
    baseline_overrides = []
    baseline_overrides.append(ssm_client.get_patch_baseline(
        BaselineId=event['baseline_id']
    ))
    s3_bucket_name = event['bucket_name']
    s3_file_name = event['baseline_filename']
    json_content = json.dumps(baseline_overrides, indent=4, sort_keys=True, default=str)
    try:
        s3_res.Object(bucket_name=s3_bucket_name, key=s3_file_name).put(Body = json_content)
    except Exception as e:
        print(e)
    bucket_location = s3_client.get_bucket_location(Bucket=s3_bucket_name)['LocationConstraint']
    print(bucket_location)
    baseline_obj_url = "https://"+s3_bucket_name+".s3."+bucket_location+".amazonaws.com/"+s3_file_name
    print(baseline_obj_url)
    
    #Iterate for each region
    for region in regions:
        #Create session for the region
        current_session = boto3.Session(region_name = region)
        ec2_res = current_session.resource('ec2')
        ssm_client_region = current_session.client('ssm')
        instance_ids = []
        
        #Get ami-created instances
        ami_success_instance_ids = []
        for ami_status_info in event['instance_ami_status']:
            if(ami_status_info['region'] == region and ami_status_info['ami_creation'] == 'success'):
                ami_success_instance_ids.append(ami_status_info['instance_id'])
                
        #Get instances with successful image creation
        instances = None
        if(len(ami_success_instance_ids) > 0):
            instances = ec2_res.instances.filter(InstanceIds= ami_success_instance_ids)
        if(instances != None):
            for instance in instances:
                instance_ids.append(instance.id)
        print(len(instance_ids))
        
        #No instane with successful image creation . Move to next step
        if(len(instance_ids) == 0):
            event['status'] = 'success'
            return event
            
        #Apply patch baseline for each instance
        try:
            response = ssm_client_region.send_command(
            InstanceIds= instance_ids,
            DocumentName='AWS-RunPatchBaseline',
             Parameters={
                'Operation': [
                    'Install',
                ],
                'BaselineOverride':[baseline_obj_url]
            },)
        except Exception as e:
            event['status'] = 'error'
            event['message'] = "Error in applying patch. Check if SSM agents are online \n "+str(e)
            event['subject'] = 'OS Patch Error'
            send_email(event)
            return event
        
        command_id = response['Command']['CommandId']
        command_ids[region]  = command_id

    #Add the command ids to the event object
    event['command_ids'] = command_ids
    event['status'] = 'success'
    event['message'] = 'OS patch for all instances are executed'
    event['subject'] = 'OS Patch Initiated'
    return event
