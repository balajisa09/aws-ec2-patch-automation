# OS Patch Automation - Terraform

This terraform project is used to setup lambda functions, s3 bucket, IAM roles and policies required to automate OS patch in AWS EC2 instances.

## Automation plan

![alt text](https://github.com/Balaji-SA/-AWS-EC2-Patch-Automation/blob/master/images/OS-patch-automation-plan.jpeg?raw=true)

## Prerequisite

- Verify SSM agent is online for all EC2 Instances.
- Configure $HOME/.aws/credentials file with the access key and secret key of the IAM user as a default profile.
- Create an IAM role that has policies to create lambda functions,step function, s3 bucket, SNS topic and attach it to the IAM user.

## Steps to follow

- Git clone the repository .
- Install terraform.
- Navigate to TF-OS-Patching-Process/main and execute terraform init.
- Execute terrform plan and terraform apply.
- Schedule and enable the cloudwatch event created by terraform with JSON input referring the document above.

## Step function state machine created by Terraform

![alt text](https://github.com/Balaji-SA/-AWS-EC2-Patch-Automation/blob/master/images/stepfunctions_graph.png?raw=true)



