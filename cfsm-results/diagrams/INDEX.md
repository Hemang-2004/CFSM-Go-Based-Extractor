# CFSM diagrams (37 programs)

Each diagram: title, issue, IPs detected, what the CFSM shows. Files: `<name>.png/.svg/.pdf/.dot`.

| Bug | Type | IPs detected | Diagram |
|---|---|---|---|
| cockroach #1462 | Blocking / Mixed Deadlock / Channel & WaitGroup | none | [blocking_cockroach_1462.png](blocking_cockroach_1462.png) |
| cockroach #2448 | Blocking / Communication Deadlock / Channel | IP-1, IP-3, IP-7 | [blocking_cockroach_2448.png](blocking_cockroach_2448.png) |
| cockroach #24808 | Blocking / Communication Deadlock / Channel | none | [blocking_cockroach_24808.png](blocking_cockroach_24808.png) |
| cockroach #25456 | Blocking / Communication Deadlock / Channel | IP-7 | [blocking_cockroach_25456.png](blocking_cockroach_25456.png) |
| cockroach #35073 | Blocking / Communication Deadlock / Channel | IP-3 | [blocking_cockroach_35073.png](blocking_cockroach_35073.png) |
| cockroach #35931 | Blocking / Communication Deadlock / Channel | none | [blocking_cockroach_35931.png](blocking_cockroach_35931.png) |
| etcd #6857 | Blocking / Communication Deadlock / Channel | IP-1, IP-3, IP-4, IP-8 | [blocking_etcd_6857.png](blocking_etcd_6857.png) |
| etcd #6873 | Blocking / Mixed Deadlock / Channel & Lock | IP-1, IP-4, IP-7 | [blocking_etcd_6873.png](blocking_etcd_6873.png) |
| etcd #7443 | Blocking / Mixed Deadlock / Channel & Lock | none | [blocking_etcd_7443.png](blocking_etcd_7443.png) |
| etcd #7902 | Blocking / Mixed Deadlock / Channel & Lock | none | [blocking_etcd_7902.png](blocking_etcd_7902.png) |
| grpc #1460 | Blocking / Mixed Deadlock / Channel & Lock | IP-1 | [blocking_grpc_1460.png](blocking_grpc_1460.png) |
| grpc #3017 | Blocking / Resource Deadlock / Double locking | none | [blocking_grpc_3017.png](blocking_grpc_3017.png) |
| grpc #660 | Blocking / Communication Deadlock / Channel | IP-1, IP-3, IP-7, IP-8 | [blocking_grpc_660.png](blocking_grpc_660.png) |
| istio #16224 | Blocking / Mixed Deadlock / Channel & Lock | IP-1, IP-3, IP-7 | [blocking_istio_16224.png](blocking_istio_16224.png) |
| kubernetes #10182 | Blocking / Mixed Deadlock / Channel & Lock | IP-1, IP-7 | [blocking_kubernetes_10182.png](blocking_kubernetes_10182.png) |
| kubernetes #11298 | Blocking / Communication Deadlock / Channel & Condition Variable | none | [blocking_kubernetes_11298.png](blocking_kubernetes_11298.png) |
| kubernetes #26980 | Blocking / Mixed Deadlock / Channel & Lock | IP-3 | [blocking_kubernetes_26980.png](blocking_kubernetes_26980.png) |
| kubernetes #38669 | Blocking / Communication Deadlock / Channel | IP-3, IP-7 | [blocking_kubernetes_38669.png](blocking_kubernetes_38669.png) |
| kubernetes #6632 | Blocking / Mixed Deadlock / Channel & Lock | IP-1 | [blocking_kubernetes_6632.png](blocking_kubernetes_6632.png) |
| kubernetes #70277 | Blocking / Communication Deadlock / Channel | none | [blocking_kubernetes_70277.png](blocking_kubernetes_70277.png) |
| moby #27782 | Blocking / Communication Deadlock / Channel & Condition Variable | IP-3, IP-7 | [blocking_moby_27782.png](blocking_moby_27782.png) |
| moby #28462 | Blocking / Mixed Deadlock / Channel & Lock | IP-1 | [blocking_moby_28462.png](blocking_moby_28462.png) |
| moby #29733 | Blocking / Communication Deadlock / Condition Variable | none | [blocking_moby_29733.png](blocking_moby_29733.png) |
| moby #30408 | Blocking / Communication Deadlock / Condition Variable | none | [blocking_moby_30408.png](blocking_moby_30408.png) |
| moby #33293 | Blocking / Communication Deadlock / Channel | none | [blocking_moby_33293.png](blocking_moby_33293.png) |
| moby #4395 | Blocking / Communication Deadlock / Channel | none | [blocking_moby_4395.png](blocking_moby_4395.png) |
| serving #2137 | Blocking / Mixed Deadlock / Channel & Lock | IP-3 | [blocking_serving_2137.png](blocking_serving_2137.png) |
| cockroach #4407  (non-blocking) | NonBlocking / Go-Specific / WaitGroup | none | [nonblocking_cockroach_4407.png](nonblocking_cockroach_4407.png) |
| etcd #3077  (non-blocking) | NonBlocking / Go-Specific / Misuse channel | IP-1, IP-3 | [nonblocking_etcd_3077.png](nonblocking_etcd_3077.png) |
| grpc #2371  (non-blocking) | NonBlocking / Go-Specific / Misuse channel | none | [nonblocking_grpc_2371.png](nonblocking_grpc_2371.png) |
| istio #8967  (non-blocking) | NonBlocking / Go-Specific / Misuse channel | none | [nonblocking_istio_8967.png](nonblocking_istio_8967.png) |
| kubernetes #13058  (non-blocking) | NonBlocking / Go-Specific / WaitGroup | none | [nonblocking_kubernetes_13058.png](nonblocking_kubernetes_13058.png) |
| kubernetes #79631  (non-blocking) | NonBlocking / Traditional / Data race | IP-3 | [nonblocking_kubernetes_79631.png](nonblocking_kubernetes_79631.png) |
| kubernetes #81148  (non-blocking) | NonBlocking / Traditional / Data race | IP-3 | [nonblocking_kubernetes_81148.png](nonblocking_kubernetes_81148.png) |
| kubernetes #82239  (non-blocking) | NonBlocking / Traditional / Data race | IP-3 | [nonblocking_kubernetes_82239.png](nonblocking_kubernetes_82239.png) |
| kubernetes #88331  (non-blocking) | NonBlocking / Traditional / Data race | IP-3 | [nonblocking_kubernetes_88331.png](nonblocking_kubernetes_88331.png) |
| serving #6472  (non-blocking) | NonBlocking / Traditional / Data race | none | [nonblocking_serving_6472.png](nonblocking_serving_6472.png) |
