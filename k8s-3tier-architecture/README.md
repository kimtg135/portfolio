# Kubernetes MySQL HA Infrastructure

고가용성 MySQL Master-Slave 복제 구조 기반의 Kubernetes 인프라 프로젝트

## 아키텍처 개요

```
                    ┌─────────────────────────────────────────────────┐
                    │              Kubernetes Cluster                  │
                    │                                                  │
  Client ──────────┤  ┌──────────┐    ┌──────────────────────────┐   │
  (Ingress)        │  │ MetalLB  │    │   Namespace: database    │   │
                   │  │   L2     │    │                          │   │
  ┌─────────┐     │  └──────────┘    │  ┌────────┐             │   │
  │  Nginx  │─────┤                   │  │ Master │ (node-0)    │   │
  │  :80    │     │  ┌──────────┐    │  │ MySQL  │             │   │
  └─────────┘     │  │ProxySQL  │────┤  └───┬────┘             │   │
                   │  │(R/W Split│    │      │ GTID Replication  │   │
  ┌─────────┐     │  │ x2 Pods) │    │  ┌───┴────┐ ┌────────┐ │   │
  │ FastAPI │─────┤  └──────────┘    │  │Slave-1 │ │Slave-2 │ │   │
  │ :8000   │     │                   │  │(node-1)│ │(node-2)│ │   │
  └─────────┘     │                   │  └────────┘ └────────┘ │   │
                   │                   └──────────────────────────┘   │
  ┌─────────┐     │                                                  │
  │Grafana  │     │  ┌──────────────────────────────────┐           │
  │Promethe │─────┤  │  NFS Storage (172.100.100.20)    │           │
  └─────────┘     │  │  /nfs/database-1, database-2     │           │
                   │  │  /nfs/nginx, fastapi, backup     │           │
                   │  └──────────────────────────────────┘           │
                    └─────────────────────────────────────────────────┘
```

## 기술 스택

| 구분 | 기술 |
|------|------|
| **Container Orchestration** | Kubernetes (StatefulSet, Deployment, CronJob) |
| **Database** | MySQL 8.0 (Master-Slave GTID Replication) |
| **Proxy** | ProxySQL 2.6.3 (읽기/쓰기 분리) |
| **Load Balancer** | MetalLB (L2 Mode) |
| **Storage** | NFS + PV/PVC (Retain Policy) |
| **Monitoring** | Prometheus + Grafana |
| **DNS** | BIND9 |
| **Backup** | CronJob + mysqldump (일 1회, 7일 보관) |
| **Security** | NetworkPolicy, Kubernetes Secret |
| **Web** | Nginx, FastAPI |

## 프로젝트 구조

```
├── docs/                          # 문서
│   └── analysis-report.md         # 인프라 분석 보고서 (발견 문제점 및 해결)
├── docker/                        # Docker 이미지 빌드
│   ├── Dockerfile                 # MySQL 커스텀 이미지
│   ├── docker-compose.yaml        # 로컬 개발용 MySQL + Redis
│   ├── my.cnf                     # MySQL Master 설정
│   └── init.d/
│       └── user-setup.sql         # 초기 DB/사용자 생성 SQL
├── dns/                           # DNS 설정 (BIND9)
│   ├── db.1st-project.local       # 존 파일 (A 레코드)
│   ├── named.conf.local           # 존 정의
│   └── named.conf.options         # DNS 옵션 및 포워더
└── kubernetes/                    # Kubernetes 매니페스트
    ├── metallb/                   # MetalLB 로드밸런서 설정
    │   └── metallb.yaml
    ├── namespace/                 # 네임스페이스 정의
    │   └── namespace-all.yaml     # database, fastapi, nginx, monitoring
    ├── configmap/                 # ConfigMap
    │   ├── configmap-master.yaml  # MySQL Master 설정
    │   ├── configmap-slave-1.yaml # Slave-1 설정 + 복제 템플릿
    │   ├── configmap-slave-2.yaml # Slave-2 설정 + 복제 템플릿
    │   ├── configmap-init-scripts.yaml  # DB 초기화 SQL
    │   └── configmap-proxysql.yaml      # ProxySQL R/W 분리 설정
    ├── secret/                    # Secret (운영 시 sealed-secrets 권장)
    │   ├── secret-database.yaml
    │   ├── secret-fastapi.yaml
    │   └── secret-nginx.yaml
    ├── storage/                   # PersistentVolume & Claim
    │   ├── pv-database-1.yaml
    │   ├── pv-database-2.yaml
    │   ├── pv-nginx.yaml
    │   ├── pv-fastapi.yaml
    │   ├── pv-backup.yaml
    │   ├── pvc-database-1.yaml
    │   ├── pvc-database-2.yaml
    │   ├── pvc-fastapi.yaml
    │   ├── pvc-nginx.yaml
    │   └── pvc-backup.yaml
    ├── statefulset/               # MySQL StatefulSet (Master + Slave x2)
    │   ├── mysql-master.yaml      # Master (node-0)
    │   ├── mysql-slave-1.yaml     # Slave-1 (node-1) + initContainer 복제 설정
    │   └── mysql-slave-2.yaml     # Slave-2 (node-2) + initContainer 복제 설정
    ├── proxysql/                  # ProxySQL Deployment + Service
    │   └── proxysql-deploy-svc.yaml
    ├── ingress/                   # Ingress 규칙
    │   ├── ingress-fastapi.yaml
    │   ├── ingress-monitoring.yaml
    │   └── ingress-nginx.yaml
    ├── monitoring/                # 모니터링 스택
    │   ├── prometheus-deploy.yaml # Prometheus + RBAC + ConfigMap
    │   └── grafana-deploy.yaml    # Grafana + Datasource 자동 설정
    ├── backup/                    # 백업
    │   └── backup-cronjob.yaml    # 일일 02:00 mysqldump, 7일 보관
    └── security/                  # 보안 정책
        └── network-policy.yaml    # 네임스페이스 간 접근 제어
```

