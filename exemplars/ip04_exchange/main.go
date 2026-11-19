// IP-4 Exchange: request struct carrying a reply channel, buffered.
package main

type request struct {
	payload int
	resp    chan int
}

func main() {
	reqs := make(chan request, 1)
	go func() {
		r := <-reqs
		r.resp <- r.payload * 2
	}()
	r := request{payload: 21, resp: make(chan int, 1)}
	reqs <- r
	_ = <-r.resp
}
