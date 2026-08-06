#!/bin/sh
set -eu
awslocal s3api head-bucket --bucket frontierops-local 2>/dev/null || \
  awslocal s3api create-bucket --bucket frontierops-local
