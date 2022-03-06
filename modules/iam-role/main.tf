#Create IAM Policy
resource "aws_iam_policy" "lambda_os_patch_policy" {
  name        = "lambda_os_patch_policy"
  policy = file("${path.module}/os-patch-policy.json")
}

#Create IAM role and attach policy
resource "aws_iam_role" "lambda_os_patch_role"{
  name = "os_patch_role_terraform"
  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
EOF
    managed_policy_arns = [aws_iam_policy.lambda_os_patch_policy.arn]

}

output "lambda_iam_role_arn" {
  value = aws_iam_role.lambda_os_patch_role.arn
}