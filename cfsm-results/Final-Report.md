# Running dingo-hunter's CFSM extraction on GoBench: Results and Interaction Patterns

*Project Elective · 31 October 2026*

## 1. About the project

In this project I took a static analysis tool, **dingo-hunter**, and ran it on a benchmark of real Go concurrency bugs, **GoBench**. I then used a research paper, *Discovering architecture-aware and sound process models of multi-agent systems: a compositional approach* (Nesterov, Bernardinello, Lomazova and Pomello, Software and Systems Modeling, 2022), to describe what kinds of interactions the programs contain.

**dingo-hunter** reads Go source code and builds a **Communicating Finite State Machine (CFSM)** for every goroutine and every channel. A CFSM is a small state graph where each edge is a channel send (`!`) or receive (`?`). The `cfsms` command of dingo-hunter produces these machines. In the output, `close(ch)` is encoded as a message called `STOP`. The tool only models channel communication, and it assumes channels are unbuffered. Judging whether the machines are safe is a second step, done by a separate Haskell tool (`gmc-synthesis`), which I did not run.

**GoBench** is a collection of real concurrency bugs from projects such as etcd, Kubernetes, Moby, CockroachDB and gRPC. I used its **GoKer** part, which has **103** small bug programs: 68 blocking bugs (deadlocks and leaks) and 35 non-blocking bugs (data races and misuse of Go features).

**The paper** is about process mining. It proposes describing a multi-agent system by composing the models of individual agents through a small catalogue of **twelve interface patterns (IP-1 to IP-12)**, each proven not to deadlock. The paper's warning that agent interactions can easily be arranged so that they deadlock is exactly what GoBench is about. I used the twelve patterns as a vocabulary to classify what I found.

## 2. What I did

I built dingo-hunter (this needed Go 1.19 and a one-line patch, because one function it used had been removed from a library). For each of the 103 bug files I did what GoBench itself does: turned the test function into `main` and fixed the imports. Then I ran `dingo-hunter cfsms` on every file and wrote a script to read the resulting machines and tag the interaction patterns. All outputs, logs and a per-bug summary table are in the `cfsm-results` folder.

## 3. Main results

| Outcome | Programs |
|---|---|
| GoKer bugs analysed | **103** |
| Ran to completion | 71 |
| &nbsp;&nbsp;…and produced CFSMs | **37** |
| &nbsp;&nbsp;…and produced nothing (no channels in the program) | 34 |
| Crashed inside dingo-hunter | **32** |

