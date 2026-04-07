# 성능 테스트 도구 선택 사유서

## 1. 개요

rocket-farm 프로젝트의 성능 테스트 도구로 **Grafana k6**를 선택하고, **EKS 클러스터 외부 EC2에서 실행**하며, **k6 OSS + Grafana Cloud 무료 플랜 조합**으로 운영한다.

본 문서는 JMeter, Locust와의 비교 분석을 통해 선택 근거를 기술한다.

---

## 2. rocket-farm 인프라 현황

| 구성 요소 | 상세 |
|---|---|
| **클라우드** | AWS (Seoul Primary / Tokyo DR) |
| **컴퓨팅** | EKS + Karpenter 노드 자동 스케일링 (t3.small) |
| **서비스** | 6개 마이크로서비스 (api-gateway, auth, product, order, inventory, payment) |
| **배포** | ArgoCD GitOps + Argo Rollouts Blue/Green |
| **CI/CD** | GitHub Actions (Terraform plan/apply, Helm lint, diff) |
| **모니터링** | kube-prometheus-stack (Prometheus + Grafana + AlertManager) + Loki |
| **네트워크** | ALB + WAF + ExternalDNS + Route53 |
| **알림** | ArgoCD Notifications → Slack |

---

## 3. 도구 비교 — 확장성 · 편의성 · 비용

### 3.1 확장성

k6는 Go 엔진 기반으로 동일 리소스 대비 JMeter(JVM Thread 모델)보다 약 25배, Locust(gevent 코루틴)보다 약 10배 높은 가상 유저 처리 효율을 보인다.

| 기준 (8GB RAM 단일 머신) | JMeter | Locust | **k6** |
|---|---|---|---|
| 처리 가능 VU | ~2,000 | ~5,000 | **~50,000** |
| 동작 원리 | 1 VU = 1 Java Thread | 1 VU = 1 gevent 코루틴 | 1 VU = Go goroutine |
| VU당 메모리 | 1~4 MB | ~1 MB | **수 KB** |

