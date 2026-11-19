// IP-6 Alternative exchange: select over alternative req/reply channels.
package main

func main() {
	reqA := make(chan int, 1)
	reqB := make(chan int, 1)
	resp := make(chan int, 1)
	go func() {
		select {
		case v := <-reqA:
			resp <- v + 1
		case v := <-reqB:
			resp <- v + 2
		}
	}()
	reqA <- 10
	_ = <-resp
}
