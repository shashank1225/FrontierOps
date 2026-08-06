resource "aws_ecr_repository" "api" {
  name                 = "${local.name}-api"
  image_tag_mutability = "IMMUTABLE"
  image_scanning_configuration {
    scan_on_push = true
  }
  encryption_configuration {
    encryption_type = "AES256"
  }
}
resource "aws_ecr_lifecycle_policy" "api" {
  repository = aws_ecr_repository.api.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1, description = "Retain 30 images", selection = {
        tagStatus = "any", countType = "imageCountMoreThan", countNumber = 30
        }, action = {
        type = "expire"
      }
    }]
  })
}
