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

	if err := db.Connect(utils.SSL_MODE); err != nil {
		log.Fatal(err)
	}
	defer db.Close()

	users, users_by_username, err := db.GetUsers()
	if err != nil {
		log.Fatal(err)
	}

	trainings_by_name, trainings_by_id, trainings_by_unique_id, err := db.GetTrainings()
	if err != nil {
		log.Fatal(err)
	}

	userTrainingKeys, err := GetUserTrainingKeys(db)
	if err != nil {
		log.Fatal(err)
	}

	usersWithMissingTrainings, _, err := GetUsersWithMissingTrainings(db)
	if err != nil {
		log.Fatal(err)
	}

	usersWithExpiredTrainings, err := GetUsersWithExpiredTrainings(db)
	if err != nil {
		log.Fatal(err)
	}

	keysA := GetKeys(usersWithMissingTrainings)
	keysB := GetKeys(usersWithExpiredTrainings)

	setA := ToSet(keysA)
	setB := ToSet(keysB)
	allUserIDs := Union(setA, setB)

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

					// Try to find trainings
					if foundTrainingID, ok := FindTraining(trainings_by_name, trainings_by_unique_id, trainingName, trainingID); ok {
						userID := users_by_username[username]

						// Check the found training in each user
						key := fmt.Sprintf("%d-%d-%s", userID, foundTrainingID, date)
						if !userTrainingKeys[key] {
							expiryDate := GetExpiryDate(completionDate, foundTrainingID, trainings_by_id)
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

// Utils

func GetKeys(items map[int][]string) []int {
	var keys []int
	for key := range items {
		if len(items[key]) > 0 {
			keys = append(keys, key)
		}
	}
	return keys
}

// Convert a slice to a set
func ToSet[T comparable](arr []T) map[T]struct{} {
	set := make(map[T]struct{})
	for _, v := range arr {
		set[v] = struct{}{}
	}
	return set
}

// Union of two sets
func Union[T comparable](a, b map[T]struct{}) map[T]struct{} {
	union := make(map[T]struct{})
	for k := range a {
		union[k] = struct{}{}
	}
	for k := range b {
		union[k] = struct{}{}
	}
	return union
}

func FindTraining(trainings_by_name map[string]map[string]interface{}, trainings_by_unique_id map[string]map[string]interface{}, training_name string, training_id string) (int, bool) {
	if training_name == "Chemical Safety" || training_name == "Chemical Safety Refresher" {
		training_name = "Chemical Safety/Chemical Safety Refresher"
	} else if training_name == "Biosafety for Study Team Members" || training_name == "Biosafety Refresher for Study Team Members" {
		training_name = "Biosafety for Study Team Members/Biosafety Refresher for Study Team Members"
	} else if training_name == "Biosafety for Permit Holders" || training_name == "Biosafety Refresher for Permit Holders" {
		training_name = "Biosafety for Permit Holders/Biosafety Refresher for Permit Holders"
	} else if training_name == "Transportation of Dangerous Goods by Ground and Air_ April 2020- March 7 2022" {
		training_name = "Transportation of Dangerous Goods by Ground and Air"
	} else if training_name == "Remote Work. Home Office Ergonomics. Orientation" {
		training_name = "Home Office Ergo"
	}

	// Try to find it by training name
	if training, ok := trainings_by_name[training_name]; ok {
		return int(training["id"].(int64)), true
	} else {
		// Try to find it by training id
		for key, value := range trainings_by_unique_id {
			for _, part := range strings.Split(key, ",") {
				if strings.TrimSpace(part) == training_id {
					return int(value["id"].(int64)), true
				}
			}
		}
	}

	return -1, false
}

func GetExpiryDate(completionDate string, traingID int, trainings map[int]map[string]interface{}) string {
	t, err := time.Parse(time.RFC3339, completionDate)
	if err != nil {
		fmt.Println("Error parsing date:", err)
		return ""
	}

	expiry_in_years := int(trainings[traingID]["expiry_in_years"].(int64))
	newTime := t.AddDate(expiry_in_years, 0, 0)
	newDateStr := newTime.Format("2006-01-02")
	return newDateStr
}
