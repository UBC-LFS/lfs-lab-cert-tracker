package app

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"strings"
	"time"
	"trms_scheduler/utils"
)

func Update_by_API(ssl_mode string) {
	var db utils.Database
	if err := db.Connect(ssl_mode); err != nil {
		log.Fatal(err)
	}
	defer db.Close()

	usersWithMissingCerts, _, err := db.GetUsersWithMissingCerts()
	if err != nil {
		log.Fatal(err)
	}

	usersWithExpiredCerts, _, err := db.GetUsersWithExpiredCerts()
	if err != nil {
		log.Fatal(err)
	}

	keysA := getKeys(usersWithMissingCerts)
	keysB := getKeys(usersWithExpiredCerts)

	setA := toSet(keysA)
	setB := toSet(keysB)
	allUserIDs := union(setA, setB)

	users, err := db.GetUsers()
	if err != nil {
		log.Fatal(err)
	}
	var usernames []string
	for userID := range allUserIDs {
		usernames = append(usernames, users[userID]["username"].(string))
	}
	fmt.Println(usernames)

	groupSize := 5
	var groups [][]string

	for i := 0; i < len(usernames); i += groupSize {
		end := i + groupSize
		if end > len(usernames) {
			end = len(usernames)
		}
		groups = append(groups, usernames[i:end])
	}

	for i, group := range groups {
		fmt.Printf("Group %d: %v\n", i+1, group)

		var requestIdentifiers []map[string]string
		for _, g := range group {
			temp := make(map[string]string)
			temp["identifierType"] = "CWL"
			temp["identifier"] = g
			requestIdentifiers = append(requestIdentifiers, temp)
		}

		fmt.Println(requestIdentifiers)

		page := 1
		hasNextPage := true
		for hasNextPage {
			fmt.Println(page, hasNextPage)
			apiURL := fmt.Sprintf("%s?page=%d&pageSize=%d", os.Getenv("LFS_LAB_CERT_TRACKER_API_URL"), page, 20)

			payload := map[string][]map[string]string{
				"requestIdentifiers": requestIdentifiers,
			}

			// Convert payload to JSON
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
			fmt.Println("Status:", res.Status)
			fmt.Printf("type %T\n", body)

			var data map[string]interface{}
			json.Unmarshal(body, &data)

			hasNextPage = data["hasNextPage"].(bool)
			page = int(data["page"].(float64)) + 1
			fmt.Println("here ==", page, hasNextPage)
			// fmt.Println(data["pageItems"])
			// fmt.Printf("type %T\n", data["pageItems"])

			for j, item := range data["pageItems"].([]interface{}) {
				fmt.Println(j)

				var status string
				var trainingID string
				var trainingName string
				var completionDate string
				if subitem, ok := item.(map[string]interface{}); ok {
					if reqId, ok := subitem["requestedIdentifier"]; ok {
						fmt.Println(reqId.(map[string]interface{})["identifier"])
					}

					if reqId, ok := subitem["certificate"]; ok {
						status = reqId.(map[string]interface{})["status"].(string)
						trainingID = strings.TrimSpace(reqId.(map[string]interface{})["trainingId"].(string))
						trainingName = strings.TrimSpace(reqId.(map[string]interface{})["trainingName"].(string))
						completionDate = reqId.(map[string]interface{})["completionDate"].(string)
					}
				}

				if status == "active" && len(trainingID) > 0 && len(trainingName) > 0 && len(completionDate) > 0 {
					t, err := time.Parse(time.RFC3339, completionDate)
					if err != nil {
						log.Fatal(err)
					}
					date := t.Format("2006-01-02")
					fmt.Println(status, trainingName, date)
				} else {
					log.Fatal("Warning: No status, trainingName or completionDate.")
				}

			}
		}
	}
}

func getKeys(items map[int][]string) []int {
	var keys []int
	for key := range items {
		if len(items[key]) > 0 {
			keys = append(keys, key)
		}
	}
	return keys
}

// Convert a slice to a set
func toSet[T comparable](arr []T) map[T]struct{} {
	set := make(map[T]struct{})
	for _, v := range arr {
		set[v] = struct{}{}
	}
	return set
}

// Union of two sets
func union[T comparable](a, b map[T]struct{}) map[T]struct{} {
	union := make(map[T]struct{})
	for k := range a {
		union[k] = struct{}{}
	}
	for k := range b {
		union[k] = struct{}{}
	}
	return union
}
