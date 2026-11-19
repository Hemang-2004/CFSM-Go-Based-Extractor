// IP-12 Sync or exchange: select mixing one UNBUFFERED and one buffered case.
package main

func main() {
	rendezvous := make(chan struct{}) // unbuffered: synchronous (s)
	data := make(chan int, 1)         // buffered: asynchronous
	go func() { data <- 3 }()
	select {
	case rendezvous <- struct{}{}: // sync path
	case v := <-data: // async path
		_ = v
	}
}
