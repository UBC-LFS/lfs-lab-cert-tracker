package main

import (
	"fmt"
	"log"
	"trms_scheduler/utils"
)

/*
# Send for Missing Training records
- Check on 1st Monday and 3rd Monday at 10:30 AM
*/

func sendToUsers(users map[string][]string) {
	utils.SendToUsers(users, 0, "missing")
}

func sendToPIs(pis map[string][]map[string]interface{}) {
	utils.SendToPIs(pis, 0, "missing")
}

func main() {
	fmt.Println("Start - Missing Training")

	var db utils.Database

	if err := db.Connect(utils.SSL_MODE); err != nil {
		log.Fatal(err)
	}
	defer db.Close()

	allUsers, _, err := db.GetUsers()
	if err != nil {
		log.Fatal(err)
	}

	usersWithMissingCerts, err := utils.GetUsersWithMissingCerts(db)
	if err != nil {
		log.Fatal(err)
	}

	users := make(map[string][]string)
	pis := make(map[string][]map[string]interface{})

	for _, value := range usersWithMissingCerts {
		user := allUsers[value.UserID]
		userName := utils.DisplayUserInfo(user, "")
		users[userName] = append(users[userName], value.MissingCerts...)

		for _, piID := range value.Supervisors {
			piID_int := utils.StrToInt(piID)
			pi := allUsers[piID_int]
			piName := utils.DisplayUserInfo(pi, "")

			item := map[string]interface{}{
				"area":      value.LabName,
				"user":      utils.DisplayUserInfo(pi, "no-email"),
				"trainings": value.MissingCerts,
			}
			pis[piName] = append(pis[piName], item)
		}
	}

	sendToUsers(users)
	sendToPIs(pis)
}
