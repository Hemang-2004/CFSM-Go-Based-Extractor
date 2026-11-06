# What dingo-hunter sees in GoBench

### A CFSM extraction study of the 103 GoKer bugs, read through the interface patterns of Nesterov et al. (2022)

*Project Elective · prepared 31 October 2026*

---

## 1. The short version

I ran dingo-hunter's CFSM extractor (`dingo-hunter cfsms`) over all 103 GoKer bug kernels in GoBench, and then used the twelve "interface patterns" from the Nesterov paper as a vocabulary to describe what the extracted models, and the programs behind them, are actually doing.

**What happened when I ran it**

- Of 103 programs, **71 ran to completion** and **32 crashed** inside dingo-hunter.
- Of the 71 that finished, only **37 produced any CFSMs**. The other **34 produced nothing**, and for 32 of those 34 the reason is simple: the program uses no channel at all, and dingo-hunter only models channels.
- The 37 programs gave **138 machines**: 70 channel machines and 68 goroutine machines. Most programs are tiny, with one to three goroutines and one or two channels.
- dingo-hunter does **not** print a "deadlock found" verdict on its own. The verdict comes from a separate Haskell tool (`gmc-synthesis`) that I did not install or run. So what follows is a description of the models, not a bug-detection score.

**What the CFSMs say**

