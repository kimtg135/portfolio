# === ST : 기본 변수 ===
variable "project_name" {
  description = "프로젝트 이름"
  type        = string
}

variable "region_name" {
  description = "AWS 리전"
  type        = string
}
# === EN : 기본 변수 ===
# === ST : EKS 클러스터 변수 ===
variable "eks_version" {
  description = "eks_cluster_version"
  type        = string
}

variable "eks_cluster_log_types" {
  description = "EKS 클러스터 로그 유형 목록"
  type        = list(string)
}
# === EN : EKS 클러스터 변수 ===
# === ST : Addon 변수 ===
variable "eks_addon_coredns" {
  description = "eks_addon(coredns)"
  type        = string
}

variable "eks_addon_kube_proxy" {
  description = "eks_addon(kube-proxy)"
  type        = string
}

variable "eks_addon_vpc_cni" {
  description = "eks_addon(vpc-cni)"
  type        = string
}

variable "eks_addon_external_dns" {
  description = "eks_addon(external-dns)"
  type        = string
}

variable "eks_addon_resolve_conflicts" {
  description = "eks_addon 충돌 해결 설정 (생성, 업데이트 설정을 따로 지정필요시 2개로 분리)"
  type        = string
}
# === EN : Addon 변수 ===