> **공식 근거:** k6 공식 문서에서 단일 머신 30,000~40,000 VU, 최대 300,000 RPS 처리 가능 명시
> — [Running Large Tests | Grafana k6](https://grafana.com/docs/k6/latest/testing-guides/running-large-tests/)

> **공식 근거:** JMeter 공식 Best Practices에서 대규모 테스트 시 GUI 모드의 리소스 한계를 명시하고 CLI 전용 실행 권장
> — [Best Practices | Apache JMeter](https://jmeter.apache.org/usermanual/best-practices.html)

이는 테스트 실행 시 필요한 EC2 인스턴스 규모에 직접적으로 영향을 미치며, t3.medium (4GB) 한 대로 대부분의 부하 시나리오를 소화할 수 있다.

### 3.2 편의성 — 기존 인프라와의 통합

**3개 도구 모두 무료(오픈소스)이므로 라이선스 비용 차이는 없다. 진짜 차이는 기존 인프라와의 통합 비용이다.**

| 기존 인프라 | JMeter | Locust | **k6** |
|---|---|---|---|
| **Prometheus** (이미 설치) | Backend Listener 플러그인 + InfluxDB 중간 레이어 필요 | prometheus_client 직접 개발 또는 별도 exporter 배포 필요 | **`--out experimental-prometheus-rw` 한 줄로 연동 완료** |
| **Grafana** (이미 설치) | 대시보드 직접 설계 | 대시보드 직접 설계 | **공식 대시보드 JSON import만으로 완료** |
| **GitHub Actions** (이미 사용) | CLI 실행 가능하나 결과 파싱 및 Pass/Fail 판정 직접 구현 | CLI 실행 가능하나 Pass/Fail 판정 직접 구현 | **Threshold 내장 → 실패 시 non-zero exit code 자동 반환 → CI 자동 실패** |
| **ArgoCD** (GitOps 사용) | 공식 K8s 지원 없음, XML 파일은 GitOps 부적합 | Helm chart 가능하지만 CRD 없음 | **JS 스크립트로 Git 관리 완벽, 코드 리뷰 가능** |
| **Slack 알림** (이미 설정) | 별도 스크립트 필요 | 별도 스크립트 필요 | **Threshold fail → GitHub Actions fail → 기존 알림 파이프라인 자동 활용** |

> **공식 근거:** k6 Prometheus Remote Write 네이티브 지원
> — [Prometheus Remote Write | Grafana k6](https://grafana.com/docs/k6/latest/results-output/real-time/prometheus-remote-write/)

> **공식 근거:** k6 Threshold 실패 시 non-zero exit code 반환 → CI 자동 실패 처리
> — [Thresholds | Grafana k6](https://grafana.com/docs/k6/latest/using-k6/thresholds/)

> **공식 근거:** k6 Scenarios로 서비스별 독립 VU/duration/executor 정의 가능 → 6개 마이크로서비스 동시 테스트에 적합
> — [Scenarios | Grafana k6](https://grafana.com/docs/k6/latest/using-k6/scenarios/)

### 3.3 비용

| 비용 항목 | JMeter | Locust | **k6** |
|---|---|---|---|
| 라이선스 | 무료 | 무료 | 무료 |
| 10,000 VU 부하 시 EC2 비용 (시간당) | t3.small × 20대 = **$0.416** | t3.small × 7대 = **$0.146** | t3.medium × 1대 = **$0.042** |
| Prometheus/Grafana 통합 셋업 인건비 | 3~5일 | 2~3일 | **0.5일** |
| CI/CD 통합 셋업 인건비 | 2~3일 | 1~2일 | **0.5일** |
| 초기 셋업 총 소요일 | **5~7일** | **3~4일** | **1~2일** |

---

## 4. EKS 외부 설치 사유

### 4.1 외부 테스트를 선택한 이유

실제 사용자 트래픽은 EKS 클러스터 외부에서 유입된다. 성능 테스트의 목적은 사용자와 동일한 경로로 부하를 발생시켜 **전체 인프라 체인의 병목과 한계를 검증**하는 것이다.

```
실제 사용자 요청 경로 (= EC2 외부 테스트 경로):

  사용자/EC2 → Route53 → WAF → ALB → Ingress → Service → Pod
              ~~~~~~~~   ~~~   ~~~
              이 구간은 EKS 내부 테스트 시 완전히 스킵됨
```

| 검증 대상 | EKS 내부 테스트 | EC2 외부 테스트 |
|---|---|---|
| 애플리케이션 응답 성능 | ✅ | ✅ |
| ALB 부하 분산 동작 | ❌ 스킵 | ✅ |
| WAF Rate Limit 동작 | ❌ 스킵 | ✅ |
| Ingress 라우팅 | ❌ 스킵 | ✅ |
| TLS 핸드셰이크 오버헤드 | ❌ 스킵 | ✅ |
| DNS 응답 시간 | ❌ 스킵 | ✅ |
| 실제 네트워크 레이턴시 | ❌ 누락 | ✅ |

> **EKS 내부 테스트는 "앱 단위 벤치마크"이고, 외부 테스트가 실제 "성능 테스트"이다.**

### 4.2 외부 방식이 오히려 더 단순한 이유

EKS 내부 실행 시 필요한 k6-operator(Helm 배포 + CRD + RBAC + ConfigMap 관리)가 불필요해지므로, 전체 구성이 더 간결해진다.

| 항목 | EKS 내부 (k6-operator) | **EC2 외부 (k6 직접 설치)** |
|---|---|---|
| 설치 | Helm + CRD + RBAC 설정 | **`yum install k6` 한 줄** |
| 스크립트 관리 | ConfigMap/PVC 업로드 | **Git clone → 바로 실행** |
| 실행 | `kubectl apply -f testrun.yaml` | **`k6 run script.js`** |
| 디버깅 | Pod 로그 확인 | **stdout 직접 확인** |

### 4.3 EC2 구성

```
┌─── 동일 VPC (rocket-farm) ────────────────────────────────┐
│                                                             │
│  ┌──────────────────┐         ┌──────────────────────────┐ │
│  │  EC2 (k6 전용)    │  HTTPS  │  EKS Cluster              │ │
│  │  t3.medium        │────────▶│  ALB (rocket-farm-main)   │ │
│  │  테스트 시에만 ON  │  :443   │    → Ingress → Service    │ │
│  │                   │         │    → Pod                  │ │
│  │  k6 binary        │         │                           │ │
│  │      │            │         │  Prometheus + Grafana     │ │
│  │      └── 결과 ────│── HTTPS──│──▶ Grafana Cloud (무료)   │ │
│  │                   │         │                           │ │
│  └──────────────────┘         └──────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

- Terraform으로 EC2 관리 → 테스트 시에만 ON/OFF → 비용 거의 0
- 동일 VPC 내 배치로 Security Group 인바운드 허용만으로 ALB 접근 가능
- WAF에 테스트 EC2 IP allowlist 등록 → Rate Limit 차단 방지

---

## 5. k6 OSS + Grafana Cloud 무료 플랜 조합 전략

### 5.1 왜 이 조합인가

| 구성 요소 | 역할 | 비용 |
|---|---|---|
| **k6 OSS** | 테스트 엔진 (EC2에서 실행) | 무료 (AGPL v3) |
| **Grafana Cloud 무료 플랜** | 테스트 결과 저장 · 시각화 · 팀 공유 | **무료 (월 500 VU-hours)** |

Self-hosted Prometheus로 직접 결과를 보내는 방법도 가능하지만, Grafana Cloud 무료 티어를 활용하면 **EKS 내부 Prometheus를 건드리지 않고** 성능 테스트 결과를 독립적으로 관리할 수 있다.

### 5.2 Grafana Cloud 무료 플랜 제공 범위

| 항목 | 무료 제한 | 출처 |
|---|---|---|
| k6 테스트 | **500 VU-hours/월** | [grafana.com/pricing](https://grafana.com/pricing/) |
| Metrics | 10,000 active series | [Grafana Cloud Free Tier](https://grafana.com/products/cloud/free-tier/) |
| Logs | 50 GB/월 | 상동 |
| 데이터 보관 | 14일 | 상동 |
| 사용자 | 3명 | 상동 |
| 비용 | **$0 (신용카드 불필요)** | 상동 |

### 5.3 500 VU-hours 실사용 환산

```
rocket-farm 6개 서비스 기준:

  일반 테스트: 100 VU × 10분 = ~17 VU-hours → 월 약 29회 가능
  중규모 테스트: 200 VU × 15분 = 50 VU-hours → 월 약 10회 가능
  대규모 테스트: 500 VU × 30분 = 250 VU-hours → 월 약 2회 가능

→ 일반적인 성능 테스트 운영에 충분한 수준
```

### 5.4 OSS와 Cloud의 역할 분담

| 상황 | 사용 구성 | 이유 |
|---|---|---|
| PR 머지 시 자동 성능 테스트 | **k6 OSS** (GitHub Actions에서 실행) | Cloud VU-hours 절약, 빈번한 실행 |
| 개발 중 빠른 부하 확인 | **k6 OSS** (EC2에서 직접 실행) | 즉시 실행, 제한 없음 |
| 릴리즈 전 최종 성능 검증 | **k6 OSS + Grafana Cloud** | 결과 영구 저장(14일), 팀 공유 URL 생성, 이전 릴리즈와 트렌드 비교 |
| 팀원/PM에게 결과 리포팅 | **Grafana Cloud** | URL 공유만으로 결과 열람 가능, EKS Grafana 접속 권한 불필요 |

### 5.5 Grafana Cloud 활용의 부가 이점

**EKS 내부 모니터링과 성능 테스트 결과의 분리:**

```
기존 Self-hosted Prometheus/Grafana:
  → 프로덕션 모니터링 전용 (서비스 메트릭, 로그, 알림)
  → 성능 테스트 데이터가 섞이지 않음
  → 프로덕션 Prometheus에 부하를 주지 않음

Grafana Cloud (무료 티어):
  → 성능 테스트 결과 전용
  → 팀 공유, 트렌드 비교, 리포팅
  → EKS 인프라와 완전히 독립적
```

---

## 6. 전체 아키텍처 요약

```
  개발자 PR 생성
       │
       ▼
  GitHub Actions (자동 트리거)
       │
       ├── 소규모 스모크 테스트 → k6 OSS (Actions Runner에서 직접)
       │                          → ALB 공개 엔드포인트 호출
       │                          → Threshold Pass/Fail → PR 상태 반영
       │
       └── 대규모 릴리즈 테스트 → EC2 (k6 OSS) + Grafana Cloud
                                  → ALB → WAF → Ingress → 전체 경로 검증
                                  → 결과 Grafana Cloud 전송 → 팀 공유 URL
                                  → Threshold 실패 시 Slack 알림
```

---

## 7. 결론

| 의사결정 | 선택 | 핵심 근거 |
|---|---|---|
| **도구** | k6 | 기존 인프라(Prometheus · Grafana · GitHub Actions)와 네이티브 통합, 최소 리소스로 최대 VU 처리 |
| **설치 위치** | EKS 외부 (EC2) | 실제 사용자 경로(DNS → WAF → ALB → Ingress → Pod) 전체 검증, k6-operator 불필요로 구성 단순화 |
| **운영 구성** | k6 OSS + Grafana Cloud 무료 플랜 | 일상 테스트는 OSS(무제한), 릴리즈 검증·리포팅은 Cloud 무료 티어(월 500 VU-hours) 활용 — 총 비용 $0 |

---

## 8. 참고 자료

### k6 공식 문서 (Grafana)

| # | 문서 | URL |
|---|---|---|
| 1 | Running Large Tests | https://grafana.com/docs/k6/latest/testing-guides/running-large-tests/ |
| 2 | Prometheus Remote Write | https://grafana.com/docs/k6/latest/results-output/real-time/prometheus-remote-write/ |
| 3 | Thresholds (Pass/Fail) | https://grafana.com/docs/k6/latest/using-k6/thresholds/ |
| 4 | Checks | https://grafana.com/docs/k6/latest/using-k6/checks/ |
| 5 | Scenarios | https://grafana.com/docs/k6/latest/using-k6/scenarios/ |
| 6 | k6 vs JMeter 비교 (Grafana 공식 블로그) | https://grafana.com/blog/k6-vs-jmeter-comparison/ |
| 7 | k6 OSS vs Cloud 비교 | https://k6.io/oss-vs-cloud/ |
| 8 | Grafana Cloud 무료 플랜 | https://grafana.com/products/cloud/free-tier/ |
| 9 | Grafana Cloud 가격 정책 | https://grafana.com/pricing/ |

### JMeter 공식 문서 (Apache)

| # | 문서 | URL |
|---|---|---|
| 10 | Remote (Distributed) Testing | https://jmeter.apache.org/usermanual/remote-test.html |
| 11 | Best Practices | https://jmeter.apache.org/usermanual/best-practices.html |

### Locust 공식 문서

| # | 문서 | URL |
|---|---|---|
| 12 | What is Locust? | https://docs.locust.io/en/stable/what-is-locust.html |
| 13 | Increase Performance (FastHttpUser) | https://docs.locust.io/en/stable/increase-performance.html |
| 14 | Testing other systems/protocols | https://docs.locust.io/en/stable/testing-other-systems.html |
