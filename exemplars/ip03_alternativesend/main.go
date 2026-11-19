// IP-3 Alternative send: select with send cases, buffered.
package main

func main() {
	a := make(chan int, 1)
	b := make(chan int, 1)
	select {
	case a <- 1:
	case b <- 2:
	}
	select {
	case <-a:
	case <-b:
	}
}
