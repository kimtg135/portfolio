# 추후 module화 가능성을 염두해 hardcoding된 값이 아닌 변수로 관리
# 1. EKS-Cluster
resource "aws_eks_cluster" "eks_pr_cluster" {
  name     = "${var.project_name}-${var.region_name}-eks-cluster"
  role_arn = aws_iam_role.cluster.arn
  version  = var.eks_version
  vpc_config {
    subnet_ids = aws_subnet.private_app[*].id
    security_group_ids = [
      aws_security_group.eks_cluster_sg.id
    ]
    endpoint_private_access = true
    endpoint_public_access  = false
  }

  depends_on = [
    aws_iam_role_policy_attachment.cluster_AmazonEKSClusterPolicy,
    aws_iam_role_policy_attachment.cluster_vpc_resource_controller,
    aws_cloudwatch_log_group.eks
  ]

  access_config {
    authentication_mode = "API"
  }

  encryption_config {
    provider { key_arn = aws_kms_key.eks.arn }
    resources = ["secrets"]
  }
  enabled_cluster_log_types = var.eks_cluster_log_types

  tags = {
    Name = "${var.project_name}-${var.region_name}-eks-cluster"
  }
}

# 2. EKS cluster 접근권한 설정
resource "aws_eks_access_entry" "current_user" {
  cluster_name  = aws_eks_cluster.eks_pr_cluster.name
  principal_arn = data.aws_caller_identity.current.arn
  type          = "STANDARD"
  depends_on    = [aws_eks_cluster.eks_pr_cluster]
}

resource "aws_eks_access_policy_association" "current_user_policy" {
  cluster_name  = aws_eks_cluster.eks_pr_cluster.name
  principal_arn = aws_eks_access_entry.current_user.principal_arn
  policy_arn    = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy"

  access_scope {
    type = "cluster"
  }
}

resource "time_sleep" "wait_for_current_user_access" {
  depends_on = [aws_eks_access_policy_association.current_user_policy]

  create_duration = "30s"
}

resource "aws_eks_access_entry" "admin_access" {
  cluster_name  = aws_eks_cluster.eks_pr_cluster.name
  principal_arn = aws_iam_role.eks_admin.arn
  type          = "STANDARD"
  depends_on    = [aws_eks_cluster.eks_pr_cluster]
}

resource "aws_eks_access_policy_association" "admin_access_policy" {
  cluster_name  = aws_eks_cluster.eks_pr_cluster.name
  principal_arn = aws_eks_access_entry.admin_access.principal_arn
  policy_arn    = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy"

  access_scope {
    type = "cluster"
  }
  depends_on = [aws_eks_cluster.eks_pr_cluster]
}

# cloudwatch log group -> monitoring에서 사용하기 위함 
resource "aws_cloudwatch_log_group" "eks" {
  name              = "/aws/eks/${var.project_name}-${var.region_name}-eks-cluster/cluster"
  retention_in_days = 30
  tags              = { Name = "${var.project_name}-${var.region_name}-eks-cluster-logs" }
}
