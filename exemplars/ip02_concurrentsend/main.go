// IP-2 Concurrent send: N senders -> one channel (fan-in), buffered.
package main

import "sync"

func main() {
	ch := make(chan int, 3)
	var wg sync.WaitGroup
	for i := 0; i < 3; i++ {
		wg.Add(1)
		go func(v int) { defer wg.Done(); ch <- v }(i)
	}
	go func() { wg.Wait(); close(ch) }()
	for range ch {
	}
}
