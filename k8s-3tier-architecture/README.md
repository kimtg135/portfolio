# Kubernetes 3-Tier Shopping Mall

Kubernetes 기반 고가용성 3-Tier 쇼핑몰 인프라 프로젝트

> 사용자: 회원가입/로그인, 상품 검색/조회, 주문  
> 관리자: 상품 등록/삭제, 주문 상태 관리(확인/배송/취소)

## 아키텍처 개요

```
                    ┌──────────────────────────────────────────────────────┐
                    │                  Kubernetes Cluster                   │
                    │                                                      │
  Client ──────────┤  ┌──────────┐                                        │
  (Ingress)        │  │ MetalLB  │    ┌────────────────────────────────┐  │
                   │  │   L2     │    │   Namespace: database          │  │
  ┌──────────┐    │  └──────────┘    │                                │  │
  │  Nginx   │    │                   │  ┌────────┐                   │  │
  │ Frontend │────┤  ┌──────────┐    │  │ Master │ (node-0)          │  │
  │  :80     │    │  │ FastAPI  │    │  │ MySQL  │                   │  │
  └──────────┘    │  │ Shop API │    │  └───┬────┘                   │  │
       │          │  │  :8000   │────┤      │ GTID Replication       │  │
       │ /api/*   │  └──────────┘    │  ┌───┴────┐  ┌────────┐      │  │
       └──────────┤       │          │  │Slave-1 │  │Slave-2 │      │  │
                   │  ┌──────────┐    │  │(node-1)│  │(node-2)│      │  │
                   │  │  Redis   │    │  └────────┘  └────────┘      │  │
                   │  │ (Cache)  │    └────────────────────────────────┘  │
                   │  └──────────┘                                        │
  ┌──────────┐    │       │          ┌──────────┐                        │
  │ Grafana  │    │  ┌──────────┐    │ProxySQL  │                        │
  │Prometheus│────┤  │   NFS    │    │(R/W Split│                        │
  └──────────┘    │  │ Storage  │    │ x2 Pods) │                        │
                   │  └──────────┘    └──────────┘                        │
                    └──────────────────────────────────────────────────────┘

요청 흐름: Client → Nginx(:80) → /api/* → FastAPI(:8000) → ProxySQL → MySQL
                                            ↕ Redis (세션/캐시)
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
| **Frontend** | Nginx (Reverse Proxy + Static SPA) |
| **Backend** | FastAPI (REST API, JWT Auth) |
| **Cache** | Redis 7 (세션, 상품 캐시) |

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
├── 05-application/                    # 쇼핑몰 애플리케이션
│   ├── configmap-nginx.yaml           # nginx.conf (Reverse Proxy → FastAPI)
│   ├── configmap-fastapi.yaml         # 애플리케이션 환경 변수
│   ├── secret-nginx.yaml
│   ├── secret-fastapi.yaml            # DB 접속정보, JWT Secret
│   ├── nginx-deploy-svc.yaml          # Nginx Deployment + ClusterIP
│   ├── fastapi-deploy-svc.yaml        # FastAPI Deployment + ClusterIP
│   ├── redis-deploy-svc.yaml          # Redis Deployment + ClusterIP
│   ├── ingress-nginx.yaml             # www.1st-project.local
│   ├── ingress-fastapi.yaml           # api.1st-project.local
│   └── docker/                        # 커스텀 이미지 빌드
│       ├── fastapi/                   # Shop API
│       │   ├── Dockerfile
│       │   ├── main.py                # FastAPI 쇼핑몰 API (인증/상품/주문/관리자)
│       │   └── requirements.txt
│       └── nginx/                     # Frontend
│           ├── Dockerfile
│           └── html/
│               ├── index.html         # 메인 (상품 목록, 검색, 주문)
│               ├── orders.html        # 주문 내역
│               └── admin.html         # 관리자 대시보드
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

### 1. 3-Tier 쇼핑몰 아키텍처
- **Nginx** → 정적 파일(SPA) 제공 + `/api/*` 요청을 FastAPI로 리버스 프록시
- **FastAPI** → JWT 인증, 상품 CRUD, 주문 처리, Redis 캐싱
- **MySQL** → Master-Slave GTID 복제, ProxySQL R/W 분리

### 2. 쇼핑몰 API 엔드포인트

| Method | Endpoint | 설명 | 권한 |
|--------|----------|------|------|
| POST | `/api/auth/register` | 회원가입 | 공개 |
| POST | `/api/auth/login` | 로그인 (JWT 발급) | 공개 |
| GET | `/api/products` | 상품 목록 (검색, 페이징) | 공개 |
| GET | `/api/products/{id}` | 상품 상세 (Redis 캐시) | 공개 |
| POST | `/api/orders` | 주문 생성 (재고 차감) | 사용자 |
| GET | `/api/orders` | 내 주문 내역 | 사용자 |
| POST | `/api/admin/products` | 상품 등록 | 관리자 |
| PUT | `/api/admin/products/{id}` | 상품 수정 | 관리자 |
| DELETE | `/api/admin/products/{id}` | 상품 삭제 (soft delete) | 관리자 |
| GET | `/api/admin/orders` | 전체 주문 현황 | 관리자 |
| PATCH | `/api/admin/orders/{id}` | 주문 상태 변경 | 관리자 |

### 3. GTID 기반 MySQL 복제
- `gtid_mode=ON`으로 트랜잭션 기반 자동 포지셔닝
- Slave에서 `super_read_only=ON`으로 쓰기 방지
- initContainer에서 `CHANGE REPLICATION SOURCE TO ... SOURCE_AUTO_POSITION=1`로 자동 복제 설정

### 4. ProxySQL 읽기/쓰기 분리
- `^SELECT` 쿼리 → Slave 호스트그룹 (읽기 분산)
- `^INSERT|^UPDATE|^DELETE` → Master 호스트그룹
- `podAntiAffinity`로 ProxySQL Pod 분산 배치

### 5. NetworkPolicy 기반 보안
- Database: FastAPI 네임스페이스에서만 접근 허용 (Nginx는 직접 DB 접근 불가)
- Nginx → FastAPI → ProxySQL → MySQL 계층형 접근 제어
- 내부 Master-Slave 통신 및 ProxySQL 트래픽 허용

### 6. 자동 백업 및 보관
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
