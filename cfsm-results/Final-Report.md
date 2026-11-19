# CFSM Extraction Results for GoBench

## Summary

This report presents the results of running dingo-hunter's CFSM (Communicating Finite State Machine) extraction tool on the GoBench GoKer benchmark suite, which contains 103 real-world Go concurrency bugs.

### Results Overview

| Category | Count |
|----------|-------|
| **Total bugs analyzed** | 103 |
| **Successful CFSM extractions** | 37 |
| **Empty (no channels)** | 34 |
| **Failed/Crashed** | 32 |

### Key Findings

**37 bugs produced CFSMs** with clear communication patterns. Each successful extraction generated:
- One combined diagram showing all goroutines and channels
- Interface Pattern (IP) detection from the Nesterov et al. (2022) paper
- Communication mismatch analysis (sends without receivers, receives without senders)

### Interface Patterns Detected

The extracted CFSMs show usage of the following interface patterns:

- **IP-1 (Send/Receive)**: Basic one-way communication between goroutines
- **IP-3 (Alternative)**: Choice between multiple communication operations (select statements)
- **IP-4 (Exchange)**: Request-response patterns with acknowledgment
- **IP-7 (Multiple Exchange)**: Repeated communication in loops
- **IP-8 (Racing Receive)**: Goroutine receives from multiple channels (racing messages)

### Bug Categories

**Blocking bugs (68 total)**:
- Communication Deadlock / Channel: 17 bugs → 11 extracted CFSMs
- Mixed Deadlock / Channel & Lock: 13 bugs → 10 extracted CFSMs
- Resource Deadlock: 24 bugs → 1 extracted CFSM
- Other blocking issues: 14 bugs → 4 extracted CFSMs

**Non-blocking bugs (35 total)**:
- Data Races: 20 bugs → 5 extracted CFSMs
- Go-Specific Issues: 12 bugs → 5 extracted CFSMs
- WaitGroup Issues: 2 bugs → 2 extracted CFSMs
- Order Violation: 1 bug → 0 extracted CFSMs

### Tool Limitations

**Why 34 bugs produced no CFSMs**: These programs contain no channels. They use only mutexes, WaitGroups, or shared memory synchronization, which dingo-hunter does not model.

**Why 32 bugs crashed**: 
- Context package issues (11 bugs): `context.Done()` channels cannot be resolved
- Select on unresolved channels (19 bugs)
- Close on unresolved values (4 bugs)
- Internal tool errors (3 bugs)
- Compilation issues after test-to-main conversion (4 bugs)

### Communication Mismatches

In **19 of the 37 extracted CFSMs**, we found clear communication mismatches:
- Sends with no corresponding receiver (goroutine blocks forever)
- Receives with no corresponding sender (goroutine blocks forever)

These mismatches directly correspond to the blocking bugs in the benchmark.

### Conclusion

dingo-hunter successfully extracted CFSMs for **37% of the GoBench suite**. For channel-based bugs, it provides clear visualizations of communication patterns and interface patterns. However, bugs involving locks, context cancellation, or shared memory fall outside its modeling scope.

The extracted diagrams (37 PNG files) show combined state machines with labeled interface patterns and highlighted communication issues, making them useful for understanding Go concurrency bugs.

---

**Generated**: November 20, 2026  
**Tool**: dingo-hunter (CFSM extractor)  
**Benchmark**: GoBench GoKer (103 bugs)  
**Results**: 37 CFSM diagrams with IP pattern detection
