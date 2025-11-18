package main

import (
	"fmt"
	"log"
	"strconv"
	"strings"
	"trms_scheduler/utils"
)

/*
# Change the SSL mode in production
- DEV = disable
- PROD = require
*/

var SSL_MODE = "disable"

func main() {
	fmt.Println("Start - Missing Training")

	var db utils.Database

	if err := db.Connect(SSL_MODE); err != nil {
		log.Fatal(err)
	}
	defer db.Close()

	allUsers, _, err := db.GetUsers()
	if err != nil {
		log.Fatal(err)
	}

	usersWithMissingCerts, err := GetUsersWithMissingCerts(db)
	if err != nil {
		log.Fatal(err)
	}

	users := make(map[string][]string)
	pis := make(map[string][]map[string]interface{})

	for _, value := range usersWithMissingCerts {
		user := allUsers[value.UserID]
		userName := fmt.Sprintf("%s %s|%s", user["first_name"], user["last_name"], user["email"])
		users[userName] = append(users[userName], value.MissingCerts...)

		for _, piID := range value.Supervisors {
			piID_int, err := strconv.Atoi(piID)
			if err != nil {
				log.Fatalf("Error converting string to int: %v", err)
			}

			pi := allUsers[piID_int]
			piName := fmt.Sprintf("%s %s|%s", pi["first_name"], pi["last_name"], pi["email"])

			temp := map[string]interface{}{
				"area":      value.LabName,
				"user":      fmt.Sprintf("%s %s", user["first_name"], user["last_name"]),
				"trainings": value.MissingCerts,
			}
			pis[piName] = append(pis[piName], temp)
		}
	}

	sendToUsers(users)
	sendToPIs(pis)
}

func sendToUsers(users map[string][]string) {
	for key, value := range users {
		userInfo := strings.Split(key, "|")
		recipientName := userInfo[0]
		recipientEmail := userInfo[1]

		var trainings []string
		for _, training := range value {
			trainings = append(trainings, "<li>"+training+"</li>")
		}

		content := "<p>Our records indicate that you have missing training certification(s) required for each area. Please take a moment to update your records at your earliest convenience. Let us know if you need any assistance.</p>" +
			"<ul>" + strings.Join(trainings, "") + "</ul>"

		body := utils.EmailTemplate(recipientName, content)

		fmt.Println(recipientEmail, body)
		// utils.SendEmail(recipientEmail, body)
	}
}

func sendToPIs(pis map[string][]map[string]interface{}) {
	for key, value := range pis {
		userInfo := strings.Split(key, "|")
		recipientName := userInfo[0]
		recipientEmail := userInfo[1]

		var items string
		for _, item := range value {
			items += "<li>" + item["area"].(string) + ": " + item["user"].(string) + "</li>"

			var trainings []string
			for _, training := range item["trainings"].([]string) {
				trainings = append(trainings, "<li>"+training+"</li>")
			}
			items += "<ul>" + strings.Join(trainings, "") + "</ul>"
		}

		content := "<p>Please be advised that the following users have missing required training certification(s) for your area. Kindly review the list and ensure appropriate actions are taken.</p>" +
			"<ul>" + items + "</ul>"

		body := utils.EmailTemplate(recipientName, content)

		fmt.Println(recipientEmail, body)
		// utils.SendEmail(recipientEmail, body)
	}
}
