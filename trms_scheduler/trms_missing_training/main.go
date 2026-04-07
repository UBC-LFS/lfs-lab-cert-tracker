package main

import (
	"fmt"
	"log"
	"slices"
	"sort"
	"strconv"
	"strings"
	"trms_scheduler/utils"
)

/*
# Send for Missing Training records
- Check on 1st Monday and 3rd Monday at 10:30 AM
*/

/* Users */
func sendToUsers(db utils.Database, allUsers map[int]map[string]interface{}) {
	fmt.Println("Start - Missing Training for Users")

	data, err := GetUsersWithMissingCerts(db)
	if err != nil {
		log.Fatal(err)
	}

	users := make(map[string][]string)
	for _, value := range data {
		user := allUsers[value.UserID]
		userName := utils.DisplayUserInfo(user, "")

		for _, cert := range value.MissingCerts {
			if !slices.Contains(users[userName], cert) {
				users[userName] = append(users[userName], cert)
			}
		}
		sort.Strings(users[userName])
	}

	if len(users) > 0 {
		// fmt.Println(len(users))
		utils.SendToUsers(users, 0, "missing")
	}
}

/* Supervisors */
func sendToPIs(db utils.Database, allUsers map[int]map[string]interface{}, allUsers_by_usernmae map[string]int) {
	fmt.Println("Start - Missing Training for Supervisors")

	data, err := GetSupervisorsWithMissingCerts(db)
	if err != nil {
		log.Fatal(err)
	}

	numPis := 0
	for piUsername, labs := range data {
		piID := allUsers_by_usernmae[piUsername]
		pi := allUsers[piID]

		var userLength int
		var areas []string
		for lab, items := range labs {
			userLength = len(items)
			areas = append(areas, "<div><strong>"+lab+"</strong> (Total: "+strconv.Itoa(userLength)+")<br />")

			var users []string
			for _, item := range items {
				users = append(users, "<li>"+item.LastName+", "+item.FirstName+"<br />")

				var certs []string
				for _, cert := range item.Certs {
					certs = append(certs, "<li>"+cert+"</li>")
				}
				users = append(users, "<ul>"+strings.Join(certs, "")+"</ul></li>")
			}
			areas = append(areas, "<ul>"+strings.Join(users, "")+"</ul></div>")
		}

		if userLength > 0 {
			message := "<p>Please be advised that the following users have missing required training certification(s) for your area. Kindly review the list and ensure appropriate actions are taken.</p>" + strings.Join(areas, "")
			body := utils.EmailTemplate(utils.DisplayUserInfo(pi, "no-email"), message)

			// fmt.Println(pi["email"], body)
			utils.SendEmail(pi["email"].(string), body)

			numPis++
		}
	}

	fmt.Println("Sent to PIs:", numPis)
}

func main() {
	fmt.Println("Start - Missing Training")

	var db utils.Database

	if err := db.Connect(utils.SSL_MODE); err != nil {
		log.Fatal(err)
	}
	defer db.Close()

	allUsers, allUsers_by_username, err := db.GetUsers()
	if err != nil {
		log.Fatal(err)
	}

	sendToUsers(db, allUsers)
	sendToPIs(db, allUsers, allUsers_by_username)
}
