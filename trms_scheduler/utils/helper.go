package utils

import (
	"fmt"
	"log"
	"net/smtp"
	"os"
	"slices"
	"strconv"
	"strings"
	"time"
)

/*
# Change the SSL mode in production
- DEV = disable
- PROD = require
*/

var SSL_MODE = os.Getenv("LFS_LAB_CERT_TRACKER_SCHEDULER_SSL_MODE")

func GetUsersAndPIsForExpiryDate(data []ExpirySearchResult, allUsers map[int]map[string]interface{}) (map[string][]string, map[string][]map[string]interface{}) {
	users := make(map[string][]string)
	temp_pis := make(map[string][]map[string]interface{})

	for _, value := range data {
		user := allUsers[value.UserID]
		userName := DisplayUserInfo(user, "")
		trainingInfo := DisplayExpiryInfo(value.CertName, value.ExpiryDate)

		found := slices.Contains(users[userName], trainingInfo)
		if !found {
			users[userName] = append(users[userName], trainingInfo)
		}

		if value.SupervisorID.Valid {
			pi := allUsers[int(value.SupervisorID.Int64)]
			piName := DisplayUserInfo(pi, "")

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
			key := CombineAreaAndUser(item["area"].(string), item["user"].(int))
			trainings[key] = append(trainings[key], item["training"].(string))
		}

		for key, value := range trainings {
			info := strings.Split(key, "|")
			areaName := info[0]
			userID_int := StrToInt(info[1])

			user := allUsers[userID_int]
			userName := DisplayUserInfo(user, "no-email")

			item := map[string]interface{}{
				"area":      areaName,
				"user":      userName,
				"trainings": value,
			}
			pis[pi] = append(pis[pi], item)
		}
	}
	return users, pis
}

/* Email */

func EmailTemplate(recipientName string, content string) string {
	body := "<p>Hi " + recipientName + ",</p>" +
		content +
		"<p>To enroll in a missing or expired training, please visit the below link and select the category that best describes your LFS affiliation for training links.<p/>" +
		"<p><b>UBC/LFS Mandatory Training</b><br /><a href='https://my.landfood.ubc.ca/lfs-intranet/onboarding/lfs-mandatory-training/'>https://my.landfood.ubc.ca/lfs-intranet/onboarding/lfs-mandatory-training/</a></p>" +
		"<p>Best regards,</p><p>LFS Training Record Management System</p>"

	return body
}

func SendEmail(recipient string, body string) {
	host := os.Getenv("LFS_LAB_CERT_TRACKER_EMAIL_HOST")
	port := "25"
	sender := os.Getenv("LFS_LAB_CERT_TRACKER_EMAIL_FROM")
	subject := "Training Record Notification at UBC LFS"

	msg := []byte("To: " + recipient + "\r\n" +
		"From: " + sender + "\r\n" +
		"Subject: " + subject + "\r\n" +
		"MIME-Version: 1.0\r\n" +
		"Content-Type: text/html; charset=\"UTF-8\"\r\n" +
		"\r\n" +
		"<html><body>" +
		body +
		"</body></html>\r\n")

	err := smtp.SendMail(host+":"+port, nil, sender, []string{recipient}, msg)
	if err != nil {
		fmt.Println("Error sending to", recipient, ":", err)
	} else {
		// fmt.Println("Email sent to", recipient)
	}
}

func SendToUsers(users map[string][]string, days int, path string) {
	for key, value := range users {
		recipientName, recipientEmail := SplitUserInfo(key)

		var trainings []string
		for _, training := range value {
			trainings = append(trainings, "<li>"+training+"</li>")
		}
		slices.Sort(trainings)

		var content string
		if path == "missing" {
			content = "<p>Our records indicate that you have missing training certification(s) required for each area. Please take a moment to update your records at your earliest convenience. Let us know if you need any assistance.</p>" +
				"<ul>" + strings.Join(trainings, "") + "</ul>"
		} else if path == "before-expiry-date" {
			content = "<p>This is a friendly reminder that one or more of your trainings will expire in " + IntToStr(days) + " days. Please update these certificates at your earliest convenience.</p>" +
				"<ul>" + strings.Join(trainings, "") + "</ul>"
		} else if path == "after-expiry-date" {
			content = "<p>This is a friendly reminder that the below training record(s) have expired. Please re-take the training(s) to meet the training requirement(s).</p>" +
				"<ul>" + strings.Join(trainings, "") + "</ul>"
		}

		body := EmailTemplate(recipientName, content)
		// fmt.Println(recipientEmail, body)
		SendEmail(recipientEmail, body)
	}
	fmt.Println("Sent to Users:", len(users))
}

