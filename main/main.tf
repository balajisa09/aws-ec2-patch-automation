

#Create IAM role
module "lambda_os_patch_iam_role" {
  source = "../modules/iam-role"
}

locals {
  function_names = ["create-ami-ec2", "verify-image-creation","delete-old-ami-ec2","start-os-patch","verify-os-patch","send-patch-status-mail"]
}

#Deploy Lambda functions
module "lambda_functions" {
  source = "../modules/lambda-functions"
  function_names = local.function_names
  lambda_iam_role_arn = module.lambda_os_patch_iam_role.lambda_iam_role_arn
}

#Create Step-function State-machine
module "sf_state_machine" {
  source = "../modules/statemachine"
  create_ami_lambda_arn = module.lambda_functions.create_ami_lambda_arn
  verify_ami_lambda_arn = module.lambda_functions.verify_ami_lambda_arn
  delete_old_ami_lambda_arn = module.lambda_functions.delete_old_ami_lambda_arn
  start_os_patch_lambda_arn = module.lambda_functions. start_os_patch_lambda_arn
  verify_os_patch_lambda_arn = module.lambda_functions.verify_os_patch_lambda_arn
  send_patch_status_lambda_arn = module.lambda_functions.send_patch_status_lambda_arn 
}

#Create a S3 bucket for SSM service to fetch the patchbaseline
locals{
  s3_bucket_name = "os-patchbaseline-cf-dev"
}
module "s3_bucket_patchbaseline" {
  source = "../modules/s3_bucket"
  bucket_name = local.s3_bucket_name
  lambda_iam_role_arn = module.lambda_os_patch_iam_role.lambda_iam_role_arn
}



#Create SNS topic 
locals{
  sns_topic_name = "auto-os-patch-topic"
}

module "sns_topic" {
  source = "../modules/sns_topic"
  sns_topic_name = var.sns_topic_name
}

#Create cloudwatch rule to trigger state machine

locals{
  cw_rule_name = "Initiate-OS-Patch"
}
module "cloudwatch_rule" {
  source = "../modules/cloudwatch_rule"
  cw_rule_name = var.cloudwatch_rule_name
  os_patch_statemachine_arn = module.sf_state_machine.os_patch_statemachine_arn
}

#Outputs

output "creat-ami-lambda" {
  value = module.lambda_functions.create_ami_lambda_arn
}

output "verify-ami-lambda" {
  value = module.lambda_functions.verify_ami_lambda_arn
}

output "delete-ami-lambda" {
  value = module.lambda_functions.delete_old_ami_lambda_arn
}

output "start-os-patch-lambda" {
  value = module.lambda_functions.start_os_patch_lambda_arn
}

output "sverify-os-patch-lambda" {
  value = module.lambda_functions.verify_os_patch_lambda_arn
}

output "send_patch_status_lambda" {
  value = module.lambda_functions.send_patch_status_lambda_arn
}

output "s3_bucket_name" {
  value = var.s3_bucket_name
  description = "Use this bucket name in cloudwatch event JSON input"
}

output "sns_topic_arn" {
  value = module.sns_topic.sns_topic_arn
  description = "Use this SNS topic arn in cloudwatch event JSON input"
}