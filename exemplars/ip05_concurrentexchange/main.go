// IP-5 Concurrent exchange: worker pool, fan-out requests + collect replies.
package main

import "sync"

type job struct {
	n    int
	resp chan int
}

func main() {
	jobs := make(chan job, 4)
	var wg sync.WaitGroup
	for w := 0; w < 2; w++ {
		go func() {
			for j := range jobs {
				j.resp <- j.n * j.n
			}
		}()
	}
	for i := 0; i < 4; i++ {
		wg.Add(1)
		j := job{n: i, resp: make(chan int, 1)}
		jobs <- j
		go func() { defer wg.Done(); _ = <-j.resp }()
	}
	wg.Wait()
	close(jobs)
}
