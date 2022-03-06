#Create IAM policy for the cloudwatch rule to trigger state machine
resource "aws_iam_policy" "cw_os_patch_policy" {
  name        = "cw_os_patch_policy"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "states:StartExecution",
        ]
        Effect   = "Allow"
        Resource = ["${var.os_patch_statemachine_arn}"]
      },
    ]
  })
  
}

#Create IAM role and attach policy
resource "aws_iam_role" "cw_os_patch_role"{
  name = "cw_os_patch_role"
  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": "sts:AssumeRole",
      "Principal": {
        "Service": "events.amazonaws.com"
      },
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
EOF
    managed_policy_arns = [aws_iam_policy.cw_os_patch_policy.arn]

}

resource "aws_cloudwatch_event_rule" "cw_os_patch_rule"{
    name = var.cw_rule_name
    description = "Initiates the Automated OS patch Process"
    schedule_expression = "rate(60 minutes)"
    is_enabled = false
}

#Create cloudwatch event rule target
resource "aws_cloudwatch_event_target" "cw_rule_target"{
    rule = aws_cloudwatch_event_rule.cw_os_patch_rule.name
    arn = var.os_patch_statemachine_arn
    role_arn = aws_iam_role.cw_os_patch_role.arn
}