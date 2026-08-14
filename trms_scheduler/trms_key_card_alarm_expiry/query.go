package main

import (
	"database/sql"
	"fmt"
	"time"
	"trms_scheduler/utils"
)

// From KEY_REQUEST/UTILS
//APPROVED = '0'
//DECLINED = '1'
//INSUFFICIENT = '2'

type Status int

const (
	Approved Status = iota
	Declined
	Insufficient
)

func makeStatus(status string) Status {
	if status == "0" {
		return Approved
	} else if status == "1" {
		return Declined
	} else if status == "2" {
		return Insufficient
	}
	return -1
}

type FormUser struct {
	firstName string
	lastName  string
	email     string
}

type Room struct {
	building string
	floor    string
	number   string
}

type EntityType string

const (
	Group   EntityType = "group"
	Manager EntityType = "user"
)

type RoomEntity struct {
	entityID   int
	entityType EntityType
}

type KeyRequestStatusResult struct {
	status    Status
	createdAt time.Time
}

type Option string

const (
	Card   Option = "r.card_access"
	Alarm Option = "r.alarm"
	Key   Option = "r.key"
)

func GetApprovalEntityMapping(db utils.Database) (map[int]int, error) {
	query := `
			SELECT entities.room_id, COUNT(entities.room_id) as num_approvers
			FROM
				(SELECT room_id, 'user' AS entity_type, user_id AS entity_id
				FROM key_request_room_managers

				UNION ALL

				SELECT room_id, 'group' AS entity_type, approvalgroup_id AS entity_id
				FROM key_request_room_groups

				ORDER BY room_id) entities
			GROUP BY entities.room_id
		`

	rows, err := db.Conn.Query(query)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	// room_id : count

	roomApproverMap := make(map[int]int)

	for rows.Next() {
		var roomID int
		var approverCount int

		if err := rows.Scan(
			&roomID,
			&approverCount,
		); err != nil {
			return nil, err
		}
		roomApproverMap[roomID] = approverCount
	}

	return roomApproverMap, nil
}

// Form id : room: entity/entity_type : approval (most recent)
//
//	3 : {
//				 3 : {
//					 (1, 'group') :
//						 {status, created_at}
//					}
//	}
func processKeyRequestRows(db utils.Database, query string) (map[int]map[int]map[RoomEntity]KeyRequestStatusResult, error) {
	rows, err := db.Conn.Query(query)
	if err != nil {
		fmt.Println("Error with the query")
		return nil, err
	}
	defer rows.Close()

	keyRequestStatusMap := make(map[int]map[int]map[RoomEntity]KeyRequestStatusResult)

	for rows.Next() {

		var rfsID int
		var rfsCreatedAt time.Time
		var rfsStatus string
		var rfsFormID int
		var rfsManagerID sql.NullInt64
		var rfsGroupID sql.NullInt64
		var rfsRoomID int

		// User details
		var first string
		var last string
		var email string

		// Room details
		var building string
		var floor string
		var roomNumber string

		var r RoomEntity
		if err := rows.Scan(
			&rfsID,
			&rfsCreatedAt,
			&rfsStatus,
			&rfsFormID,
			&rfsManagerID,
			&rfsGroupID,
			&rfsRoomID,
			&first,
			&last,
			&email,
			&building,
			&floor,
			&roomNumber,
		); err != nil {
			return nil, err
		}

		if rfsGroupID.Valid {
			r.entityID = int(rfsGroupID.Int64)
			r.entityType = Group
		} else if rfsManagerID.Valid {
			r.entityID = int(rfsManagerID.Int64)
			r.entityType = Manager
		} else {
			// impossible case
		}

		roomMapping := keyRequestStatusMap[rfsFormID]

		if roomMapping == nil {
			keyRequestStatusMap[rfsFormID] = make(map[int]map[RoomEntity]KeyRequestStatusResult)
			roomMapping = keyRequestStatusMap[rfsFormID]
		}

		entityMapping := roomMapping[rfsRoomID]

		if entityMapping == nil {
			roomMapping[rfsRoomID] = make(map[RoomEntity]KeyRequestStatusResult)
			entityMapping = roomMapping[rfsRoomID]
		}

		currentMostRecentRS, exists := entityMapping[r]

		if !exists || currentMostRecentRS.createdAt.Before(rfsCreatedAt) {
			status := makeStatus(rfsStatus)
			var newStatus KeyRequestStatusResult
			newStatus.createdAt = rfsCreatedAt
			newStatus.status = status
			entityMapping[r] = newStatus
		}

		_, exists = FormUserMap[rfsFormID]

		if !exists {
			var user FormUser
			user.firstName = first
			user.lastName = last
			user.email = email
			FormUserMap[rfsFormID] = user
		}

		_, exists = RoomMap[rfsRoomID]

		if !exists {
			var room Room
			room.building = building
			room.floor = floor
			room.number = roomNumber
			RoomMap[rfsRoomID] = room
		}

	}

	return keyRequestStatusMap, nil
}

func makeQuery(option Option) string {
	return fmt.Sprintf(`
		WITH expiring AS (
			SELECT
				rf.id AS requestform_id,
				rfr.room_id,
				auth_user.first_name AS first_name,
				auth_user.last_name AS last_name,
				auth_user.email AS email,
				b.name AS building,
				f.name AS floor,
				r.number AS roomNumber
			FROM key_request_requestform rf
					 JOIN key_request_requestform_rooms rfr
						  ON rfr.requestform_id = rf.id
					JOIN key_request_room r
                          ON rfr.room_id = r.id
					JOIN auth_user
						  ON auth_user.id = rf.user_id
					JOIN key_request_building b
						  ON b.id = r.building_id
					JOIN key_request_floor f
						  ON f.id = r.floor_id
			WHERE rf.expiry_date = CURRENT_DATE + INTERVAL '14 days'
   			  AND auth_user.is_active = TRUE
			  AND r.is_active = TRUE
			  AND %s = TRUE
		)
		SELECT
			rfs.id,
			rfs.created_at,
			rfs.status,
			rfs.form_id,
			rfs.manager_id,
			rfs.group_id,
			rfs.room_id,
			e.first_name,
			e.last_name,
			e.email,
			e.building,
			e.floor,
			e.roomNumber
		FROM key_request_requestformstatus rfs
				 JOIN expiring e
					  ON rfs.form_id = e.requestform_id
						  AND rfs.room_id = e.room_id
		ORDER BY rfs.form_id, rfs.room_id;
`, option)
}

func GetKRForKeyTwoWeeks(db utils.Database) (map[int]map[int]map[RoomEntity]KeyRequestStatusResult, error) {
	keyStatuses := makeQuery(Key)
	return processKeyRequestRows(db, keyStatuses)
}

func GetKRForAlarmTwoWeeks(db utils.Database) (map[int]map[int]map[RoomEntity]KeyRequestStatusResult, error) {
	alarmStatuses := makeQuery(Alarm)
	return processKeyRequestRows(db, alarmStatuses)
}

func GetKRForCardTwoWeeks(db utils.Database) (map[int]map[int]map[RoomEntity]KeyRequestStatusResult, error) {
	cardStatuses := makeQuery(Card)
	return processKeyRequestRows(db, cardStatuses)
}
