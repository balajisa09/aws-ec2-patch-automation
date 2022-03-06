resource "aws_s3_bucket" "patchbaseline_bucket" {
  bucket = var.bucket_name
  acl    = "public-read"
  policy = <<EOF
    {
        "Version": "2008-10-17",
        "Statement": [
            {
                "Sid": "2",
                "Effect": "Allow",
                "Principal": {
                    "AWS": "${var.lambda_iam_role_arn}"
                },
                "Action": "s3:*",
                "Resource": "arn:aws:s3:::${var.bucket_name}/*"
            },
            {
                "Sid": "PublicReadGetObject",
                "Effect": "Allow",
                "Principal": "*",
                "Action": "s3:GetObject",
                "Resource": "arn:aws:s3:::${var.bucket_name}/*"
            }
        ]
    }

  EOF
  }
