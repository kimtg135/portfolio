# Rocket-Farm Project

## 프로젝트 개요
- **기간**: 2026.02.25~2026.04.30
- **인원**: 총 5명
- **역할**: EKS, Auto scale(karpenter+hpa), DB
- **한 줄 요약**: 쇼핑몰 글로벌 DR 시나리오, 각 상황별 다른 DR level

## 아키텍처
<!-- 아키텍처 다이어그램 이미지를 images/ 폴더에 넣고 아래 경로 수정 -->
![architecture](./images/architecture.png)

## 기술 스택
| 분류 | 기술 |
|------|------|
| IaC | Terraform |
| Container Orchestration | AWS EKS |
| Auto Scaling | Karpenter, HPA |
| CI/CD | ArgoCD |
| 보안 | KMS, Private Subnet |
| 모니터링 | |

## 디렉토리 구조
```
1.rocket-farm_project/
├── EKS/           # EKS 클러스터 생성 Terraform 코드
├── Karpenter/     # Karpenter 배포 Helm chart
├── HPA/           # HPA 적용 Helm chart
├── DB/            # DB 생성 Terraform 코드
└── README.md
```

## 주요 설계 결정

### 1. EKS Private Endpoint Only
- **이유**: 
- **효과**: 

### 2. KMS etcd 암호화
- **이유**: 
- **효과**: 

### 3. Karpenter 도입
- **이유**: 
- **효과**: 

### 4. HPA 적용
- **이유**: 
- **효과**: 

## 트러블슈팅

### 이슈 1: 
- **상황**: 
- **원인**: 
- **해결**: 

### 이슈 2: 
- **상황**: 
- **원인**: 
- **해결**: 

## 개선하고 싶은 점
- 