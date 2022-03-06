data "archive_file" "create_ami_zip" {
  type        = "zip"
  for_each = toset(var.function_names)
  source_file = format("%s%s%s","python-lambdas/",each.key,".py")
  output_path = format("%s%s",each.key,".zip")
}

resource "aws_lambda_function" "lambda_functions" {
  for_each = toset(var.function_names)
  filename      = format("%s%s",each.key,".zip")
  function_name = each.key
  role          = var.lambda_iam_role_arn
  handler       = format("%s%s",each.key,".lambda_handler")
  source_code_hash = filebase64sha256(format("%s%s",each.key,".zip"))
  runtime          = "python3.6"
  timeout          = 30
}


output "create_ami_lambda_arn" {
  value = aws_lambda_function.lambda_functions["create-ami-ec2"].arn
}

output "verify_ami_lambda_arn" {
  value = aws_lambda_function.lambda_functions["verify-image-creation"].arn
}

output "delete_old_ami_lambda_arn" {
  value = aws_lambda_function.lambda_functions["delete-old-ami-ec2"].arn
}

output "start_os_patch_lambda_arn" {
  value = aws_lambda_function.lambda_functions["start-os-patch"].arn
}

output "verify_os_patch_lambda_arn" {
  value = aws_lambda_function.lambda_functions["verify-os-patch"].arn
}

output "send_patch_status_lambda_arn" {
  value = aws_lambda_function.lambda_functions["send-patch-status-mail"].arn
}