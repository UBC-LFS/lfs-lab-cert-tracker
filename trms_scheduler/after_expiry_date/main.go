package main

import (
	"fmt"
	"log"
	"trms_scheduler/utils"
)

func send15days(db utils.Database, allUsers map[int]map[string]interface{}) {
	expiredTrainings, err := utils.GetExpiredTrainings(db)
	if err != nil {
		log.Fatal(err)
	}

	users, pis := utils.GetUsersAndPIsForExpiryDate(expiredTrainings, allUsers)

	sendToUsers(users)
	sendToPIs(pis)
	sendToAdmins(db, users)
}

func sendToUsers(users map[string][]string) {
	utils.SendToUsers(users, 0, "after-expiry-date")
}

func sendToPIs(pis map[string][]map[string]interface{}) {
	utils.SendToPIs(pis, 0, "after-expiry-date")
}

func sendToAdmins(db utils.Database, users map[string][]string) {
	utils.SendToAdmins(db, users, 0, "after-expiry-date")
}

func main() {
	fmt.Println("Start - After Expiry Date")

	var db utils.Database

	if err := db.Connect(utils.SSL_MODE); err != nil {
		log.Fatal(err)
	}
	defer db.Close()

	allUsers, _, err := db.GetUsers()
	if err != nil {
		log.Fatal(err)
	}

	send15days(db, allUsers)
}