- In **19 of the 37** models there is a channel with a send and no receive, or a receive and no send. That is a communication mismatch. In a synchronous model such an operation can never complete, which is exactly what a leaked or blocked goroutine looks like.
- For the 11 plain "Channel" communication deadlocks, **10 show a mismatch** straight from the model. The one that does not (grpc #660) is the most interesting case, and I walk through it in section 5.
- For bugs that combine channels with a **lock**, the CFSM looks perfectly healthy, because the lock is invisible to the tool. This is the biggest blind spot.

**Which interaction patterns GoBench uses**

- The modelled programs are built almost entirely from the simplest patterns in the paper: one-way **Send/Receive (IP-1)**, **alternative send/receive (IP-3)** through `select` or `if`, **repeated exchange until stop (IP-7)** through loops, and, in two programs, **racing incoming messages (IP-8)**. A genuine request/response **Exchange (IP-4)** shows up only twice.
- My main interpretive claim is that **a GoBench channel bug is usually a pattern whose soundness condition has been broken**: a send nobody receives (IP-1), a loser of a race that is never told it lost (IP-8), a loop with no way to stop (IP-7). Section 6 goes through this. It is my reading, not something the paper says about Go.

---

## 2. The two source materials, in plain language

### 2.1 The paper

*Discovering architecture-aware and sound process models of multi-agent systems: a compositional approach*, by Roman Nesterov, Luca Bernardinello, Irina Lomazova and Lucia Pomello, *Software and Systems Modeling* (2022), doi 10.1007/s10270-022-01008-x.

The paper is about **process mining**, not Go. You start with an event log of a multi-agent system, a list of who did what and when. If you feed the whole log to an off-the-shelf discovery algorithm (they use the Inductive Miner), you get a Petri net that replays the log, but it is a tangle: the agents' behaviours are knotted together with extra silent transitions, and it over-generalises what each agent can do.

Their fix is **compositional**:

1. **Filter** the log by agent, giving one small log per agent.
2. **Discover** a small, sound Petri net (a "GWF-net") for each agent from its own log.
3. **Compose** them through an **interface pattern**, a small, pre-proven-sound net that says how the agents talk (who sends, who receives, who synchronises). Each agent's discovered net has to be a *refinement* of its slot in the pattern. If it is, the composed model is guaranteed sound, meaning it can always finish and has no dead actions.

The reason for restricting yourself to a catalogue is a warning in Section 3 that is directly relevant to this project: *"It is easy to arrange agent interactions leading to deadlocks."* Their example is two perfectly sound agents, where one may decide never to receive a message the other is waiting on. Composed, they deadlock. Arbitrary composition is not safe; composition through a vetted pattern is.

**The twelve interface patterns** (Tables 3 and 4 of the paper):

| ID | Name | Meaning |
|---|---|---|
| IP-1 | Send / Receive | X sends a message to Y (or receives from Y); no reply |
| IP-2 | Concurrent send / receive | X sends several messages to Y at once |
| IP-3 | Alternative send / receive | X sends exactly one of two or more alternative message sets |
| IP-4 | Exchange | X sends, then Y replies |
| IP-5 | Concurrent exchange | several concurrent requests, each answered |
| IP-6 | Alternative exchange | one of several alternative requests, answered correspondingly |
| IP-7 | Multiple exchange | IP-4 repeated until X decides to stop |
| IP-8 | Racing incoming messages | X receives one of several messages from two or more other agents; the losers must be notified or have their message removed |
| IP-9 | Sync before exchange | a joint synchronous action, then the exchange |
| IP-10 | Sync after exchange | the exchange, then a joint synchronous action |
| IP-11 | Sync and exchange | the synchronous action runs concurrently with the exchange |
| IP-12 | Sync or exchange | either the synchronous action or the exchange, not both |

IP-1 to IP-7 are bilateral (two agents). IP-8 is the only multilateral pattern. IP-9 to IP-12 mix messages with a joint synchronous step. Each pattern is provably sound (Proposition 1).

**What the experiments found.** Using artificial logs from reference models for each of the twelve patterns, the compositional approach cut the number of "neighbouring transitions" (a measure of how tangled the interaction structure is) by **83% to 97%** compared with direct discovery. Its precision stayed within about 10% of the reference model. Two cases did not go smoothly. For IP-2 the discovered agents were not valid refinements, because the log never showed the concurrent actions in different orders. For IP-7, direct discovery's precision collapsed (down 61% against the reference), while the compositional model held up.

**The paper's own stated limits** matter for this project: the catalogue is incomplete by their own admission, choosing the pattern is a manual step, and **broadcast communication** is listed as future work.

**One honest note on "running" the paper.** The paper has no runnable tool that works on Go. Its experiments use the ProM process-mining platform, with data on Zenodo. I read the whole paper and used its pattern catalogue as a lens. I did not re-run its ProM experiments, and its patterns are defined over asynchronous Petri-net channels. Go's unbuffered channels are rendezvous. So the mapping in section 6 is an analogy, and I flag where it strains.

### 2.2 dingo-hunter and CFSMs

dingo-hunter (`nickng/dingo-hunter`, the tool behind Ng and Yoshida's CC 2016 paper and the POPL 2017 "Fencing off Go" paper) is a static analyser for Go. Given a `main` package it builds an SSA form, runs a pointer analysis, and for each goroutine extracts a **Communicating Finite State Machine**: a small state graph whose edges are channel sends (`!`) and receives (`?`).

Three things to know when reading its output:

- A line such as `q10 0 ? bool q12` means: *in state q10, receive a `bool` from machine 0, then move to q12.* The number is the **peer machine**. For a goroutine, the peers are channels.
- **Channels are machines too.** Every channel becomes a small relay machine that receives from one goroutine and hands the value to another. These come first in the output, which is why the tool says, for example, `Total of 5 CFSMs (2 are channels)`.
- `STOP` is the tool's encoding of **`close(ch)`**. A send of `STOP` is a close; a receive of `STOP` is the receiver noticing the close.

dingo-hunter's own README lists limits that matter later: it supports **unbuffered (synchronous) channels only**, and it assumes goroutines spawned after a communication do not depend on it.

### 2.3 GoBench and GoKer

GoBench is a benchmark of real concurrency bugs from open-source Go projects (etcd, Kubernetes, Docker/Moby, CockroachDB, gRPC and others). Its **GoKer** half distils each bug into a small self-contained test file. There are **103** of them: **68 blocking** and **35 non-blocking**. Each one carries a taxonomy label: communication deadlock, mixed deadlock, resource deadlock, data race, misuse of a Go feature, and so on.

---

## 3. What I did

1. **Built dingo-hunter.** It would not build on the installed Go 1.27: one API it used (`CreateTestMainPackage`) had been removed upstream, and the pinned `x/tools` crashes on a newer Go type feature. I installed **Go 1.19.13** and patched a single call in `ssabuilder/pointer.go`. That only affects packages with no `main`, which does not apply here. I also restored `go.mod` and `go.sum` to their original contents.
2. **Prepared each bug** the same way GoBench's own `InstrumentMainFunc` does: rename the `Test…` function to `main`, make the package `main`, drop the `testing` import, and fix imports with `goimports`. I used `perl` instead of `sed -i` because the latter behaves differently on macOS.
3. **Ran `dingo-hunter cfsms`** on every `*_test.go` under `goker/`, eight in parallel, with a two-minute limit each. Nothing hit the limit; the whole sweep took about nine seconds.
4. **Parsed the output** with a script: per goroutine, which channels it sends on, receives from, closes, and whether it has a choice point or a loop; per channel, who sends, receives and closes.
5. **Tagged patterns** from that structure, using simple rules (section 6.1), then **spot-checked** the tags against the Go source and the bug descriptions for eight programs (section 6.1).

Everything is in the `cfsm-results` folder: `summary.tsv` (one row per bug), `cfsms/` (the 71 output files) and `logs/` (the run logs).

**What I did not do:** I did not run `gmc-synthesis` (it needs a Haskell toolchain, `cabal` packages and the `petrify` binary), so there are no tool-issued safety verdicts. I also did not run GoReal (the larger half of GoBench, which needs Docker) or the paper's ProM experiments.

---

## 4. Results of running dingo-hunter on GoBench

### 4.1 The funnel

| Stage | Programs |
|---|---|
| GoKer bugs | **103** |
| Ran to completion | 71 |
| &nbsp;&nbsp;&nbsp;…of which produced CFSMs | **37** |
| &nbsp;&nbsp;&nbsp;…of which produced nothing ("Machine 0 is empty") | 34 |
| Crashed inside dingo-hunter | **32** |

### 4.2 Coverage by bug type

| Kind / family | Bug type | Bugs | CFSMs produced | Ran, nothing found | Crashed |
|---|---|---|---|---|---|
| Blocking / Communication Deadlock | Channel | 17 | 11 | 0 | 6 |
| Blocking / Communication Deadlock | Channel & Condition Variable | 2 | 2 | 0 | 0 |
| Blocking / Communication Deadlock | Channel & Context | 7 | 0 | 0 | 7 |
| Blocking / Communication Deadlock | Condition Variable | 2 | 2 | 0 | 0 |
| Blocking / Mixed Deadlock | Channel & Lock | 13 | 10 | 0 | 3 |
| Blocking / Mixed Deadlock | Channel & WaitGroup | 2 | 1 | 0 | 1 |
| Blocking / Mixed Deadlock | Misuse WaitGroup | 1 | 0 | 1 | 0 |
| Blocking / Resource Deadlock | AB-BA Deadlock | 6 | 0 | 4 | 2 |
| Blocking / Resource Deadlock | Double Locking | 14 | 1 | 9 | 4 |
| Blocking / Resource Deadlock | RWR Deadlock | 4 | 0 | 3 | 1 |
| NonBlocking / Go-Specific | Anonymous Function | 4 | 0 | 3 | 1 |
| NonBlocking / Go-Specific | Misuse Channel | 6 | 3 | 1 | 2 |
| NonBlocking / Go-Specific | Testing Library | 2 | 0 | 0 | 2 |
| NonBlocking / Go-Specific | WaitGroup | 2 | 2 | 0 | 0 |
| NonBlocking / Traditional | Data Race | 20 | 5 | 13 | 2 |
| NonBlocking / Traditional | Order Violation | 1 | 0 | 0 | 1 |
| **All of GoKer** |  | **103** | **37** | **34** | **32** |


The pattern is clear. **The tool only sees channels.** Almost everything that is purely about locks (double locking, AB-BA, read-lock recursion) comes back empty or crashes, and most data races come back empty too. Where channels are present it often works, with two exceptions: anything involving `context`, and anything it cannot resolve.

### 4.3 The 34 "empty" runs are not failures

32 of the 34 programs contain no `make(chan …)` at all. They are about mutexes, WaitGroups, or shared memory. dingo-hunter ran correctly and found nothing to model. The full list is in Appendix C.

### 4.4 The 32 crashes

| Cause | Programs |
|---|---|
| `select` on a channel the extractor could not resolve | 19 (9 of them inside Go's own `context` package) |
| `close()` on something it could not resolve to a channel | 4 |
| Nil-pointer crash inside dingo-hunter | 3 |
| Receive on an unresolved channel | 1 |
| Does not compile as `main` after the test-to-main rewrite (still uses `t *testing.T`) | 4 |
| Standard library `net` would not type-check (cgo on macOS) | 1 |

The most telling finding is about **`context`**. dingo-hunter follows calls into the standard library, reaches `context.propagateCancel`, and trips on a `select` over the parent's `Done()` channel, which it cannot resolve. **11 of the 16 programs that use `context` crashed**, including all seven GoBench bugs labelled "Channel & Context". That is a real modelling gap, because `context` cancellation is one of the most common interaction idioms in modern Go. Appendix B has the per-bug reasons.

### 4.5 What the CFSMs look like

Across the 37 programs:

- **138 machines**: 70 channel machines and 68 goroutine machines.
- **Channels per program**: 1 channel in 18 programs, 2 in 10, 3 in 6, 4 in 1, 5 in 2.
- **Goroutine machines per program**: 1 in 13, 2 in 14, 3 in 9. (One program had a channel but no goroutine machine.)
- **22 of 37** use `close` (the `STOP` message), **14** contain a choice point such as a `select`, and **7** contain a loop.

These are small systems. That is a property of GoKer: each bug was boiled down to the few lines that matter.

---

## 5. Reading the CFSMs: four worked examples

### 5.1 `moby #4395`: the simplest broken pattern

The source, in essence:

```go
func Go(f func() error) chan error {
    ch := make(chan error)
    go func() { ch <- f() }()      // G2
    return ch
}
func TestMoby4395(t *testing.T) { Go(func() error { return errors.New("") }) }   // never reads ch
```

dingo-hunter's output:

```
Machine 0  (the channel)   q00  1 ? error  q02
Machine 1  (goroutine)     q10  0 ! error  q11
```

The goroutine sends an `error` to the channel. The channel machine is ready to take it and pass it on, but **no machine ever receives from the channel**. Read straight off the CFSM, the send has no receiver. In the paper's terms, this is an **IP-1 (Send)** whose partner never appears. GoBench's own description says the same thing in words: the anonymous goroutine can be stuck sending on a channel that nobody ever drains.

### 5.2 `grpc #660`: a race where the loser is never told

```go
func (bc *benchmarkClient) doCloseLoopUnary() {            // G1
    for {
        done := make(chan bool)
        go func() { if rand.Intn(10) > 7 { done <- false; return }; done <- true }()   // G2
        select {
        case <-bc.stop: return
        case <-done:
        }
    }
}
// a helper goroutine does:  bc.stop <- true
```

The extracted CFSM has **two channels** (`stop`, `done`) and **three goroutines**:

```
helper     q20  0 ! bool  q21                       send on stop
G2         q30  1 ! bool  q31   |   q30  1 ! bool  q32   either of two sends on done
G1 (loop)  q40  0 ? bool  q41   |   q40  1 ? bool  q40   receive from stop (exit) or from done (loop)
```

It is a very faithful picture of the code, and it contains three of the paper's patterns at once:

- **IP-8, racing incoming messages**: G1 takes whichever of `stop` or `done` arrives first, from two different senders.
- **IP-3, alternative send**: G2 sends one of two alternatives.
- **IP-7, multiple exchange**: G1 loops.

The paper's definition of IP-8 includes a clause that is easy to miss: the losing sender must be notified, or its message removed. G1 takes `stop` and returns, and G2 is left blocked forever on `done <-`. That is the bug. It is also why this is the one plain-channel bug where the **simple "send with no receiver" check passes**. Both ends of `done` exist in the model. Finding the leak needs the ordering analysis that the synthesis step performs, which I did not run.

### 5.3 `etcd #6857`: the richest model in the set

`etcd #6857` has five channels, three goroutines, and, unusually, a **channel sent over a channel**. A client calls `Status()`, which creates a private reply channel and sends it to the node's `status` channel. In the CFSM that appears as `q50 0 ! chan Status`. The node's `run()` loop does `select { case c := <-n.status: …; case <-n.stop: close(n.done); return }`:

```
Status caller  q50  0 ! chan Status q51 ;  q51  4 ? Status q52      request, then wait for the reply
Stop caller    q60  1 ! struct{} q61  |  q60  2 ? struct{} q63      send stop, or see done
run loop       q70  0 ? chan Status q71  |  q70  1 ? struct{} q73   race: status request vs stop
               q73  2 ! STOP q74                                    close(done)
```

This single program covers IP-8 (the `select` racing two senders), IP-4 (request/reply, using a reply channel in one case and `close(done)` as the acknowledgement in the other), and IP-3. The bug, per the source, is that once `Stop()` has made `run()` return, a later `Status()` sends on `n.status` and nobody is left to receive.

Passing a channel as a value is outside the paper's model, where channels are fixed parts of the interface. It is an example of what the catalogue would need to grow to cover.

### 5.4 `kubernetes #10182`: when the CFSM looks fine and the program is not

The bug is a mutex held while sending on a channel:

```go
func (s *statusManager) SetPodStatus() {
    s.podStatusesLock.Lock(); defer s.podStatusesLock.Unlock()
    s.podStatusChannel <- true         // blocks while holding the lock
}
```

The CFSM shows two producers, `SetPodStatus` ×2, each sending one `bool`, and one consumer that loops receiving `bool`. That is a perfectly healthy **fan-in feeding a loop**. The consumer even looks like it can run forever. **The lock does not appear anywhere in the model, and the lock is the bug.** Nothing in the CFSM hints at the deadlock.

The same blind spot applies to the other "Channel & Lock" bugs, and it is the clearest reason the CFSM approach alone cannot serve as a GoBench detector.

---

## 6. Interaction patterns used in GoBench

### 6.1 How I assigned patterns

For each of the 37 modelled programs I looked at the structure of the goroutine machines:

- **IP-1**: a channel with a sender and a *different* receiver.
- **IP-3**: a state with two or more alternative sends or receives (a `select`, `if`, or `switch`). A plain "receive a value, or see the close" fork on a single channel is *not* counted. That is the normal end of a `range` loop.
- **IP-4**: two goroutines each sending to the other on different channels, with `close` counted as an acknowledgement.
- **IP-7**: a goroutine with communication inside a cycle, or a drain-until-closed fork.
- **IP-8**: an alternative-receive state whose channels are fed by two or more different goroutines.

These are heuristics. I checked them by hand against the source for eight programs: five read closely (moby #4395, grpc #660, etcd #6857, kubernetes #10182, cockroach #35073) and three by their channel operations only (etcd #6873, cockroach #2448, serving #2137). Treat the counts as indicative, not exact.

### 6.2 The census

| Paper pattern | What it means | What it looks like in Go | Programs | Examples |
|---|---|---|---|---|
| IP-1 Send / Receive | One agent sends, another receives, no reply expected | `ch <- v` in one goroutine, `<-ch` in another | 10 | cockroach #2448, etcd #6857, etcd #6873, grpc #1460 |
| IP-2 Concurrent send / receive | Several messages sent at once | A goroutine spawning several senders, or independent channel operations | not separable | Concurrency lives *between* CFSMs, so the tool never shows it as one pattern |
| IP-3 Alternative send / receive | Exactly one of several message sets is used | `select` with several cases, or `if`/`switch` choosing what to send | 14 | cockroach #2448, cockroach #35073, etcd #6857, grpc #660 |
| IP-4 Exchange | Request, then a response | Send a request, wait on a reply channel or on `close(done)` | 2 | etcd #6857, etcd #6873 |
| IP-5 / IP-6 Concurrent and alternative exchange | Several requests, or one of several, each answered | Parallel or `select`-guarded request/reply | 0 | none recovered |
| IP-7 Multiple exchange | Repeat the exchange until one side stops it | A `for` loop with channel operations, `for range ch`, receive until `close` | 8 | cockroach #2448, cockroach #25456, etcd #6873, grpc #660 |
| IP-8 Racing incoming messages | One agent takes the first of messages from two or more others | `select` over channels fed by different goroutines | 2 | etcd #6857, grpc #660 |
| IP-9 to IP-12 Sync + exchange | A joint synchronous action combined with message exchange | Channels combined with a lock, WaitGroup, Cond or context (not visible to the tool) | 17 bugs labelled this way by GoBench | Channel & Lock 13, Channel & WaitGroup 2, Channel & Cond 2 |


**How to read it.**

- Seventeen of the 37 programs show *no* paper pattern. They are mostly single-goroutine send or receive fragments (the bug has already been boiled down to one dangling operation), plus WaitGroup and Cond-variable bugs.
- **IP-1, IP-3 and IP-7 dominate**, and **IP-8 appears only twice** among the programs that survived. However, **20 of the 32 crashed programs contain a `select`**, so racing receives are very likely under-counted. The programs most likely to contain IP-8 are the ones the tool could not model.
- **Four of the 14 IP-3 tags sit on data-race bugs**, where the "alternative" probably comes from ordinary `if`/`switch` branching rather than a deliberate message choice. I did not check each one.
- **IP-4 is rare**: just two programs. Go programmers usually express "ask and wait" with `sync.WaitGroup`, a `done` channel, or `context`, rather than a full request/reply pair. In this benchmark it is mostly the *absence* of the reply that causes the bug.
- **IP-2, IP-5 and IP-6 never show up as separate patterns.** That is partly a limitation of the tool: each goroutine is its own sequential machine, so concurrency is something that happens *between* machines, not inside one.

### 6.3 The whole benchmark, by the constructs used

I also counted constructs directly in all 103 source files, which includes the programs dingo-hunter could not model. These are text counts, so treat them as approximate.

| Construct | Programs using it (of 103) |
|---|---|
| `make(chan …)` | 63 (of which 15 use a buffered channel) |
| `select` | 45 |
| `close(…)` | 45 |
| `sync.Mutex` / `RWMutex` | 63 |
| `sync.WaitGroup` | 39 |
| `time.After` / `Sleep` / timers | 33 |
| `context` | 16 |
| `sync.Cond` | 9 |

Two things stand out. **Channels and locks are equally common (63 each)**, so a tool that sees only one of them is blind to about half the benchmark. And **`close` is everywhere (45)**. In Go, closing a channel is the native way to *broadcast* "we're done" to every receiver, and the paper lists broadcast as an *open item for future work*. Of the patterns in this benchmark, that is probably the one the paper's catalogue most obviously lacks.

### 6.4 The mixed patterns IP-9 to IP-12

The paper's mixed patterns combine a message exchange with a **joint synchronous action**. GoBench has no single construct that is exactly that, but the closest analogue is the large group of bugs where **channels are combined with another synchronisation primitive**: 13 "Channel & Lock", 2 "Channel & WaitGroup", 2 "Channel & Condition Variable", and 7 "Channel & Context" (context cancellation behaves like a channel close).

dingo-hunter models only the channel half of each. That is why, in section 5.4, the CFSM of a Channel-&-Lock bug can look entirely innocent: **the half that carries the sync is not in the model.** Real Go locks are mutual exclusion, not the simultaneous two-party action the paper formalises, so the mapping to IP-9..IP-12 is an analogy, not an equivalence.

### 6.5 Bugs as broken pattern conditions (my interpretation)

The paper's whole argument is that *sound* patterns keep agents from getting stuck, and that "arbitrary interfaces" are dangerous. Reading GoBench's channel bugs through that lens, many of them are simply a pattern with one of its conditions removed:

| Paper pattern | Condition that keeps it sound | The GoBench bug when it is violated | Examples |
|---|---|---|---|
| IP-1 Send | Somebody receives what is sent | Send with no receiver; the sender blocks forever | moby #4395, moby #33293 |
| IP-8 Racing | The loser is notified or its message removed | Parent returns without draining the other channel; the sender leaks | grpc #660, grpc #1424, kubernetes #5316, moby #33781 |
| IP-7 Multiple exchange | The loop can be stopped, and both sides agree when | Producer outlives its consumer, or `close` is never reached (the typical shape; I did not confirm it bug by bug) | kubernetes #38669, cockroach #25456 (loop shape only) |
| IP-4 Exchange | A reply always comes | Request sent after the server has shut down | etcd #6857 (see 5.3) |
| IP-9..12 Sync + exchange | The sync step cannot block the exchange | A lock is held while blocking on a channel | kubernetes #10182, #6632, #1321, grpc #1353 |

Two cautions. The IP-8 and IP-9..12 examples other than grpc #660 come from GoBench's bug descriptions, not from CFSMs, because those programs crashed. And this table is my reading of how the paper's soundness conditions line up with GoBench's bug descriptions. The paper does not discuss Go or these bugs.

### 6.6 What the paper's catalogue does not cover

Looking across GoBench, the interactions it would need to grow to describe are:

1. **Locks and shared memory**: 24 resource-deadlock bugs and 20 data races have no channel interaction at all.
2. **Cancellation through `context`**: a one-to-many "stop" signal.
3. **Broadcast via `close`**: used in 45 of the 103 programs.
4. **Channels as values**: channels sent over channels (etcd #6857).
5. **Buffered channels as semaphores or queues** (15 programs; serving #2137 uses them as token pools).
6. **Multilateral patterns beyond IP-8**: fan-in and fan-out (kubernetes #10182 and cockroach #2448).

---

## 7. Caveats

- **No verdicts.** I did not run `gmc-synthesis`. The "send with no receiver" signal in this report is my own simple check on the CFSMs, a stand-in for the real analysis.
- **Orphan sends are not always bugs.** 6 of the 11 programs with an unreceived send use a *buffered* channel. dingo-hunter treats every channel as unbuffered, so in the real program the send would have completed. For example, cockroach #35073 uses a 16-slot buffer.
- **Loops are over-approximated.** In `kubernetes #10182` the real consumer loops exactly twice, while the CFSM shows an unbounded receive loop.
- **Pattern tags are heuristics**, spot-checked on eight programs but not all 37.
- **Static construct counts** (section 6.3) are text matches, so a mention in a comment or an unused import could skew them slightly.
- **The patch to dingo-hunter** only affects packages without a `main` function, and I do not expect it to change results here. I did not test that claim against an unpatched build.
- **Go 1.19 is not the toolchain GoBench targets.** Some programs (for example the one that failed on `net`) might behave differently on Linux or in the project's Docker image.

---

## 8. Conclusions and next steps

**On dingo-hunter.** It is a good *describer* of channel structure and a poor *detector* on this benchmark. About a third of GoKer has no channels, a third crashes (often on `context`, `select` or `close`), and a third gives usable models. Even among the usable ones, several bug classes are invisible because the bug lives in a lock.

**On the paper.** Its pattern vocabulary fits the channel-only GoBench bugs surprisingly well. The programs are built from IP-1, IP-3, IP-7 and IP-8, and most of the bugs can be phrased as a pattern whose soundness condition was broken. But the catalogue stops at message passing between a couple of agents. GoBench's other half (locks, `context`, broadcast by `close`, buffered semaphores) falls outside it.

**If I were taking this further:**

1. Install and run `gmc-synthesis` to get actual safe/unsafe verdicts on the 37 CFSM sets.
2. Teach the extractor to stop at the `context` package boundary, or model `ctx.Done()` as a closable channel. That alone would recover up to 11 crashed programs.
3. Add buffered-channel capacity to the model so that cases like cockroach #35073 stop being false alarms.
4. Run the same sweep on the Linux/Docker build GoBench itself targets.

---

## Appendix A. The 37 programs that produced CFSMs

| Bug | GoBench type | Channels | Goroutines | Patterns seen | Notable in the CFSM |
|---|---|---|---|---|---|
| cockroach #1462 | Channel & WaitGroup | 3 | 1 | none | none |
| cockroach #2448 | Channel | 3 | 2 | IP-1, IP-3, IP-7 | receive with no sender; fan-out |
| cockroach #24808 | Channel | 2 | 1 | none | send with no receiver (buffered chan) |
| cockroach #25456 | Channel | 1 | 1 | IP-7 | receive with no sender |
| cockroach #35073 | Channel | 1 | 2 | IP-3 | send with no receiver (buffered chan); fan-in |
| cockroach #35931 | Channel | 2 | 1 | none | send with no receiver (buffered chan) |
| etcd #6857 | Channel | 5 | 3 | IP-1, IP-3, IP-4, IP-8 | send with no receiver; receive with no sender; channel passed as a value |
| etcd #6873 | Channel & Lock | 2 | 3 | IP-1, IP-4, IP-7 | none |
| etcd #7443 | Channel & Lock | 3 | 3 | none | send with no receiver (buffered chan); receive with no sender |
| etcd #7902 | Channel & Lock | 1 | 0 | none | none |
| grpc #1460 | Channel & Lock | 1 | 2 | IP-1 | none |
| grpc #3017 | Double Locking | 1 | 2 | none | none |
| grpc #660 | Channel | 2 | 3 | IP-1, IP-3, IP-7, IP-8 | none |
| istio #16224 | Channel & Lock | 3 | 2 | IP-1, IP-3, IP-7 | receive with no sender |
| kubernetes #10182 | Channel & Lock | 1 | 3 | IP-1, IP-7 | fan-in |
| kubernetes #11298 | Channel & Condition Variable | 2 | 3 | none | none |
| kubernetes #26980 | Channel & Lock | 2 | 3 | IP-3 | none |
| kubernetes #38669 | Channel | 2 | 2 | IP-3, IP-7 | send with no receiver (buffered chan) |
| kubernetes #6632 | Channel & Lock | 2 | 3 | IP-1 | send with no receiver |
| kubernetes #70277 | Channel | 3 | 1 | none | receive with no sender |
| moby #27782 | Channel & Condition Variable | 3 | 1 | IP-3, IP-7 | send with no receiver; receive with no sender |
| moby #28462 | Channel & Lock | 1 | 2 | IP-1 | none |
| moby #29733 | Condition Variable | 2 | 2 | none | receive with no sender |
| moby #30408 | Condition Variable | 1 | 2 | none | none |
| moby #33293 | Channel | 1 | 1 | none | send with no receiver |
| moby #4395 | Channel | 1 | 1 | none | send with no receiver |
| serving #2137 | Channel & Lock | 5 | 2 | IP-3 | send with no receiver (buffered chan); receive with no sender |
| cockroach #4407 (NB) | WaitGroup | 1 | 1 | none | none |
| etcd #3077 (NB) | Misuse Channel | 4 | 3 | IP-1, IP-3 | receive with no sender |
| grpc #2371 (NB) | Misuse Channel | 1 | 1 | none | none |
| istio #8967 (NB) | Misuse Channel | 1 | 2 | none | none |
| kubernetes #13058 (NB) | WaitGroup | 1 | 2 | none | none |
| kubernetes #79631 (NB) | Data Race | 1 | 1 | IP-3 | receive with no sender |
| kubernetes #81148 (NB) | Data Race | 1 | 2 | IP-3 | none |
| kubernetes #82239 (NB) | Data Race | 1 | 2 | IP-3 | none |
| kubernetes #88331 (NB) | Data Race | 1 | 1 | IP-3 | receive with no sender |
| serving #6472 (NB) | Data Race | 2 | 1 | none | none |


## Appendix B. The 32 programs that crashed

| Bug | GoBench type | Why dingo-hunter stopped |
|---|---|---|
| cockroach #1055 | Channel & WaitGroup | receive on an unresolved channel |
| cockroach #10790 | Channel & Context | walked into Go's `context` package; `select` on an undefined channel |
| cockroach #13197 | Channel & Context | walked into Go's `context` package; `select` on an undefined channel |
| cockroach #13755 | Channel & Context | walked into Go's `context` package; `select` on an undefined channel |
| cockroach #18101 | Double Locking | walked into Go's `context` package; `select` on an undefined channel |
| etcd #5509 | Double Locking | walked into Go's `context` package; `select` on an undefined channel |
| etcd #7492 | Channel & Lock | `select` on a channel the extractor could not resolve |
| grpc #1275 | Channel | `select` on a channel the extractor could not resolve |
| grpc #1353 | Channel & Lock | `close()` applied to something it could not resolve to a channel |
| grpc #1424 | Channel | `close()` applied to something it could not resolve to a channel |
| grpc #862 | Channel & Context | walked into Go's `context` package; `select` on an undefined channel |
| istio #17860 | Channel | walked into Go's `context` package; `select` on an undefined channel |
| istio #18454 | Channel & Context | walked into Go's `context` package; `select` on an undefined channel |
| kubernetes #13135 | AB-BA Deadlock | nil-pointer crash inside dingo-hunter |
| kubernetes #1321 | Channel & Lock | `close()` applied to something it could not resolve to a channel |
| kubernetes #25331 | Channel & Context | walked into Go's `context` package; `select` on an undefined channel |
| kubernetes #30872 | AB-BA Deadlock | nil-pointer crash inside dingo-hunter |
| kubernetes #5316 | Channel | `select` on a channel the extractor could not resolve |
| kubernetes #58107 | RWR Deadlock | nil-pointer crash inside dingo-hunter |
| moby #17176 | Double Locking | `select` on a channel the extractor could not resolve |
| moby #21233 | Channel | `close()` applied to something it could not resolve to a channel |
| moby #33781 | Channel & Context | `select` on a channel the extractor could not resolve |
| moby #7559 | Double Locking | standard library `net` would not type-check (cgo) |
| syncthing #5795 | Channel | `select` on a channel the extractor could not resolve |
| etcd #8194 (NB) | Data Race | `select` on a channel the extractor could not resolve |
| grpc #1687 (NB) | Misuse Channel | does not compile as `main` (still uses `t *testing.T`) |
| kubernetes #70892 (NB) | Anonymous Function | `select` on a channel the extractor could not resolve |
| kubernetes #81091 (NB) | Data Race | `select` on a channel the extractor could not resolve |
| moby #18412 (NB) | Order Violation | `select` on a channel the extractor could not resolve |
| serving #3068 (NB) | Misuse Channel | does not compile as `main` (still uses `t *testing.T`) |
| serving #4908 (NB) | Testing Library | does not compile as `main` (still uses `t *testing.T`) |
| serving #6171 (NB) | Testing Library | does not compile as `main` (still uses `t *testing.T`) |


## Appendix C. The 34 programs that produced nothing

| Bug | GoBench type | Uses any channel? |
|---|---|---|
| cockroach #10214 | AB-BA Deadlock | no |
| cockroach #16167 | Double Locking | no |
| cockroach #3710 | RWR Deadlock | no |
| cockroach #584 | Double Locking | no |
| cockroach #6181 | RWR Deadlock | no |
| cockroach #7504 | AB-BA Deadlock | no |
| cockroach #9935 | Double Locking | no |
| etcd #10492 | Double Locking | no |
| etcd #6708 | Double Locking | no |
| grpc #795 | Double Locking | no |
| hugo #3251 | AB-BA Deadlock | no |
| hugo #5379 | Double Locking | yes |
| kubernetes #62464 | RWR Deadlock | no |
| moby #25384 | Misuse WaitGroup | no |
| moby #36114 | Double Locking | no |
| moby #4951 | AB-BA Deadlock | no |
| syncthing #4829 | Double Locking | no |
| cockroach #35501 (NB) | Anonymous Function | no |
| etcd #4876 (NB) | Data Race | no |
| etcd #9446 (NB) | Data Race | no |
| grpc #1748 (NB) | Data Race | no |
| grpc #3090 (NB) | Data Race | no |
| istio #16742 (NB) | Data Race | no |
| istio #8144 (NB) | Data Race | no |
| istio #8214 (NB) | Data Race | no |
| kubernetes #49404 (NB) | Data Race | no |
| kubernetes #77796 (NB) | Data Race | no |
| kubernetes #80284 (NB) | Data Race | no |
| kubernetes #82550 (NB) | Data Race | no |
| kubernetes #89164 (NB) | Data Race | no |
| moby #22941 (NB) | Anonymous Function | no |
| moby #27037 (NB) | Anonymous Function | no |
| serving #3148 (NB) | Data Race | no |
| serving #5865 (NB) | Misuse Channel | yes |

