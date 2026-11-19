// IP-8 Racing incoming: one goroutine selects recv from >=3 channels.
package main

func main() {
	a := make(chan int, 1)
	b := make(chan int, 1)
	c := make(chan int, 1)
	go func() { a <- 1 }()
	select {
	case <-a:
	case <-b:
	case <-c:
	}
}
