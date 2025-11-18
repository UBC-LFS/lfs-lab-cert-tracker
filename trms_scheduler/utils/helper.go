package utils

import (
	"fmt"
	"net/smtp"
	"os"
	"strings"
	"time"
)

func EmailTemplate(recipientName string, content string) string {
	body := "<p>Hi " + recipientName + ",</p>" +
		content +
		"<p>To enroll in a missing or expired  training, please visit the below link and select the category that best describes your LFS affiliation for training links.<p/>" +
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
		fmt.Println("Email sent to", recipient)
	}
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