- **The 37 programs gave 138 machines** (70 channel machines and 68 goroutine machines). They are small: one to three goroutines and one to five channels each.
- **The 34 empty runs are expected.** 32 of them use no channel at all (they are about mutexes, WaitGroups or shared memory), and dingo-hunter models only channels.
- **The 32 crashes** mostly come from `select` statements it could not resolve (19), `close()` on something it could not trace to a channel (4), internal nil-pointer errors (3), and a few programs that did not compile after the rewrite (4) or failed to type-check (1). The biggest single cause is Go's `context` package: **11 of the 16 programs that use `context` crashed**, including all seven bugs labelled "Channel & Context".
- **What the CFSMs say.** In 19 of the 37 models there is a channel with a send but no receive, or a receive but no send. In a synchronous model such an operation can never complete, which is what a blocked or leaked goroutine looks like. For the 11 plain "Channel" communication deadlocks that produced a model, **10 show this mismatch** directly. The remaining one (grpc #660) has both ends of the channel present, and finding its bug needs the ordering analysis that I did not run. The mismatch check is my own simple test, not an official verdict from the tool.

One example. In `moby #4395` a goroutine sends an error on a channel that nobody reads. The CFSM is just a goroutine with `0 ! error` and a channel machine waiting to pass it on. No machine ever receives it, so the send is stuck, which matches the real bug.

## 4. Which interaction patterns (IPs) were present

I tagged the 37 modelled programs by the structure of their goroutine machines and checked the tags by hand against the source for eight of them.

| Pattern | What it means | Programs | Examples |
|---|---|---|---|
| **IP-1** Send / Receive | One goroutine sends, another receives, no reply | **10** | grpc #1460, moby #28462, kubernetes #10182 |
| **IP-3** Alternative send / receive | One of several messages is chosen (`select`, `if`) | **14** | grpc #660, cockroach #2448, etcd #6857 |
| **IP-4** Exchange | A request followed by a reply | **2** | etcd #6857, etcd #6873 |
| **IP-7** Multiple exchange | Repeated exchange in a loop until stopped | **8** | grpc #660, istio #16224, cockroach #2448 |
| **IP-8** Racing incoming messages | A goroutine takes the first of messages from two or more senders | **2** | grpc #660, etcd #6857 |
| IP-2, IP-5, IP-6 | Concurrent or alternative sends / exchanges | not found | |
| **IP-9 to IP-12** Sync + exchange | A synchronous action combined with message exchange | not visible in CFSMs | see below |

Points worth stating:

- **The programs are built from the simplest patterns: IP-1, IP-3 and IP-7.** IP-8 appears in two programs only, but 20 of the 32 crashed programs contain a `select`, so racing receives are probably under-counted. IP-4 is rare.
- **`grpc #660` contains three patterns at once.** One goroutine races a `stop` message against a `done` message (IP-8), the sender chooses between two values (IP-3), and the receiver loops (IP-7). The paper's IP-8 requires the losing sender to be notified. Here it is not, so its goroutine leaks. That is the bug.
- **`etcd #6857` is the richest model.** It has five channels and three goroutines. It combines a request and reply (IP-4), a `select` racing two senders (IP-8), and even a channel passed as a value, which is outside the paper's patterns.
- **The mixed patterns (IP-9 to IP-12)** combine messages with a synchronous action. GoBench has 17 bugs that combine channels with a lock, WaitGroup or condition variable, which is the closest real-world equivalent. dingo-hunter models only the channel half, so these show up in the CFSM as ordinary IP-1 or IP-7 behaviour while the lock, which causes the bug, is invisible. For example, `kubernetes #10182` shows two producers and one looping consumer, which looks healthy.
- **My interpretation** is that a GoBench channel bug is usually one of these patterns with its safety condition broken: a send nobody receives (IP-1), a race loser that is never told (IP-8), or a loop with no way to stop (IP-7). The paper does not say this about Go; it is my reading.

## 5. Is it suitable for race detection?

**No. dingo-hunter's CFSM extraction is not suitable for data-race detection.** My reasons:

1. **A data race is about unsynchronised access to shared memory.** CFSMs record only channel sends and receives. Reads and writes of variables, and the mutexes that protect them, never appear in the model, so there is nothing for a race check to work on.
2. **The results on the race bugs confirm it.** GoKer has 21 "traditional" bugs (20 data races and 1 order violation). Of these, **13 produced no model, 3 crashed, and only 5 produced a CFSM**. Those 5 contain only incidental channel operations, which I tagged as IP-3 (four programs) or no pattern (one), and none of them shows a race.
3. **The tool was designed for communication deadlocks**, as its own README states. It is built to find mismatches between sends and receives, not unsynchronised memory access.

**Where it is useful:** for the plain channel deadlocks and goroutine leaks (the "Communication Deadlock / Channel" group), it produced a model for 11 of the 17 bugs, and 10 of those 11 showed a send-without-receive or receive-without-send mismatch. So for channel-based blocking bugs it is a reasonable first-stage tool, as long as the real verdict step (`gmc-synthesis`) is added. For bugs involving locks, `context`, or shared memory, it is not suitable. For race detection, a dynamic tool such as Go's built-in race detector (`go test -race`) is the appropriate choice.

## 6. Limitations

- I did not run `gmc-synthesis`, so I have no official safe/unsafe verdicts.
- dingo-hunter treats every channel as unbuffered. 6 of the 11 programs with an unreceived send use buffered channels, so those may be false alarms.
- The pattern tags come from simple rules and were checked by hand on eight programs only. The paper's patterns are defined for asynchronous channels, while Go's unbuffered channels are synchronous, so the mapping is an analogy.
- I used Go 1.19, not the toolchain GoBench targets, so a few results could differ on Linux.

## 7. Conclusion

dingo-hunter produced usable CFSMs for 37 of the 103 GoBench programs. Those programs use mostly the simple patterns IP-1, IP-3 and IP-7, with IP-8 and IP-4 in a few cases, and the channel deadlocks among them show clear send/receive mismatches. It cannot see locks, `context` or shared memory, so it is **not suitable for race detection** and only partly suitable for deadlock detection.

*Full details, worked examples and appendices are in REPORT.pdf in the same folder.*
