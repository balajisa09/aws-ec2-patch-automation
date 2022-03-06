import json
import boto3
import os
from datetime import datetime
from pprint import pprint

region = os.getenv("region")
lambda_client = boto3.client('lambda')
ssm_client = boto3.client('ssm')

#Send email with msg and subject
def send_email(event):
    invoke_response = lambda_client.invoke(FunctionName="send-patch-status-mail",
                                         InvocationType='Event',
                                         Payload=json.dumps(event))

#convert string to datetime object
def dateTime(timeString):
    return datetime.strptime(timeString, "%Y-%m-%dT%H:%M:%S.%fZ")
 
#Get latest image by creation date
def getLastestImage(images):
    creation_time = []
    latest_image = None
    for image in images:
            datetime_obj = dateTime(image['CreationDate'])
            creation_time.append(datetime_obj)
            if(max(creation_time) == datetime_obj):
                latest_image = image
    return latest_image
    
def lambda_handler(event, context):
    #Get input from previous state in stepfunction
    regions = event['regions']
    patch_key = event['autopatch_key']
    #Iterate for each region
    for region in regions:
        #Create session for the region
        current_session = boto3.Session(region_name = region)
        ec2_res = current_session.resource('ec2')
        ec2_client = current_session.client('ec2')
        #Get all images
        image_ob = ec2_client.describe_images(Owners=['self'])
        images = image_ob['Images']
        
        #Get ami-created instances
        ami_success_instance_ids = []
        for ami_status_info in event['instance_ami_status']:
            if(ami_status_info['region'] == region and ami_status_info['ami_creation'] == 'success'):
                ami_success_instance_ids.append(ami_status_info['instance_id'])
                
        #Get instances with successful image creation
        instances = ec2_res.instances.filter(InstanceIds= ami_success_instance_ids)
        successful_instances = []
        for instance in instances:
            successful_instances.append(instance.id)
            
        #Iterate each instance with successful image creation
        for instance in successful_instances:
            matching_images = []
            #Iterate each image to find related images for the instance with instance-id tag
            for image in images:
                instanceFlag = False
                createdFlag = False
                if 'Tags' in image:
                    for tags in image['Tags']:
                        if(tags['Key'] == 'instance-id'):
                            if(tags['Value'] == instance):
                                instanceFlag = True
                        if(tags['Key'] == 'created-by'):
                            if(tags['Value'] == 'auto-os-patch'):
                                createdFlag = True
                if(instanceFlag and createdFlag):
                #adding images of respective instances
                    matching_images.append(image)
                    
            print(matching_images)
            #get second latest image for the instance
            second_latest_image = None
            if(len(matching_images) == 0):
                print("No image detected for "+instance)
                continue
            elif(len(matching_images) == 1):
                print("Only one image found ...skipping deletion")
                continue
            else:
                latest_image = getLastestImage(matching_images)
                matching_images.remove(latest_image)
                second_latest_image = getLastestImage(matching_images)
                #deregister second latest image of the instance
                print("Deleting " + second_latest_image['ImageId'] +" of instance "+instance)
                try:
                    ec2_client.deregister_image(ImageId=second_latest_image['ImageId'], DryRun=False)
                except Exception as e:
                    event['status'] = 'error'
                    event['message'] = "Error in Deleting the AMI "+second_latest_image['ImageId']+"\n"+str(e)
                    event['subject'] = 'AMI Deletion Error'
                    send_email(event)
                    return event
                #Deleting respective snapshots
                print("Deleting Snapshot")
                for snapshot in second_latest_image['BlockDeviceMappings']:
                    if 'SnapshotId' in snapshot['Ebs']:
                        snapshotId = snapshot['Ebs']['SnapshotId']
                        ec2_client.delete_snapshot(SnapshotId=snapshotId, DryRun=False)
        
    event['status'] = 'success'
    event['message'] = 'Old AMIs are Deleted successfully'
    event['subject'] = 'AMI Deletion Success'
    
    return event
