
resource "aws_iam_policy" "statemachine_os_patch_policy" {
  name        = "statemachine_os_patch_policy"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "lambda:InvokeFunction",
        ]
        Effect   = "Allow"
        Resource = [
                "${var.create_ami_lambda_arn}:*",
                "${var.verify_ami_lambda_arn}:*",
                "${var.delete_old_ami_lambda_arn}:*",
                "${var.start_os_patch_lambda_arn}:*",
                "${var.verify_os_patch_lambda_arn}:*",
                "${var.send_patch_status_lambda_arn}:*"
            ]
      },
    ]
  })
  
}

#Create IAM role and attach policy
resource "aws_iam_role" "statemachine_os_patch_role"{
  name = "statemachine_os_patch_role"
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
    managed_policy_arns = [aws_iam_policy.statemachine_os_patch_policy.arn]

}

resource "aws_sfn_state_machine" "os_patch_state_machine" {
  name     = "os_patch_state_machine"
  role_arn = aws_iam_role.statemachine_os_patch_role.arn

  definition = <<EOF
{
  "StartAt": "Create AMI",
  "States": {
    "Create AMI": {
      "Type": "Task",
      "Resource": "${var.create_ami_lambda_arn}",
      "Next": "Verify image creation"
    },
    "Verify image creation": {
      "Type": "Task",
      "Resource": "${var.verify_ami_lambda_arn}",
      "InputPath": "$",
      "OutputPath": "$",
      "Next": "Is all images created"
    },
    "Is all images created": {
      "Type": "Choice",
      "Choices": [
        {
          "Variable": "$.status",
          "StringEquals": "success",
          "Next": "Delete Old Windows AMIs"
        },
        {
          "And": [
            {
              "Variable": "$.status",
              "StringEquals": "pending"
            },
            {
              "Variable": "$.ami_creation_attempts",
              "NumericGreaterThanPath": "$.max_attempts"
            }
          ],
          "Next": "Delete Old Windows AMIs"
        },
        {
          "And": [
            {
              "Variable": "$.status",
              "StringEquals": "pending"
            },
            {
              "Variable": "$.ami_creation_attempts",
              "NumericLessThanEqualsPath": "$.max_attempts"
            }
          ],
          "Next": "Retry-verify-image-creation"
        }
      ]
    },
    "Retry-verify-image-creation": {
      "Type": "Wait",
      "SecondsPath": "$.ami_verification_interval",
      "Next": "Verify image creation"
    },
    "Delete Old Windows AMIs": {
      "Type": "Task",
      "Resource": "${var.delete_old_ami_lambda_arn}",
      "InputPath": "$",
      "OutputPath": "$",
      "Next": "Start OS patch"
    },
    "Start OS patch": {
      "Type": "Task",
      "Resource": "${var.start_os_patch_lambda_arn}",
      "InputPath": "$",
      "OutputPath": "$",
      "Next": "Verify OS patch"
    },
    "Verify OS patch": {
      "Type": "Task",
      "Resource": "${var.verify_os_patch_lambda_arn}",
      "InputPath": "$",
      "OutputPath": "$",
      "Next": "Is all instances patched"
    },
    "Is all instances patched": {
      "Type": "Choice",
      "Choices": [
        {
          "Variable": "$.status",
          "StringEquals": "success",
          "Next": "send email"
        },
        {
          "And": [
            {
              "Variable": "$.status",
              "StringEquals": "pending"
            },
            {
              "Variable": "$.os_patch_attempts",
              "NumericGreaterThanPath": "$.max_attempts"
            }
          ],
          "Next": "send email"
        },
        {
          "And": [
            {
              "Variable": "$.status",
              "StringEquals": "pending"
            },
            {
              "Variable": "$.os_patch_attempts",
              "NumericLessThanEqualsPath": "$.max_attempts"
            }
          ],
          "Next": "Retry-verify-os-patch"
        }
      ]
    },
    "Retry-verify-os-patch": {
      "Type": "Wait",
      "SecondsPath": "$.patch_verification_interval",
      "Next": "Verify OS patch"
    },
    "send email": {
      "Type": "Task",
      "Resource": "${var.send_patch_status_lambda_arn}",
      "InputPath": "$",
      "OutputPath": "$",
      "End": true
    }
  }
}

EOF
}

output "os_patch_statemachine_arn" {
  value = aws_sfn_state_machine.os_patch_state_machine.arn
}