// IP-9 Sync before exchange: UNBUFFERED rendezvous, then buffered exchange.
package main

func main() {
	sync := make(chan struct{}) // unbuffered: synchronous rendezvous (s)
	data := make(chan int, 1)   // buffered: asynchronous exchange
	go func() {
		sync <- struct{}{} // rendezvous
		data <- 7
	}()
	<-sync // rendezvous
	_ = <-data
}
