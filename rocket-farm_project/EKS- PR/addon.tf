# EKS Addon 
# 1. addon 버전 조회 이후 data소스에 최신버전으로 저장
data "aws_eks_addon_version" "coredns" {
  addon_name         = var.eks_addon_coredns
  kubernetes_version = var.eks_version
  most_recent        = true
}

data "aws_eks_addon_version" "kube_proxy" {
  addon_name         = var.eks_addon_kube_proxy
  kubernetes_version = var.eks_version
  most_recent        = true
}

data "aws_eks_addon_version" "vpc_cni" {
  addon_name         = var.eks_addon_vpc_cni
  kubernetes_version = var.eks_version
  most_recent        = true
}

data "aws_eks_addon_version" "external_dns" {
  addon_name         = var.eks_addon_external_dns
  kubernetes_version = var.eks_version
  most_recent        = true
}

# 2. EKS 클러스터에 addon 추가
resource "aws_eks_addon" "coredns" {
  cluster_name                = aws_eks_cluster.eks_pr_cluster.name
  addon_name                  = var.eks_addon_coredns
  addon_version               = data.aws_eks_addon_version.coredns.version
  resolve_conflicts_on_create = var.eks_addon_resolve_conflicts
  resolve_conflicts_on_update = var.eks_addon_resolve_conflicts
  depends_on                  = [aws_eks_cluster.eks_pr_cluster]
}

resource "aws_eks_addon" "kube_proxy" {
  cluster_name                = aws_eks_cluster.eks_pr_cluster.name
  addon_name                  = var.eks_addon_kube_proxy
  addon_version               = data.aws_eks_addon_version.kube_proxy.version
  resolve_conflicts_on_create = var.eks_addon_resolve_conflicts
  resolve_conflicts_on_update = var.eks_addon_resolve_conflicts
  depends_on                  = [aws_eks_cluster.eks_pr_cluster]
}

resource "aws_eks_addon" "vpc_cni" {
  cluster_name                = aws_eks_cluster.eks_pr_cluster.name
  addon_name                  = var.eks_addon_vpc_cni
  addon_version               = data.aws_eks_addon_version.vpc_cni.version
  service_account_role_arn    = aws_iam_role.vpc_cni.arn
  resolve_conflicts_on_create = var.eks_addon_resolve_conflicts
  resolve_conflicts_on_update = var.eks_addon_resolve_conflicts
  depends_on                  = [aws_eks_cluster.eks_pr_cluster]
}

resource "aws_eks_addon" "external_dns" {
  cluster_name                = aws_eks_cluster.eks_pr_cluster.name
  addon_name                  = var.eks_addon_external_dns
  addon_version               = data.aws_eks_addon_version.external_dns.version
  service_account_role_arn    = aws_iam_role.external_dns.arn
  resolve_conflicts_on_create = var.eks_addon_resolve_conflicts
  resolve_conflicts_on_update = var.eks_addon_resolve_conflicts
  depends_on                  = [aws_eks_cluster.eks_pr_cluster]
}