func SendToPIs(pis map[string][]map[string]interface{}, days int, path string) {
	for key, value := range pis {
		recipientName, recipientEmail := SplitUserInfo(key)

		var items string
		for _, item := range value {
			items += "<li>" + item["area"].(string) + ": <strong>" + item["user"].(string) + "</strong></li>"

			var trainings []string
			for _, training := range item["trainings"].([]string) {
				trainings = append(trainings, "<li>"+training+"</li>")
			}
			slices.Sort(trainings)
			items += "<ul>" + strings.Join(trainings, "") + "</ul>"
		}

		var content string
		if path == "before-expiry-date" {
			content = "<p>Please be advised that the training certifications for the following users in your area will expire in " + IntToStr(days) + " days. Please remind these individuals to complete the necessary renewal process before their certifications expire.</p>" +
				"<ul>" + items + "</ul>"
		} else if path == "after-expiry-date" {
			content = "<p>Please be advised that the training certifications for the following users in your area have already expired. Please remind them to complete their renewal at the earliest convenience to prevent any area access issues.</p>" +
				"<ul>" + items + "</ul>"
		}

		body := EmailTemplate(recipientName, content)
		// fmt.Println(recipientEmail, body)
		SendEmail(recipientEmail, body)
	}

	fmt.Println("Sent to PIs:", len(pis))
}

func SendToAdmins(db Database, users map[string][]string, days int, path string) {
	admins, err := db.GetAdmins()
	if err != nil {
		log.Fatal(err)
	}

	var items string
	for key, trainings := range users {
		userName, _ := SplitUserInfo(key)

		var temp []string
		for _, training := range trainings {
			temp = append(temp, "<li>"+training+"</li>")
		}

		slices.Sort(temp)
		items += "<li><strong>" + userName + "</strong><ul>" + strings.Join(temp, "") + "</ul></li>"
	}

	var content string
	if path == "before-expiry-date" {
		content = "<p>Please be advised that the training certifications for the following users in your area will expire in " + IntToStr(days) + " days. Please remind these individuals to complete the necessary renewal process before their certifications expire.</p>" +
			"<ul>" + items + "</ul>"
	} else if path == "after-expiry-date" {
		content = "<p>Please be advised that the training certifications for the following users in your area have already expired. Please remind them to complete their renewal at the earliest convenience to prevent any area access issues.</p>" +
			"<ul>" + items + "</ul>"
	}

	for _, admin := range admins {
		recipientName := DisplayUserInfo(admin, "no-email")
		recipientEmail := admin["email"].(string)

		body := EmailTemplate(recipientName, content)
		// fmt.Println(recipientEmail, body)
		SendEmail(recipientEmail, body)
	}

	fmt.Println("Sent to Admins:", len(admins))
}

// For API Update

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

func FindValue(m map[string]int, target string) (int, bool) {
	for key, val := range m {
		for _, part := range strings.Split(key, ",") {
			if strings.TrimSpace(part) == target {
				return val, true
			}
		}
	}
	return 0, false
}

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

/* Utils */

func GetDate(datetime time.Time) string {
	return fmt.Sprintf("%d-%02d-%02d", datetime.Year(), datetime.Month(), datetime.Day())
}

func IntToStr(num int) string {
	return strconv.Itoa(num)
}

func StrToInt(num string) int {
	num_int, err := strconv.Atoi(num)
	if err != nil {
		log.Fatalf("Error converting string to int: %v", err)
	}
	return num_int
}

func SplitUserInfo(info string) (string, string) {
	userInfo := strings.Split(info, "|")
	return userInfo[0], userInfo[1]
}

func DisplayExpiryInfo(name string, expiryDate time.Time) string {
	return fmt.Sprintf("%s (Expiry Date: %s)", name, GetDate(expiryDate))
}

func DisplayUserInfo(user map[string]interface{}, option string) string {
	if option == "no-email" {
		return fmt.Sprintf("%s %s", user["first_name"], user["last_name"])
	}
	return fmt.Sprintf("%s %s|%s", user["first_name"], user["last_name"], user["email"])
}

func CombineAreaAndUser(area string, user int) string {
	return fmt.Sprintf("%s|%d", area, user)
}
