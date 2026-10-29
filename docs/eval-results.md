# Evaluation: agent with memory vs without memory

| # | Alert | Expected change | With memory | Without memory |
|---|---|---|---|---|
| 1 | EC2 CPU utilization above 92 percent for 10 minutes on cloud-pulse-web | bigger | PASS (bigger) | PASS (bigger) |
| 2 | Website slow and CPU saturated at 97 percent | bigger | PASS (bigger) | PASS (bigger) |
| 3 | 5xx errors rising, instance memory exhausted | bigger | not run | not run |
| 4 | Throughput dropped during traffic spike, CPU at 90 percent | bigger | not run | not run |
| 5 | FinOps: instance averaged 0.2 percent CPU over 24h, oversized and wasting money | smaller | not run | not run |
| 6 | Latency is high but CPU is normal at 12 percent | same | not run | not run |
| 7 | Disk usage above 90 percent on web server | same | not run | not run |
| 8 | EC2 status check failed on cloud-pulse-web | same | not run | not run |

**With memory: 2/2 correct. Without memory: 2/2 correct.**

Method: fixed baseline main.tf (t3.micro), rule-based scoring on the direction of the instance_type change. Memory is a small seeded set of 8 incidents plus lessons from real PRs, so this shows the memory effect, not a general benchmark.