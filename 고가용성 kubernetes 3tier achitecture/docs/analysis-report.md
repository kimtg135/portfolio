# 1차 프로젝트 산출물 분석 보고서

## 분석 대상
- Docker 기반 MySQL 이미지 빌드 (Dockerfile, docker-compose)
- Kubernetes 클러스터 설정 (MetalLB, DNS)
- Kubernetes 매니페스트 (StatefulSet, ConfigMap, Secret, PV/PVC 등)

---

## 발견된 주요 문제점 및 해결

### 1. IP 주소 하드코딩 (심각)
- **문제**: ConfigMap에서 `master-host=172.100.100.30` 고정 → K8s 내부에서 접근 불가
- **해결**: Kubernetes DNS 사용 `mysql-master-svc.database.svc.cluster.local`

### 2. 비밀번호 보안 (심각)
- **문제**: ConfigMap에 비밀번호 평문 노출 (`Repl_Secure_Pass_456`)
- **해결**: Secret의 `secretKeyRef`로 참조, 운영 환경에서는 sealed-secrets 권장

### 3. 복제 설정 오류
- **문제**: MySQL 8.0에서 deprecated된 `master-host`, `master-user` 옵션 사용
- **해결**: `CHANGE REPLICATION SOURCE TO` 구문으로 initContainer 통해 설정

### 4. Master ConfigMap 누락
- **문제**: Master StatefulSet이 `configmap-master`를 참조하지만 파일 없음
- **해결**: `configmap-master.yaml` 생성

### 5. Health Check 불일치
- **문제**: Master에만 Health Check 없음
- **해결**: Master/Slave 모두 livenessProbe, readinessProbe 통일

### 6. PVC 이름 오타
- **문제**: `faastapi-pvc` (a가 하나 더 많음)
- **해결**: `fastapi-pvc`로 수정

### 7. PVC 용량 불일치
- **문제**: `database-pvc-2`가 10Gi인데 PV는 15Gi
- **해결**: PVC를 15Gi로 통일

### 8. NetworkPolicy 불완전
- **문제**: monitoring 네임스페이스에서 DB 접근 불가, DB 내부 통신 규칙 없음
- **해결**: monitoring + database 내부 통신 규칙 추가

### 9. 사용자 생성 SQL 불일치
- **문제**: `CREATE USER 'slave1234'` 후 `GRANT ... TO 'slave'` (사용자명 불일치)
- **해결**: `slave`로 통일

### 10. Ingress deprecated annotation
- **문제**: `kubernetes.io/ingress.class` annotation 사용 (deprecated)
- **해결**: `ingressClassName: nginx` 필드로 변경

---

## 추가 개선 권장사항
- Helm Chart 또는 Kustomize로 환경별 설정 분리
- GitOps (ArgoCD) 도입으로 배포 자동화
- MySQL Exporter 추가로 상세 메트릭 수집
- Master 고가용성 (InnoDB Cluster 또는 Failover 자동화)
