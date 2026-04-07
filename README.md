# Portfolio

## 소개
DevOps/인프라 엔지니어 포트폴리오입니다.

## 프로젝트 목록

| # | 프로젝트 | 설명 | 주요 기술 |
|---|---------|------|-----------|
| 1 | [k8s-3tier-architecture](./k8s-3tier-architecture) | 고가용성 Kubernetes 3-Tier 인프라 구축 | K8s, MySQL HA, ProxySQL, MetalLB, Prometheus |
| 2 | [rocket-farm_project](./rocket-farm_project) | AWS EKS 기반 컨테이너 인프라 구축 | Terraform, EKS, Karpenter, HPA |

## 전체 구조

```
portfolio/
├── k8s-3tier-architecture/          # 고가용성 K8s 3-Tier 인프라
│   ├── dns/                         # BIND9 DNS 설정
│   ├── docker/                      # Docker 이미지 빌드
│   ├── docs/                        # 분석 보고서, 배포 가이드
│   └── kubernetes/                  # K8s 매니페스트
│       ├── 00-namespace/
│       ├── 01-network/              # MetalLB, NetworkPolicy
│       ├── 02-storage/              # PV/PVC (NFS)
│       ├── 03-database/             # MySQL Master-Slave (GTID)
│       ├── 04-proxysql/             # R/W 분리
│       ├── 05-application/          # Nginx, FastAPI
│       ├── 06-monitoring/           # Prometheus, Grafana
│       └── 07-backup/               # CronJob 백업
│
└── rocket-farm_project/             # AWS EKS 인프라
    ├── EKS- PR/                     # EKS 클러스터 Terraform
    ├── DB/                          # 데이터베이스 설정
    ├── Karpenter/                   # Karpenter 오토스케일링
    ├── HPA/                         # Horizontal Pod Autoscaler
    └── architecture/                # 아키텍처 문서
```
