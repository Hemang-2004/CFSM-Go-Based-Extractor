// IP-1 Send/Receive: buffered one-way, no reply.
package main

func main() {
	ch := make(chan int, 1)
	go func() { ch <- 42 }()
	_ = <-ch
}
