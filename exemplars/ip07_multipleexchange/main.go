// IP-7 Multiple exchange (terminable): for{select{case <-done:...}} with context.
package main

import "context"

func main() {
	ctx, cancel := context.WithCancel(context.Background())
	data := make(chan int, 1)
	done := make(chan struct{}, 1)
	go func() {
		for {
			select {
			case <-ctx.Done():
				return
			case <-done:
				return
			case v := <-data:
				_ = v
			}
		}
	}()
	data <- 1
	data <- 2
	cancel()
	done <- struct{}{}
}
