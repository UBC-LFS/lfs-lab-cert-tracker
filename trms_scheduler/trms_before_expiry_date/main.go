package main

import (
	"fmt"
	"log"
	"slices"
	"strings"
	"trms_scheduler/utils"
)

/*
# Send for training records before the expiry date
- Check everyday at 9:00 AM
*/

func send30days(db utils.Database, allUsers map[int]map[string]interface{}) {
	DAYS := 30

	expiringTrainings, err := utils.GetExpiringTrainings(db, DAYS)
	if err != nil {
		log.Fatal(err)
	}

	users := make(map[string][]string)
	temp_pis := make(map[string][]map[string]interface{})

	for _, value := range expiringTrainings {
		user := allUsers[value.UserID]
		userName := fmt.Sprintf("%s %s|%s", user["first_name"], user["last_name"], user["email"])
		trainingInfo := utils.DisplayExpiryInfo(value.CertName, value.ExpiryDate)

		found := slices.Contains(users[userName], trainingInfo)
		if !found {
			users[userName] = append(users[userName], trainingInfo)
		}

		if value.SupervisorID.Valid {
			pi := allUsers[int(value.SupervisorID.Int64)]
			piName := fmt.Sprintf("%s %s|%s", pi["first_name"], pi["last_name"], pi["email"])

			item := map[string]interface{}{
				"user":     value.UserID,
				"area":     value.LabName,
				"training": trainingInfo,
			}

			temp_pis[piName] = append(temp_pis[piName], item)
		}
	}

	pis := make(map[string][]map[string]interface{})
	for pi, items := range temp_pis {
		trainings := make(map[string][]string)
		for _, item := range items {
			key := fmt.Sprintf("%s|%d", item["area"], item["user"])
			trainings[key] = append(trainings[key], item["training"].(string))
		}

		for key, value := range trainings {
			info := strings.Split(key, "|")
			areaName := info[0]
			userID_int := utils.StrToInt(info[1])

			user := allUsers[userID_int]
			userName := fmt.Sprintf("%s %s", user["first_name"], user["last_name"])

			item := map[string]interface{}{
				"area":      areaName,
				"user":      userName,
				"trainings": value,
			}
			pis[pi] = append(pis[pi], item)
		}
	}

	sendToUsers(users, DAYS)
	sendToPIs(pis, DAYS)
}

func sendToUsers(users map[string][]string, days int) {
	utils.SendToUsers(users, days, "before-expiry-date")
}

func sendToPIs(pis map[string][]map[string]interface{}, days int) {
	utils.SendToPIs(pis, days, "before-expiry-date")
}

func send15days(db utils.Database, allUsers map[int]map[string]interface{}) {
	DAYS := 15

	expiringTrainings, err := utils.GetExpiringTrainings(db, DAYS)
	if err != nil {
		log.Fatal(err)
	}

	users := make(map[string][]string)
	for _, value := range expiringTrainings {
		user := allUsers[value.UserID]
		userInfo := utils.DisplayUserInfo(user, "")

		trainingInfo := utils.DisplayExpiryInfo(value.CertName, value.ExpiryDate)

		found := slices.Contains(users[userInfo], trainingInfo)

		if !found {
			users[userInfo] = append(users[userInfo], trainingInfo)
		}
	}
	utils.SendToAdmins(db, users, DAYS, "before-expiry-date")
}

func main() {
	fmt.Println("Start - Before Expiry Date")

	var db utils.Database

	if err := db.Connect(utils.SSL_MODE); err != nil {
		log.Fatal(err)
	}
	defer db.Close()

	allUsers, _, err := db.GetUsers()
	if err != nil {
		log.Fatal(err)
	}

	send30days(db, allUsers)
	send15days(db, allUsers)
}
