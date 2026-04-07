# 배포 단계별 상세 가이드

## 사전 준비

```bash
# 1. 대상 노드 라벨 설정
kubectl label nodes node-0 kubernetes.io/hostname=node-0
kubectl label nodes node-1 kubernetes.io/hostname=node-1
kubectl label nodes node-2 kubernetes.io/hostname=node-2

# 2. NFS 저장소 준비
sudo mkdir -p /nfs/{database-1,database-2,wordpress,fastapi,backup}
sudo chmod 777 /nfs/*

# 3. NFS 내보내기 설정 (/etc/exports)
/nfs *(rw,sync,no_subtree_check,no_root_squash)
sudo exportfs -ra
```

---

## 1단계: 네임스페이스 생성

```bash
kubectl apply -f kubernetes/namespace/namespace-all.yaml
kubectl get namespaces
```

## 2단계: ConfigMap 및 Secret 생성

```bash
kubectl apply -f kubernetes/configmap/
kubectl apply -f kubernetes/secret/

# 검증
kubectl get configmap -n database
kubectl get secret -n database
```

## 3단계: 저장소 생성 (PV/PVC)

```bash
kubectl apply -f kubernetes/storage/

# 검증
kubectl get pv
kubectl get pvc -n database
kubectl get pvc -n fastapi
kubectl get pvc -n wordpress
```

## 4단계: MetalLB 설정

```bash
kubectl apply -f kubernetes/metallb/metallb.yaml
```

## 5단계: MySQL Master-Slave 배포

```bash
# Master 먼저 배포 (순서 중요!)
kubectl apply -f kubernetes/statefulset/mysql-master.yaml
kubectl wait --for=condition=ready pod -l app=mysql-master -n database --timeout=300s

# Slave 배포
kubectl apply -f kubernetes/statefulset/mysql-slave-1.yaml
sleep 30
kubectl apply -f kubernetes/statefulset/mysql-slave-2.yaml

# Pod 상태 확인
kubectl get pods -n database -w
```

## 6단계: ProxySQL 배포

```bash
kubectl apply -f kubernetes/proxysql/proxysql-deploy-svc.yaml
kubectl wait --for=condition=ready pod -l app=proxysql -n database --timeout=300s
```

## 7단계: 보안 정책 적용

```bash
kubectl apply -f kubernetes/security/network-policy.yaml
```

## 8단계: 모니터링 배포

```bash
kubectl apply -f kubernetes/monitoring/
```

## 9단계: Ingress 배포

```bash
kubectl apply -f kubernetes/ingress/
```

## 10단계: 백업 설정

```bash
kubectl apply -f kubernetes/backup/backup-cronjob.yaml
```

---

## 배포 완료 검증

```bash
# 모든 Pod 상태 확인
kubectl get pods -A

# 모든 Service 확인
kubectl get svc -A

# MySQL 복제 상태 확인
kubectl exec -it -n database mysql-master-0 -- \
  mysql -u root -p -e "SHOW MASTER STATUS\G"

kubectl exec -it -n database mysql-slave-1-0 -- \
  mysql -u root -p -e "SHOW REPLICA STATUS\G"
```

---

## 주요 접근 명령어

### MySQL 직접 접근
```bash
# Master
kubectl exec -it -n database mysql-master-0 -- mysql -u root -p

# ProxySQL 경유
kubectl port-forward -n database svc/proxysql-mysql-svc 3306:3306
mysql -h 127.0.0.1 -u proxysql -pproxysql_pass
```

### 로그 확인
```bash
kubectl logs -f -n database mysql-master-0 -c mysql
kubectl logs -f -n database deploy/proxysql -c proxysql
```

---

## 트러블슈팅

### Pod가 Pending 상태
```bash
kubectl describe pod <pod-name> -n database
# → PVC 바인딩, 노드 라벨, 리소스 부족 확인
```

### MySQL 복제 실패
```bash
kubectl exec -it -n database mysql-master-0 -- \
  mysql -u root -p -e "SHOW MASTER STATUS;"

kubectl exec -it -n database mysql-slave-1-0 -- \
  mysql -u root -p -e "SHOW REPLICA STATUS\G"
# → Seconds_Behind_Source, Last_Error 확인
```

---

## 보안 체크리스트

- [ ] Secret 비밀번호 변경 (기본 테스트 비밀번호 교체)
- [ ] NetworkPolicy 적용 확인
- [ ] RBAC 권한 최소화
- [ ] 정기적 백업 복구 테스트
- [ ] 로그 모니터링 설정
