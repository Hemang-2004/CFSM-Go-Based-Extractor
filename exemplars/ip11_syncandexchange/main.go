// IP-11 Sync and exchange: UNBUFFERED sync concurrent with buffered message.
package main

import "sync"

func main() {
	rendezvous := make(chan struct{}) // unbuffered: synchronous (s)
	data := make(chan int, 1)         // buffered: asynchronous
	var wg sync.WaitGroup
	wg.Add(1)
	go func() {
		defer wg.Done()
		rendezvous <- struct{}{} // sync branch
		data <- 5                // data branch, concurrent
	}()
	<-rendezvous
	_ = <-data
	wg.Wait()
}