## 배포 가이드

### 사전 준비

```bash
# 1. 노드 라벨 설정
kubectl label nodes node-0 kubernetes.io/hostname=node-0
kubectl label nodes node-1 kubernetes.io/hostname=node-1
kubectl label nodes node-2 kubernetes.io/hostname=node-2

# 2. NFS 저장소 준비
sudo mkdir -p /nfs/{database-1,database-2,nginx,fastapi,backup}
sudo chmod 777 /nfs/*

# 3. NFS 내보내기 설정 (/etc/exports)
/nfs *(rw,sync,no_subtree_check,no_root_squash)
sudo exportfs -ra
```

### 배포 순서

```bash
# 1. 네임스페이스
kubectl apply -f kubernetes/namespace/

# 2. ConfigMap & Secret
kubectl apply -f kubernetes/configmap/
kubectl apply -f kubernetes/secret/

# 3. 스토리지 (PV → PVC)
kubectl apply -f kubernetes/storage/

# 4. MetalLB
kubectl apply -f kubernetes/metallb/

# 5. MySQL Master (먼저 배포 후 Ready 대기)
kubectl apply -f kubernetes/statefulset/mysql-master.yaml
kubectl wait --for=condition=ready pod -l app=mysql-master -n database --timeout=300s

# 6. MySQL Slaves
kubectl apply -f kubernetes/statefulset/mysql-slave-1.yaml
kubectl apply -f kubernetes/statefulset/mysql-slave-2.yaml

# 7. ProxySQL
kubectl apply -f kubernetes/proxysql/

# 8. 보안 정책
kubectl apply -f kubernetes/security/

# 9. 모니터링
kubectl apply -f kubernetes/monitoring/

# 10. Ingress
kubectl apply -f kubernetes/ingress/

# 11. 백업 CronJob
kubectl apply -f kubernetes/backup/
```

### 배포 검증

```bash
# 전체 Pod 상태
kubectl get pods -A

# MySQL 복제 상태 확인
kubectl exec -it -n database mysql-master-0 -- \
  mysql -u root -p -e "SHOW MASTER STATUS\G"

kubectl exec -it -n database mysql-slave-1-0 -- \
  mysql -u root -p -e "SHOW REPLICA STATUS\G"

# ProxySQL 연결 테스트
kubectl exec -it -n database deploy/proxysql -- \
  mysql -h 127.0.0.1 -P 6033 -u proxysql -pproxysql_pass -e "SELECT 1"
```

## 핵심 설계 포인트

### 1. GTID 기반 MySQL 복제
- `gtid_mode=ON`으로 트랜잭션 기반 자동 포지셔닝
- Slave에서 `super_read_only=ON`으로 쓰기 방지
- initContainer에서 `CHANGE REPLICATION SOURCE TO ... SOURCE_AUTO_POSITION=1`로 자동 복제 설정

### 2. ProxySQL 읽기/쓰기 분리
- `^SELECT` 쿼리 → Slave 호스트그룹 (읽기 분산)
- `^INSERT|^UPDATE|^DELETE` → Master 호스트그룹
- `podAntiAffinity`로 ProxySQL Pod 분산 배치

### 3. NetworkPolicy 기반 보안
- Database: Nginx, FastAPI, Monitoring 네임스페이스에서만 접근 허용
- 내부 Master-Slave 통신 및 ProxySQL 트래픽 허용

### 4. 자동 백업 및 보관
- CronJob으로 매일 02:00 Master DB 전체 백업
- `--single-transaction`으로 Hot Backup
- 7일 이상 오래된 백업 자동 삭제

## 개선 가능 영역

| 영역 | 현재 | 개선안 |
|------|------|--------|
| **고가용성** | Master 단일 Pod | InnoDB Cluster / Failover 자동화 |
| **Secret 관리** | Kubernetes Secret | Sealed Secrets / External Secrets |
| **배포 자동화** | 수동 kubectl apply | Helm Chart + ArgoCD GitOps |
| **모니터링** | 기본 Pod 메트릭 | MySQL Exporter + 커스텀 대시보드 |
| **로그 관리** | 컨테이너 내부 | EFK Stack (Elasticsearch + Fluentd + Kibana) |
| **백업** | Master에서 실행 | Slave에서 실행 (Master 부하 감소) |

## 네트워크 구성

| 호스트 | IP | 역할 |
|--------|----|------|
| dns | 172.100.100.40 | BIND9 DNS 서버 |
| db | 172.100.100.30 | 데이터베이스 서버 |
| nfs | 172.100.100.20 | NFS 스토리지 서버 |
| www | 172.100.100.100 | 웹 서비스 (MetalLB VIP) |
| proxysql-lb | 172.100.100.101 | ProxySQL LoadBalancer |

---

> **참고**: Secret 파일에 포함된 비밀번호는 학습/테스트 목적입니다. 실제 운영 환경에서는 반드시 변경하고 sealed-secrets 또는 외부 시크릿 관리자를 사용하세요.
