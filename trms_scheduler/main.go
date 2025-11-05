package main

import "trms_scheduler/app"

/*
# Change the SSL mode in production
- DEV = disable
- PROD = verify-full
*/

var SSL_MODE = "disable"

func main() {
	app.Run(SSL_MODE)
}
