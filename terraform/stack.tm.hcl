stack {
  name        = "gracii-v0.1b" 
  description = "State-of-the-art multi-agent for enterprise."
  id          = "6f9eb473-9176-481f-9f86-3a99278e229e"
  tags        = [
    "eks-bot",
  ]
}

globals {
  project_name = "gracii"
  aws_region   = "us-east-1"
  assume_iam_role = "arn:aws:iam::130506138320:role/genai-ops-service-role-cicd"
  bedrock_common_iam_role = "arn:aws:iam::130506138320:role/bedrock-knowledge-base-role"
}