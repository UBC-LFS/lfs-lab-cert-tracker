package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"strconv"
	"strings"
	"time"
	"trms_scheduler/utils"
)

/*
# How to run this app
$ go run ./update_by_api


# Change the SSL mode in production
- DEV = disable
- PROD = verify-full
*/

var SSL_MODE = "disable"

type TrainingModel struct {
	UserID         int
	TrainingID     int
	CompletionDate string
	ExpiryDate     string
	UploadedDate   string
	CertFile       string
	ByApi          bool
}

func main() {
	fmt.Println("Start - Update by API")

	var db utils.Database
	if err := db.Connect(SSL_MODE); err != nil {
		log.Fatal(err)
	}
	defer db.Close()

	users, users_by_username, err := db.GetUsers()
	if err != nil {
		log.Fatal(err)
	}

	trainings, trainings_by_unique_id, err := db.GetTrainings()
	if err != nil {
		log.Fatal(err)
	}

	userTrainingKeys, err := db.GetUserTrainingKeys()
	if err != nil {
		log.Fatal(err)
	}

	usersWithMissingTrainings, _, err := db.GetUsersWithMissingTrainings()
	if err != nil {
		log.Fatal(err)
	}

	usersWithExpiredTrainings, err := db.GetUsersWithExpiredTrainings()
	if err != nil {
		log.Fatal(err)
	}

	keysA := getKeys(usersWithMissingTrainings)
	keysB := getKeys(usersWithExpiredTrainings)

	setA := toSet(keysA)
	setB := toSet(keysB)
	allUserIDs := union(setA, setB)

	var usernames []string
	for userID := range allUserIDs {
		usernames = append(usernames, users[userID]["username"].(string))
	}

	fmt.Println("The number of users:", len(usernames))

	groupSize := 5
	var groups [][]string

	for i := 0; i < len(usernames); i += groupSize {
		end := i + groupSize
		if end > len(usernames) {
			end = len(usernames)
		}
		groups = append(groups, usernames[i:end])
	}

	now := time.Now()
	today := now.Format("2006-01-02")

	var trainingModels []TrainingModel
	for _, group := range groups {
		// fmt.Printf("Group %d: %v\n", i+1, group)

		var requestIdentifiers []map[string]string
		for _, g := range group {
			temp := make(map[string]string)
			temp["identifierType"] = "CWL"
			temp["identifier"] = g
			requestIdentifiers = append(requestIdentifiers, temp)
		}

		page := 1
		hasNextPage := true
		for hasNextPage {
			apiURL := fmt.Sprintf("%s?page=%d&pageSize=%d", os.Getenv("LFS_LAB_CERT_TRACKER_API_URL"), page, 50)

			payload := map[string][]map[string]string{
				"requestIdentifiers": requestIdentifiers,
			}

			jsonData, err := json.Marshal(payload)
			if err != nil {
				log.Fatal(err)
			}

			req, err := http.NewRequest("POST", apiURL, bytes.NewBuffer(jsonData))
			if err != nil {
				log.Fatal(err)
			}
			req.Header.Set("Content-Type", "application/json")
			req.Header.Set("X-Client-Id", os.Getenv("LFS_LAB_CERT_TRACKER_CLIENT_ID"))
			req.Header.Set("X-Client-Secret", os.Getenv("LFS_LAB_CERT_TRACKER_CLIENT_SECRET"))

			client := &http.Client{}
			res, err := client.Do(req)
			if err != nil {
				log.Fatal(err)
			}
			defer res.Body.Close()

			body, err := io.ReadAll(res.Body)
			if err != nil {
				log.Fatal(err)
			}

			var data map[string]interface{}
			json.Unmarshal(body, &data)

			hasNextPage = data["hasNextPage"].(bool)
			page = int(data["page"].(float64)) + 1

			for _, item := range data["pageItems"].([]interface{}) {
				var username string
				var status string
				var trainingID float64
				var trainingName string
				var completionDate string
				if subitem, ok := item.(map[string]interface{}); ok {
					if reqId, ok := subitem["requestedIdentifier"]; ok {
						username = reqId.(map[string]interface{})["identifier"].(string)
					}

					if reqId, ok := subitem["certificate"]; ok {
						status = reqId.(map[string]interface{})["status"].(string)
						trainingID = reqId.(map[string]interface{})["trainingId"].(float64)
						trainingName = strings.TrimSpace(reqId.(map[string]interface{})["trainingName"].(string))
						completionDate = reqId.(map[string]interface{})["completionDate"].(string)
					}
				}

				if status == "active" && trainingID != 0 && len(trainingName) > 0 && len(completionDate) > 0 {
					t, err := time.Parse(time.RFC3339, completionDate)
					if err != nil {
						log.Fatal(err)
					}

					date := t.Format("2006-01-02")
					trainingID := strconv.FormatFloat(trainingID, 'f', -1, 64)

					if foundTrainingID, ok := findValue(trainings_by_unique_id, trainingID); ok {
						userID := users_by_username[username]
						key := fmt.Sprintf("%d-%d-%s", userID, foundTrainingID, date)
						if !userTrainingKeys[key] {
							expiryDate := getExpiryDate(completionDate, foundTrainingID, trainings)
							trainingModels = append(trainingModels, TrainingModel{
								userID,
								foundTrainingID,
								date,
								expiryDate,
								today,
								"None",
								true,
							})
						}
					}
				}
			}
		}
	}

	fmt.Println("The number of trainings to be updated:", len(trainingModels))

	if len(trainingModels) > 0 {
		values := []string{}
		for _, t := range trainingModels {
			values = append(values, fmt.Sprintf("(%d,%d,'%s','%s','%s','%s',%t)", t.UserID, t.TrainingID, t.CompletionDate, t.ExpiryDate, t.UploadedDate, t.CertFile, t.ByApi))
		}

		query := fmt.Sprintf("INSERT INTO lfs_lab_cert_tracker_usercert (user_id, cert_id, completion_date, expiry_date, uploaded_date, cert_file, by_api) VALUES %s", strings.Join(values, ","))

		_, err = db.Conn.Exec(query)
		if err != nil {
			log.Fatal("Bulk insert failed:", err)
		}

		fmt.Println("Bulk insert completed successfully!")
	}
	fmt.Println("Done!")
}
