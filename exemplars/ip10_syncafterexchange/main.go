// IP-10 Sync after exchange: buffered exchange, then UNBUFFERED done-signal.
package main

func main() {
	data := make(chan int, 1) // buffered: asynchronous exchange
	done := make(chan struct{}) // unbuffered: synchronous barrier (s)
	go func() {
		_ = <-data
		done <- struct{}{} // rendezvous after exchange
	}()
	data <- 9
	<-done
}
