import json
import boto3
import os
from datetime import datetime
from pprint import pprint

region = os.getenv("region")
ssm_client = boto3.client('ssm')
lambda_client = boto3.client('lambda')
event_client = boto3.client('events')
mydate = datetime.now()
month = mydate.strftime("%b")

#create ami-name from ec2 tags
def get_ami_name(instance):
    product = ''
    version = ''
    region = ''
    service = ''
    for tags in instance.tags:
        if tags["Key"] == 'Product':
            product = tags["Value"]
        elif tags["Key"] == 'Version':
            version = tags["Value"]
        elif tags["Key"] == 'Region':
            region = tags["Value"]
        elif tags["Key"] == 'Role':
            service = tags["Value"]
    ami_name = "PreWindowsUpdate-"+month+"-"+version+"-"+product+"-"+region+"-"+service
    return ami_name

#send email with msg and subject
def send_email(event):
    invoke_response = lambda_client.invoke(FunctionName="send-patch-status-mail",
                                         InvocationType='Event',
                                         Payload=json.dumps(event))
#convert string to datetime object
def dateTime(timeString):
    return datetime.strptime(timeString, "%Y-%m-%dT%H:%M:%S.%fZ")

#Get instance name  
def get_instance_name(instance):
    for tag in instance.tags:
            if(tag['Key'] == 'Name'):
                return tag['Value']

#construct email str              
def construct_mail_str(instance_ami_status):
    final_msg = ''
    success_instances_info = []
    pending_instances_info = []
    for info in instance_ami_status:
        line = "Instance Id: "+info['instance_id']+"\n"+"Instance Name: "+info['instance_name']+"\n"+"Image Name: "+info['ami_name']+"\n\n"
        if(info['ami_creation'] == 'success'):
            success_instances_info.append(line)
        else:
            pending_instances_info.append(line)
    for instance_info in pending_instances_info:
        final_msg = final_msg + instance_info
    if(len(pending_instances_info) > 0 and len(success_instances_info) > 0 ):
        final_msg = final_msg +"\n"+"The Trimble Forestry OS Patching Process has successfully created images for the following "+str(len(success_instances_info))+" instances\n"
    for instance_info in success_instances_info:
        final_msg = final_msg + instance_info
    return final_msg
    

def lambda_handler(event, context):
    #Get input from previous state in stepfunction
    regions = event['regions']
    patch_key = event['autopatch_key']
    #Increment verification attempts
    event['ami_creation_attempts'] = event['ami_creation_attempts']+1
    image_pending = 0
    image_created_by_region = 1
    instance_ami_status = []
    instances_count = 0
    #Iterate for each region
    for region in regions:
        image_created_by_region = 1
        #create session for the region
        current_session = boto3.Session(region_name = region)
        ec2_res = current_session.resource('ec2')
        ec2_client = current_session.client('ec2')
        try:
            #Get instances based on Autopatch tag 
            instances = ec2_res.instances.filter(Filters=[{'Name': 'tag:'+patch_key+'', 'Values': ['True']}])
            #get all images
            image_ob = ec2_client.describe_images(Owners=['self'])
            images = image_ob['Images']
            #Check if the images available are created have the valid attributes (ami-name,state,creation date)
            for instance in instances:
                instances_count = instances_count + 1
                ami_name = get_ami_name(instance)
                ami_status_info = {'instance_id':instance.id,'instance_name':get_instance_name(instance),'ami_name':ami_name,
                        'region':region,'ami_creation':None}
                image_created = 0
                for image in images:
                    if(image['Name'] == ami_name and image['State'] == 'available'):
                        image_created = 1
                        ami_status_info['ami_creation'] = 'success'
                if(image_created == 0):
                    ami_status_info['ami_creation'] = 'pending'
                    print("Not all images are created yet")
                    image_created_by_region = 0
                    image_pending += 1
                
                instance_ami_status.append(ami_status_info)
            if(image_created_by_region == 0):
                break
        except Excpetion as e:
            event['status'] = 'error'
            event['message'] = "Trimble Forestry OS Patching Process failed at the step \"Verify-Image-Creation\" with the following exception."+"\n"+str(e)
            event['subject'] = 'Failed'
            send_email(event)
            return event
            
    event['instance_details'] = construct_mail_str(instance_ami_status)
    event['instance_ami_status'] = instance_ami_status
    
    if(image_pending > 0 and event['ami_creation_attempts'] > event['max_attempts']):
        event['status'] = 'pending'
        event['message'] = "Please manually verify the Image creation and trigger the Trimble Forestry OS Patching Process again.\nThe Trimble Forestry OS Patching Process Image creation has been successfully triggered and is running longer than expected. So, manually verify the image creation for the following "+str(image_pending)+" instances.\n"
        event['subject'] = 'Image Creation InComplete'
        send_email(event)
    elif(image_pending > 0):
        event['status'] = 'pending'
        event['message'] = "Please manually verify the Image creation and trigger the Trimble Forestry OS Patching Process again.\nThe Trimble Forestry OS Patching Process Image creation has been successfully triggered and is running longer than expected. So, manually verify the image creation for the following "+str(image_pending)+" instances.\n"
        event['subject'] = 'Image Creation InComplete'
    else:
        event['status'] = 'success'
        event['message'] = "The Trimble Forestry OS Patching Process has successfully created images for the following "+str(instances_count)+" instances\n"
        event['subject'] = 'Image Creation Successful'
        send_email(event)
    return event
        

