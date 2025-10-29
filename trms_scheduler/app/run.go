package app

import (
	"fmt"
	"log"
	"trms_scheduler/utils"
)

func Run(ssl_mode string) {
	var db utils.Database
	if err := db.Connect(ssl_mode); err != nil {
		log.Fatal(err)
	}
	defer db.Close()

	data, err := db.QueryData(utils.USERS)
	if err != nil {
		log.Fatal(err)
	}

	for _, row := range data {
		fmt.Println(row)
	}
}
