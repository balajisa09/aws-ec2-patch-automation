import json
import boto3
import datetime

mydate = datetime.datetime.now()
month = mydate.strftime("%b")


event_client = boto3.client('events')
lambda_client = boto3.client('lambda')
ssm_client = boto3.client('ssm')
        
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

#Get instance name  
def get_instance_name(instance):
    for tag in instance.tags:
            if(tag['Key'] == 'Name'):
                return tag['Value']

#Construct mail str                
def construct_mail_str(instances):
    final_msg =''
    for instance in instances:
        line = "Instance Id: "+instance.id+"\n"+"Instance Name: "+get_instance_name(instance)+"\n\n"
        final_msg = final_msg +line
    return final_msg
    
def lambda_handler(event, context):
    #Get data from stepfunction statemachine
    regions = event['regions']
    patch_key = event['autopatch_key']
    instances = None
    instances_count = 0
    #Iterate for each region
    for region in regions:
        #create session for the region
        current_session = boto3.Session(region_name = region)
        ec2_res = current_session.resource('ec2')
        ec2_client = current_session.client('ec2')
        #get instances based on tags
        instances = ec2_res.instances.filter(Filters=[{'Name': 'tag:'+patch_key+'', 'Values': ['True']}])
        #iterate each instance and create image 
        for instance in instances:
            instances_count = instances_count + 1
            ami_name = get_ami_name(instance)
            image_already_exist = 0
            #get all images
            image_ob = ec2_client.describe_images(Owners=['self'])
            images = image_ob['Images']
            #check if the image is already created for the month
            for image in images:
                if(image['Name'] == ami_name):
                    image_already_exist = 1
            if(image_already_exist == 1):
                print("Image already exist for the instance "+instance.id)
                continue
            #Create image and tag with instance-id to refer source
            try:
                ec2_client.create_image(InstanceId=instance.id, Name=ami_name,
                TagSpecifications=[
                        {
                            'ResourceType': 'image',
                            'Tags': [
                                {
                                    'Key': 'instance-id',
                                    'Value': '{}'.format(instance.id)
                                },
                                {
                                    'Key': 'created-by',
                                    'Value': 'auto-os-patch'
                                }
                            ]
                        },
                    ])
                print(instance.id)
            except Exception as e:
                event['status'] = 'error'
                event['message'] = "Trimble Forestry OS Patching Process failed at the step \"Create-AMI\" with the following exception."+"\n"+str(e)
                event['subject'] = "Failed"
                send_email(event)
                return event
    
    event['ami_creation_attempts'] = 0
    event['os_patch_attempts'] = 0
    event['status'] = 'success'
    event['subject'] = 'Triggered'
    event['message'] = "The Trimble Forestry OS Patching Process has been triggered for the following "+str(instances_count)+" instances\n"
    event['instance_details'] = construct_mail_str(instances)
    send_email(event)
    return event

