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
k8s-3tier-architecture/
├── 00-namespace/                      # 네임스페이스 정의
│   └── namespace-all.yaml             # database, fastapi, nginx, monitoring
├── 01-network/                        # 네트워크 인프라
│   ├── metallb.yaml                   # MetalLB L2 로드밸런서
│   ├── network-policy.yaml            # 네임스페이스 간 접근 제어
│   └── dns/                           # BIND9 DNS 설정
│       ├── db.1st-project.local       # 존 파일 (A 레코드)
│       ├── named.conf.local           # 존 정의
│       └── named.conf.options         # DNS 옵션 및 포워더
├── 02-storage/                        # PersistentVolume & Claim (NFS)
│   ├── pv-database-1.yaml
│   ├── pv-database-2.yaml
│   ├── pv-nginx.yaml
│   ├── pv-fastapi.yaml
│   ├── pv-backup.yaml
│   └── pvc-*.yaml                     # 각 PV에 대응하는 PVC
├── 03-database/                       # MySQL Master-Slave (GTID)
│   ├── configmap-master.yaml          # Master my.cnf
│   ├── configmap-slave-1.yaml         # Slave-1 설정 + 복제 템플릿
│   ├── configmap-slave-2.yaml         # Slave-2 설정 + 복제 템플릿
│   ├── configmap-init-scripts.yaml    # DB/사용자 초기화 SQL
│   ├── secret-database.yaml           # DB 인증 정보
│   ├── mysql-master.yaml              # Master StatefulSet (node-0)
│   ├── mysql-slave-1.yaml             # Slave-1 StatefulSet (node-1)
│   ├── mysql-slave-2.yaml             # Slave-2 StatefulSet (node-2)
│   └── docker/                        # MySQL 커스텀 이미지 빌드
│       ├── Dockerfile
│       ├── docker-compose.yaml        # 로컬 개발용 MySQL + Redis
│       ├── my.cnf
│       └── init.d/
│           └── user-setup.sql
├── 04-proxysql/                       # ProxySQL R/W 분리
│   ├── configmap-proxysql.yaml        # 호스트그룹 + 쿼리 라우팅 설정
│   └── proxysql-deploy-svc.yaml       # Deployment + Service (x2 Pods)
├── 05-application/                    # Nginx, FastAPI
│   ├── secret-nginx.yaml
│   ├── secret-fastapi.yaml
│   ├── ingress-nginx.yaml             # www.1st-project.local
│   └── ingress-fastapi.yaml           # api.1st-project.local
├── 06-monitoring/                     # Prometheus + Grafana
│   ├── prometheus-deploy.yaml         # Prometheus + RBAC + ConfigMap
│   ├── grafana-deploy.yaml            # Grafana + Datasource 자동 설정
│   └── ingress-monitoring.yaml        # monitoring.1st-project.local
├── 07-backup/                         # 자동 백업
│   └── backup-cronjob.yaml            # 매일 02:00 mysqldump, 7일 보관
├── docs/                              # 문서
│   ├── analysis-report.md             # 인프라 분석 보고서
│   └── deployment-guide.md            # 배포 가이드
└── README.md
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
kubectl apply -f 00-namespace/

# 2. 네트워크 (MetalLB + NetworkPolicy)
kubectl apply -f 01-network/metallb.yaml
kubectl apply -f 01-network/network-policy.yaml

# 3. 스토리지 (PV → PVC)
kubectl apply -f 02-storage/

# 4. MySQL Master (먼저 배포 후 Ready 대기)
kubectl apply -f 03-database/configmap-master.yaml
kubectl apply -f 03-database/configmap-init-scripts.yaml
kubectl apply -f 03-database/secret-database.yaml
kubectl apply -f 03-database/mysql-master.yaml
kubectl wait --for=condition=ready pod -l app=mysql-master -n database --timeout=300s

# 5. MySQL Slaves
kubectl apply -f 03-database/configmap-slave-1.yaml
kubectl apply -f 03-database/configmap-slave-2.yaml
kubectl apply -f 03-database/mysql-slave-1.yaml
kubectl apply -f 03-database/mysql-slave-2.yaml

# 6. ProxySQL
kubectl apply -f 04-proxysql/

# 7. Application (Nginx + FastAPI)
kubectl apply -f 05-application/

# 8. 모니터링
kubectl apply -f 06-monitoring/

# 9. 백업 CronJob
kubectl apply -f 07-backup/
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
