# === ST: 기본 변수 ===
project_name = "rocket-farm"
region_name  = "pr"

# === EN: 기본 변수 ===
# === ST: EKS 클러스터 변수 ===
eks_version = "1.35"

eks_cluster_log_types = [
  "api",
  "audit",
  "authenticator",
  "controllerManager",
  "scheduler"
]
# === EN: EKS 클러스터 변수 ===
# === ST: Addon 변수 ===
eks_addon_coredns           = "coredns"
eks_addon_kube_proxy        = "kube-proxy"
eks_addon_vpc_cni           = "vpc-cni"
eks_addon_external_dns      = "external-dns"
eks_addon_resolve_conflicts = "OVERWRITE"
# === EN: Addon 변수 ===
