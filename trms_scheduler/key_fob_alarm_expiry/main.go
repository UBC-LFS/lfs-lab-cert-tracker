package main

import (
	"fmt"
	"log"
	"net/smtp"
	"os"
	"strings"
	"trms_scheduler/utils"
)

var FormUserMap = make(map[int]FormUser)
var RoomMap = make(map[int]Room)

func makeRoomString(room Room) string {
	return fmt.Sprintf("%s %s - Room %s", room.building, room.floor, room.number)
}

func determineAlerts(statusMap map[int]map[int]map[RoomEntity]KeyRequestStatusResult, roomApproverMap map[int]int) map[int][]int {
	needsUpdate := make(map[int][]int)

	for formID, roomEntityStatuses := range statusMap {

		for roomID, roomEntity := range roomEntityStatuses {

			approverCount := 0

			for _, status := range roomEntity {
				if status.status >= Approved {
					approverCount++
				}
			}

			if approverCount == roomApproverMap[roomID] {

				roomIDs, exists := needsUpdate[formID]
				if !exists {
					roomIDs = []int{}
				}

				roomIDs = append(roomIDs, roomID)
				needsUpdate[formID] = roomIDs
			}

		}

	}
	return needsUpdate
}

func getExpiryItemString(option Option) string {
	if option == Key {
		return "Key"
	} else if option == FOB {
		return "FOB"
	} else if option == Alarm {
		return "Alarm Code"
	}

	return "" // Leave blank

}

func expiryEmailTemplate(recipientName string, rooms []int, option Option) string {
	var roomsBulletList strings.Builder
	roomsBulletList.WriteString("<ul>")

	for _, roomID := range rooms {
		roomString := makeRoomString(RoomMap[roomID])
		roomsBulletList.WriteString(fmt.Sprintf("<li>%s</li>", roomString))

	}
	roomsBulletList.WriteString("</ul>")

	expiryItem := strings.ToLower(getExpiryItemString(option))

	body := "<p>Hi " + recipientName + ",</p>" +
		"<p>Your " +
		expiryItem +
		"(s) for the following rooms will expire in 2 weeks.</p>" +
		roomsBulletList.String() +
		"<p>If you need to extend your access, please fill out Access Request via TRMS. Otherwise, you should return your key(s) to UBC Keydesk to avoid penalty.<p/>" +
		"<p>If you require further assistance, please email <a href=\"mailto:lfs.access@ubc.ca\">lfs.access@ubc.ca.</a></p>" +
		"<p>Best regards,</p><p>LFS Training Record Management System</p>"

	return body

}

func sendExpiryEmail(recipient string, option Option, body string) {
	host := os.Getenv("LFS_LAB_CERT_TRACKER_EMAIL_HOST")
	port := "25"
	sender := os.Getenv("LFS_LAB_CERT_TRACKER_EMAIL_FROM")

	expiryOption := getExpiryItemString(option)

	subject := fmt.Sprintf("Two-Week %s Expiry Notification at UBC LFS", expiryOption)

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

func sendEmails(formRoomMap map[int][]int, option Option) {

	for formID, rooms := range formRoomMap {

		formUser, exists := FormUserMap[formID]

		if !exists {
			fmt.Println("Error sending email. Could not find form with id: ", formID)
			continue
		}

		content := expiryEmailTemplate(formUser.firstName, rooms, option)

		sendExpiryEmail(formUser.email, option, content)

	}

}

func main() {

	var db utils.Database

	if err := db.Connect(utils.SSL_MODE); err != nil {
		log.Fatal(err)
	}

	roomApproverMap, err := GetApprovalEntityMapping(db)

	if err != nil {
		log.Fatal(err)
	}

	statusMap, err := GetKRForFobTwoWeeks(db)

	if err != nil {
		log.Fatal(err)
	}

	// form: [rooms]
	fobUpdates := determineAlerts(statusMap, roomApproverMap)
	sendEmails(fobUpdates, FOB)

	statusMap, err = GetKRForAlarmTwoWeeks(db)

	if err != nil {
		log.Fatal(err)
	}

	// form: [rooms]
	alarmUpdates := determineAlerts(statusMap, roomApproverMap)
	sendEmails(alarmUpdates, Alarm)

	statusMap, err = GetKRForKeyTwoWeeks(db)

	if err != nil {
		log.Fatal(err)
	}

	// form: [rooms]
	keyUpdates := determineAlerts(statusMap, roomApproverMap)
	sendEmails(keyUpdates, Key)

}
