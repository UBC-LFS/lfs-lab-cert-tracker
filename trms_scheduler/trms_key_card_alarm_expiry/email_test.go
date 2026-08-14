package main

import (
	"fmt"
	"log"
	"os"
	"strings"
	"testing"

	"trms_scheduler/utils"
)

const GROUP_ALPHA_ID = 1

// ORDER: key, card_access, alarm
const (
	KEY_ONLY   = 100
	CARD_ONLY   = 10
	ALARM_ONLY = 1
	ALL        = 111
	NONE       = 0
	NO_ALARM   = 110
	NO_CARD     = 101
	NO_KEY     = 11
)

var db utils.Database

func TestMain(m *testing.M) {
	err := connectDB()
	if err != nil {
		log.Fatal(err)
	}
	err = zeroTestDatabase()
	if err != nil {
		log.Fatal(err)
	}
	err = seedTestData()
	if err != nil {
		log.Fatal(err)
	}

	exitCode := m.Run()

	db.Close()

	os.Exit(exitCode)
}

func setupTest(t *testing.T) {
	err := truncateTestData()
	if err != nil {
		t.Fatal(err)
	}
}

func connectDB() error {
	// Ensure to only run on test env file

	if err := db.Connect(utils.SSL_MODE); err != nil {
		return fmt.Errorf("error connecting to database: %w", err)
	}

	return nil
}

func zeroTestDatabase() error {

	// Ensure working with test database
	var dbName string

	err := db.Conn.QueryRow("SELECT current_database()").Scan(&dbName)

	if err != nil {
		return fmt.Errorf("error finding database name: %w", err)
	}

	if !strings.Contains(dbName, "test") {
		return fmt.Errorf("aborting: refusing to truncate non-test database %s", dbName)
	}
	query := `
		DO $$
		DECLARE
			r RECORD;
		BEGIN
			FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
				EXECUTE 'TRUNCATE TABLE public.' || quote_ident(r.tablename) || ' RESTART IDENTITY CASCADE;';
			END LOOP;
		END $$;
	`

	_, err = db.Conn.Exec(query)
	if err != nil {
		return err
	}
	return nil
}

// TruncateAndSeedTestData is a helper function to seed test data into the database for testing purposes.
// First it truncates the test DB, then it adds an inventory item and an active and inactive user (1 and 2)
func truncateTestData() error {

	// Ensure working with test database
	var dbName string

	err := db.Conn.QueryRow("SELECT current_database()").Scan(&dbName)

	if err != nil {
		return fmt.Errorf("error finding database name: %w", err)
	}

	if !strings.Contains(dbName, "test") {
		return fmt.Errorf("aborting: refusing to truncate non-test database %s", dbName)
	}

	query := `TRUNCATE TABLE
    			key_request_room_managers,
    			key_request_room_groups,
    			key_request_requestformstatus,
    			key_request_requestform_rooms,
				key_request_requestform
			RESTART IDENTITY CASCADE;
		`

	_, err = db.Conn.Exec(query)
	if err != nil {
		return err
	}
	return nil
}

func seedTestData() error {
	query := `
		INSERT INTO key_request_building (id, name, code, slug, created_on, updated_on)
		VALUES (1, 'Test Building', 'TEST-123', 'test-building', NOW() - INTERVAL '4 day', NOW() - INTERVAL '4 day');

		INSERT INTO key_request_floor (id, name, slug, created_on, updated_on)
		VALUES (1, 'Test Floor', 'test-floor', NOW() - INTERVAL '4 day', NOW() - INTERVAL '4 day');

		INSERT INTO auth_user (id, email, is_active, first_name, last_name, password, date_joined, is_superuser, username, is_staff)
		VALUES (1, 'test-email@email.com', true, 'Test', 'User', '$2a$12$KIXQjHqjH8QyZsGg5rXlOeG7b1u9n1z1Z1Z1Z1Z1Z1Z1Z1Z1Z1', NOW() - INTERVAL '10 day', false, 'testuser1', false);

		INSERT INTO auth_user (id, email, is_active, first_name, last_name, password, date_joined, is_superuser, username, is_staff)
		VALUES (2, 'test-email@email.com', false, 'Test', 'User', '$2a$12$KIXQjHqjH8QyZsGg5rXlOeG7b1u9n1z1Z1Z1Z1Z1Z1Z1Z1Z1Z1', NOW() - INTERVAL '10 day', false, 'testuser2', false);

		INSERT INTO auth_user (id, email, is_active, first_name, last_name, password, date_joined, is_superuser, username, is_staff)
		VALUES (3, 'test2-email@email.com', true, 'Test', 'User', '$2a$12$KIXQjHqjH8QyZsGg5rXlOeG7b1u9n1z1Z1Z1Z1Z1Z1Z1Z1Z1Z1', NOW() - INTERVAL '10 day', false, 'testuser3', false);
	`

	err := insertData(query)
	if err != nil {
		return err
	}

	query = `
	INSERT INTO key_request_room (id, number, key, card_access, alarm, is_active, slug, created_on, updated_on, building_id, floor_id, note)
	VALUES ($1::bigint, '111', true, true, true, true, 'room-111', NOW() - INTERVAL '4 day', NOW() - INTERVAL '4 day', 1, 1, 'Room 100');`
	err = insertData(query, ALL)
	if err != nil {
		return err
	}
	query = `
	INSERT INTO key_request_room (id, number, key, card_access, alarm, is_active, slug, created_on, updated_on, building_id, floor_id, note)
	VALUES ($1::bigint, '110', true, true, false, true, 'room-110', NOW() - INTERVAL '4 day', NOW() - INTERVAL '4 day', 1, 1, 'Room 100');`
	err = insertData(query, NO_ALARM)
	if err != nil {
		return err
	}
	query = `
	INSERT INTO key_request_room (id, number, key, card_access, alarm, is_active, slug, created_on, updated_on, building_id, floor_id, note)
	VALUES ($1::bigint, '101', true, false, true, true, 'room-101', NOW() - INTERVAL '4 day', NOW() - INTERVAL '4 day', 1, 1, 'Room 100');`
	err = insertData(query, NO_CARD)
	if err != nil {
		return err
	}
	query = `
	INSERT INTO key_request_room (id, number, key, card_access, alarm, is_active, slug, created_on, updated_on, building_id, floor_id, note)
	VALUES ($1::bigint, '011', false, true, true, true, 'room-011', NOW() - INTERVAL '4 day', NOW() - INTERVAL '4 day', 1, 1, 'Room 100');`
	err = insertData(query, NO_KEY)
	if err != nil {
		return err
	}
	query = `
	INSERT INTO key_request_room (id, number, key, card_access, alarm, is_active, slug, created_on, updated_on, building_id, floor_id, note)
	VALUES ($1::bigint, '000', false, false, false, true, 'room-000', NOW() - INTERVAL '4 day', NOW() - INTERVAL '4 day', 1, 1, 'Room 100');`
	err = insertData(query, NONE)
	if err != nil {
		return err
	}
	query = `
	INSERT INTO key_request_room (id, number, key, card_access, alarm, is_active, slug, created_on, updated_on, building_id, floor_id, note)
	VALUES ($1::bigint, '001', false, false, true, true, 'room-001', NOW() - INTERVAL '4 day', NOW() - INTERVAL '4 day', 1, 1, 'Room 100');`
	err = insertData(query, ALARM_ONLY)
	if err != nil {
		return err
	}
	query = `
	INSERT INTO key_request_room (id, number, key, card_access, alarm, is_active, slug, created_on, updated_on, building_id, floor_id, note)
	VALUES ($1::bigint, '010', false, true, false, true, 'room-010', NOW() - INTERVAL '4 day', NOW() - INTERVAL '4 day', 1, 1, 'Room 100');`
	err = insertData(query, CARD_ONLY)
	if err != nil {
		return err
	}
	query = `
	INSERT INTO key_request_room (id, number, key, card_access, alarm, is_active, slug, created_on, updated_on, building_id, floor_id, note)
	VALUES ($1::bigint, '100', true, false, false, true, 'room-100', NOW() - INTERVAL '4 day', NOW() - INTERVAL '4 day', 1, 1, 'Room 100');`
	err = insertData(query, KEY_ONLY)
	if err != nil {
		return err
	}

	if err = createGroup(GROUP_ALPHA_ID, "Group Alpha"); err != nil {
		return err
	}

	if err = addMemberToGroup(GROUP_ALPHA_ID, 1); err != nil {
		return err
	}

	if err = addMemberToGroup(GROUP_ALPHA_ID, 2); err != nil {
		return err
	}

	return nil

}

func insertData(insertQuery string, args ...any) error {
	result, err := db.Conn.Exec(insertQuery, args...)
	if err != nil {
		return err
	}

	rowsAffected, err := result.RowsAffected()
	if err != nil {
		return err
	}

	if rowsAffected == 0 {
		return fmt.Errorf("insert failed: no rows affected")
	} else {
		//fmt.Println("Inserted data successfully")
	}

	return nil
}

func addManagerToRoom(roomID int, userID int) error {
	query := `
	INSERT INTO key_request_room_managers (room_id, user_id)
	VALUES ($1::bigint, $2::bigint);
	`
	return insertData(query, roomID, userID)

}

func addGroupToRoom(roomID int, groupID int) error {
	query := `
	INSERT INTO key_request_room_groups (room_id, approvalgroup_id)
	VALUES ($1::bigint, $2::bigint);
	`
	return insertData(query, roomID, groupID)
}

func addRoomsToForm(formID int, roomID int) error {
	query := `
	INSERT INTO key_request_requestform_rooms (requestform_id, room_id)
	VALUES ($1::bigint, $2::bigint);
	`
	return insertData(query, formID, roomID)
}

func addStatusToKeyRequest(formId int, roomID int, status string) error {
	query := `
	INSERT INTO key_request_requestformstatus(status, created_at, form_id, manager_id, operator_id, room_id, group_id)
	VALUES ($1, NOW() - INTERVAL '4 day', $2::bigint, 2, 2, $3::bigint, null)
	`

	return insertData(query, status, formId, roomID)
}

func addStatusToKeyRequestWithManager(formId int, roomID int, status string, managerID int) error {
	query := `
	INSERT INTO key_request_requestformstatus(status, created_at, form_id, manager_id, operator_id, room_id, group_id)
	VALUES ($1, NOW() - INTERVAL '4 day', $2::bigint, $3::bigint, 2, $4::bigint, null)
	`

	return insertData(query, status, formId, managerID, roomID)
}

func addStatusToKeyRequestWithGroup(formId int, roomID int, status string, groupID int) error {
	query := `
	INSERT INTO key_request_requestformstatus(status, created_at, form_id, manager_id, operator_id, room_id, group_id)
	VALUES ($1, NOW() - INTERVAL '4 day', $2::bigint, null, 2, $3::bigint, $4::bigint)
	`

	return insertData(query, status, formId, roomID, groupID)
}

func createGroup(groupID int, groupName string) error {
	query := `
	INSERT INTO key_request_approvalgroup (id, name)
	VALUES ($1::bigint, $2::varchar);
	`

	return insertData(query, groupID, groupName)
}

func addMemberToGroup(groupID int, userID int) error {
	query := `INSERT INTO key_request_approvalgrouprole(role, group_id, user_id)
	Values(1, $1::bigint, $2::bigint);`

	return insertData(query, groupID, userID)
}

func createRequestFormExpiry14Days() error {
	query := `
	INSERT INTO key_request_requestform (affiliation, after_hours_access, working_alone, submitted_at, updated_at, user_id, expiry_date)
	VALUES ('3', '1', false,  NOW() - INTERVAL '4 day', NOW() - INTERVAL '4 day', 1, NOW() + INTERVAL '14 day');
	`

	return insertData(query)
}

// TestQueryGetCard checks that GetKRForCardTwoWeeks returns the expected result when there is a KR Form with a 2-week
// expiry date for a request that contains a room with a Card [only a Card in this case]
func TestQueryGetCard(t *testing.T) {
	// Room with only Card: 010 -> 10

	// SET-UP
	setupTest(t)

	if err := addManagerToRoom(CARD_ONLY, 2); err != nil {
		t.Fatal(err)
	}

	if err := createRequestFormExpiry14Days(); err != nil {
		t.Fatal(err)
	}

	// Attach Room and KRS to the form
	if err := addRoomsToForm(1, CARD_ONLY); err != nil {
		t.Fatal(err)
	}

	if err := addStatusToKeyRequest(1, CARD_ONLY, "0"); err != nil {
		t.Fatal(err)
	}
	// EXECUTE

	roomApproverMap, err := GetApprovalEntityMapping(db)
	if err != nil {
		t.Fatal(err)
	}

	statusMap, err := GetKRForCardTwoWeeks(db)

	// EVALUATE

	if len(statusMap) != 1 {
		t.Fatalf("expected 1 result")
	}

	// Validate the approval status
	for _, roomEntityStatuses := range statusMap {
		for _, roomEntity := range roomEntityStatuses {
			for _, status := range roomEntity {
				if status.status != Approved {
					t.Fatalf("incorrect status; expected %d (Approved) and got %d", Approved, status.status)
				}
			}
		}

	}

	needsUpdate := determineAlerts(statusMap, roomApproverMap)

	for formID, rooms := range needsUpdate {
		if formID != 1 {
			t.Fatalf("incorrect form id; expected 1 and got %d", formID)
		}
		if len(rooms) != 1 {
			t.Fatalf("incorrect number of rooms; expected 1 and got %d", len(rooms))
		}
		if rooms[0] != CARD_ONLY {
			t.Fatalf("incorrect room id; expected %d and got %d", CARD_ONLY, rooms[0])
		}
	}
}

// TestQueryGetKey checks that GetKRForKeyTwoWeeks returns the expected result when there is a KR Form with a 2-week
// expiry date for a request that contains a room with a Key [only a Key in this case]
func TestQueryGetKey(t *testing.T) {
	// Room with only Key:

	// SET-UP
	setupTest(t)

	if err := addManagerToRoom(KEY_ONLY, 2); err != nil {
		t.Fatal(err)
	}

	if err := createRequestFormExpiry14Days(); err != nil {
		t.Fatal(err)
	}

	// Attach Room and KRS to the form
	if err := addRoomsToForm(1, KEY_ONLY); err != nil {
		t.Fatal(err)
	}

	if err := addStatusToKeyRequest(1, KEY_ONLY, "0"); err != nil {
		t.Fatal(err)
	}

	// EXECUTE

	roomApproverMap, err := GetApprovalEntityMapping(db)
	if err != nil {
		t.Fatal(err)
	}

	statusMap, err := GetKRForKeyTwoWeeks(db)

	// EVALUATE

	if len(statusMap) != 1 {
		t.Fatalf("expected 1 result, got %d", len(statusMap))
	}

	// Validate the approval status
	for _, roomEntityStatuses := range statusMap {
		for _, roomEntity := range roomEntityStatuses {
			for _, status := range roomEntity {
				if status.status != Approved {
					t.Fatalf("incorrect status; expected %d (Approved) and got %d", Approved, status.status)
				}
			}
		}
	}

	needsUpdate := determineAlerts(statusMap, roomApproverMap)

	if len(needsUpdate) != 1 {
		t.Fatalf("expected 1 result for rooms which need an update")
	}
	for formID, rooms := range needsUpdate {
		if formID != 1 {
			t.Fatalf("incorrect form id; expected 1 and got %d", formID)
		}
		if len(rooms) != 1 {
			t.Fatalf("incorrect number of rooms; expected 1 and got %d", len(rooms))
		}
		if rooms[0] != KEY_ONLY {
			t.Fatalf("incorrect room id; expected %d and got %d", KEY_ONLY, rooms[0])
		}
	}
}

// TestQueryGetAlarm checks that GetKRForAlarmTwoWeeks returns the expected result when there is a KR Form with a 2-week
// expiry date for a request that contains a room with an Alarm [only an Alarm in this case]
func TestQueryGetAlarm(t *testing.T) {
	// Room with only Alarm

	// SET-UP
	setupTest(t)

	if err := addManagerToRoom(ALARM_ONLY, 2); err != nil {
		t.Fatal(err)
	}

	if err := createRequestFormExpiry14Days(); err != nil {
		t.Fatal(err)
	}

	// Attach Room and KRS to the form
	if err := addRoomsToForm(1, ALARM_ONLY); err != nil {
		t.Fatal(err)
	}

	if err := addStatusToKeyRequest(1, ALARM_ONLY, "0"); err != nil {
		t.Fatal(err)
	}
	// EXECUTE

	roomApproverMap, err := GetApprovalEntityMapping(db)
	if err != nil {
		t.Fatal(err)
	}

	statusMap, err := GetKRForAlarmTwoWeeks(db)

	// EVALUATE

	if len(statusMap) != 1 {
		t.Fatalf("expected 1 result, got %d", len(statusMap))
	}

	// Validate the approval status
	for _, roomEntityStatuses := range statusMap {
		for _, roomEntity := range roomEntityStatuses {
			for _, status := range roomEntity {
				if status.status != Approved {
					t.Fatalf("incorrect status; expected %d (Approved) and got %d", Approved, status.status)
				}
			}
		}
	}

	needsUpdate := determineAlerts(statusMap, roomApproverMap)

	if len(needsUpdate) != 1 {
		t.Fatalf("expected 1 result for rooms which need an update")
	}
	for formID, rooms := range needsUpdate {
		if formID != 1 {
			t.Fatalf("incorrect form id; expected 1 and got %d", formID)
		}
		if len(rooms) != 1 {
			t.Fatalf("incorrect number of rooms; expected 1 and got %d", len(rooms))
		}
		if rooms[0] != ALARM_ONLY {
			t.Fatalf("incorrect room id; expected %d and got %d", ALARM_ONLY, rooms[0])
		}
	}
}

// TestQueryDateBoundaries adds forms for 13, 14, and 15 days away expiry dates to determine that only a 2-week notice is sent
func TestQueryDateBoundaries(t *testing.T) {
	// SET-UP
	setupTest(t)

	// Create 3 request forms: one on each side of date boundary

	if err := addManagerToRoom(ALL, 2); err != nil {
		t.Fatal(err)
	}

	if err := createRequestFormExpiry14Days(); err != nil {
		t.Fatal(err)
	}

	query := `
	INSERT INTO key_request_requestform (id, affiliation, after_hours_access, working_alone, submitted_at, updated_at, user_id, expiry_date)
	VALUES (2, '3', '1', false,  NOW() - INTERVAL '4 day', NOW() - INTERVAL '4 day', 1, NOW() + INTERVAL '13 day');
	INSERT INTO key_request_requestform (id, affiliation, after_hours_access, working_alone, submitted_at, updated_at, user_id, expiry_date)
	VALUES (3, '3', '1', false,  NOW() - INTERVAL '4 day', NOW() - INTERVAL '4 day', 1, NOW() + INTERVAL '15 day');
	`

	err := insertData(query)

	if err != nil {
		t.Fatal(err)
	}

	// Add the rooms to each of the forms

	if err = addRoomsToForm(1, ALL); err != nil {
		t.Fatal(err)
	}
	if err = addRoomsToForm(2, ALL); err != nil {
		t.Fatal(err)
	}
	if err = addRoomsToForm(3, ALL); err != nil {
		t.Fatal(err)
	}

	// Create key request statuses for each
	if err = addStatusToKeyRequest(1, ALL, "0"); err != nil {
		t.Fatal(err)
	}
	if err = addStatusToKeyRequest(2, ALL, "0"); err != nil {
		t.Fatal(err)
	}
	if err = addStatusToKeyRequest(3, ALL, "0"); err != nil {
		t.Fatal(err)
	}

	// EXECUTE

	roomApproverMap, err := GetApprovalEntityMapping(db)
	if err != nil {
		t.Fatal(err)
	}

	statusMap, err := GetKRForKeyTwoWeeks(db)

	// EVALUATE

	if len(statusMap) != 1 {
		t.Fatalf("expected 1 result, got %d", len(statusMap))
	}

	// Validate the approval status
	for _, roomEntityStatuses := range statusMap {
		for _, roomEntity := range roomEntityStatuses {
			for _, status := range roomEntity {
				if status.status != Approved {
					t.Fatalf("incorrect status; expected %d (Approved) and got %d", Approved, status.status)
				}
			}
		}
	}

	needsUpdate := determineAlerts(statusMap, roomApproverMap)

	if len(needsUpdate) != 1 {
		t.Fatalf("expected 1 result for rooms which need an update")
	}
	for formID, rooms := range needsUpdate {
		if formID != 1 {
			t.Fatalf("incorrect form id; expected 1 and got %d", formID)
		}
		if len(rooms) != 1 {
			t.Fatalf("incorrect number of rooms; expected 1 and got %d", len(rooms))
		}
		if rooms[0] != ALL {
			t.Fatalf("incorrect room id; expected 1 and got %d", rooms[0])
		}
	}
}

// TestQueryIgnoreOlderStatuses ensures that only the most recent status is used, ignoring ones created before
func TestQueryIgnoreOlderStatuses(t *testing.T) {
	// SET-UP
	setupTest(t)

	if err := addManagerToRoom(ALL, 2); err != nil {
		t.Fatal(err)
	}

	if err := createRequestFormExpiry14Days(); err != nil {
		t.Fatal(err)
	}

	// Add the rooms to each of the forms

	if err := addRoomsToForm(1, ALL); err != nil {
		t.Fatal(err)
	}

	// Create key request statuses for each
	if err := addStatusToKeyRequest(1, ALL, "1"); err != nil {
		t.Fatal(err)
	}
	if err := addStatusToKeyRequest(1, ALL, "0"); err != nil {
		t.Fatal(err)
	}

	// EXECUTE

	roomApproverMap, err := GetApprovalEntityMapping(db)
	if err != nil {
		t.Fatal(err)
	}

	statusMap, err := GetKRForKeyTwoWeeks(db)

	// EVALUATE

	if len(statusMap) != 1 {
		t.Fatalf("expected 1 result, got %d", len(statusMap))
	}

	// Validate the approval status
	for _, roomEntityStatuses := range statusMap {
		for _, roomEntity := range roomEntityStatuses {
			for _, status := range roomEntity {
				if status.status != Approved {
					t.Fatalf("incorrect status; expected %d (Approved) and got %d", Approved, status.status)
				}
			}
		}
	}

	needsUpdate := determineAlerts(statusMap, roomApproverMap)

	if len(needsUpdate) != 1 {
		t.Fatalf("expected 1 result for rooms which need an update")
	}
	for formID, rooms := range needsUpdate {
		if formID != 1 {
			t.Fatalf("incorrect form id; expected 1 and got %d", formID)
		}
		if len(rooms) != 1 {
			t.Fatalf("incorrect number of rooms; expected 1 and got %d", len(rooms))
		}
		if rooms[0] != ALL {
			t.Fatalf("incorrect room id; expected 1 and got %d", rooms[0])
		}
	}
}

// TestQueryIgnoreRoomsNoStatuses ensures that requests with no statues are ignored
func TestQueryIgnoreRoomsNoStatuses(t *testing.T) {
	// SET-UP
	setupTest(t)

	if err := addManagerToRoom(ALL, 2); err != nil {
		t.Fatal(err)
	}

	if err := createRequestFormExpiry14Days(); err != nil {
		t.Fatal(err)
	}

	// Add the rooms to each of the forms
	if err := addRoomsToForm(1, ALL); err != nil {
		t.Fatal(err)
	}

	// EXECUTE

	roomApproverMap, err := GetApprovalEntityMapping(db)
	if err != nil {
		t.Fatal(err)
	}

	statusMap, err := GetKRForKeyTwoWeeks(db)

	if err != nil {
		t.Fatal(err)
	}

	// EVALUATE

	if len(statusMap) != 0 {
		t.Fatalf("expected 0 result, got %d", len(statusMap))
	}

	needsUpdate := determineAlerts(statusMap, roomApproverMap)

	if len(needsUpdate) != 0 {
		t.Fatalf("expected 0 result, got %d", len(needsUpdate))
	}
}

// TestQueryIgnoreRoomsDeclinedStatus ensures that requests with a Declined status (as the most recent) is ignored
func TestQueryIgnoreRoomsDeclinedStatus(t *testing.T) {
	// SET-UP
	setupTest(t)

	if err := addManagerToRoom(ALL, 2); err != nil {
		t.Fatal(err)
	}

	if err := createRequestFormExpiry14Days(); err != nil {
		t.Fatal(err)
	}

	// Add the rooms to each of the forms
	if err := addRoomsToForm(1, ALL); err != nil {
		t.Fatal(err)
	}

	roomApproverMap, err := GetApprovalEntityMapping(db)
	if err != nil {
		t.Fatal(err)
	}

	// EXECUTE

	// Create key request statuses for Declined
	if err = addStatusToKeyRequest(1, ALL, "1"); err != nil {
		t.Fatal(err)
	}

	// EVALUATE

	statusMap, err := GetKRForKeyTwoWeeks(db)

	if err != nil {
		t.Fatal(err)
	}

	// Validate the approval status
	for _, roomEntityStatuses := range statusMap {
		for _, roomEntity := range roomEntityStatuses {
			for _, status := range roomEntity {
				if status.status != Declined {
					t.Fatalf("incorrect status; expected %d (Declined) and got %d", Declined, status.status)
				}
			}
		}
	}

	needsUpdate := determineAlerts(statusMap, roomApproverMap)

	if len(needsUpdate) != 0 {
		t.Fatalf("expected 0 result, got %d", len(needsUpdate))
	}
}

// TestQueryIgnoreRoomsInsufficientStatus ensures that requests with an Insufficient status (as the most recent) is ignored
func TestQueryIgnoreRoomsInsufficientStatus(t *testing.T) {
	// SET-UP
	setupTest(t)

	if err := addManagerToRoom(ALL, 2); err != nil {
		t.Fatal(err)
	}

	if err := createRequestFormExpiry14Days(); err != nil {
		t.Fatal(err)
	}

	// Add the rooms to each of the forms
	if err := addRoomsToForm(1, ALL); err != nil {
		t.Fatal(err)
	}

	// Create key request statuses for Insufficient
	if err := addStatusToKeyRequest(1, ALL, "2"); err != nil {
		t.Fatal(err)
	}

	roomApproverMap, err := GetApprovalEntityMapping(db)
	if err != nil {
		t.Fatal(err)
	}

	// EXECUTE

	statusMap, err := GetKRForKeyTwoWeeks(db)

	if err != nil {
		t.Fatal(err)
	}

	// Validate the approval status
	for _, roomEntityStatuses := range statusMap {
		for _, roomEntity := range roomEntityStatuses {
			for _, status := range roomEntity {
				if status.status != Insufficient {
					t.Fatalf("incorrect status; expected %d (Insufficient) and got %d", Insufficient, status.status)
				}
			}
		}
	}

	needsUpdate := determineAlerts(statusMap, roomApproverMap)

	if len(needsUpdate) != 0 {
		t.Fatalf("expected 0 result, got %d", len(needsUpdate))
	}
}

func TestQueryPartlyApprovedRoomMultiplePIs(t *testing.T) {

	// SET-UP
	setupTest(t)

	// Add multiple managers
	if err := addManagerToRoom(ALL, 2); err != nil {
		t.Fatal(err)
	}
	if err := addManagerToRoom(ALL, 3); err != nil {
		t.Fatal(err)
	}

	if err := createRequestFormExpiry14Days(); err != nil {
		t.Fatal(err)
	}

	// Attach Room and KRS to the form
	if err := addRoomsToForm(1, ALL); err != nil {
		t.Fatal(err)
	}

	if err := addStatusToKeyRequestWithManager(1, ALL, "0", 2); err != nil {
		t.Fatal(err)
	}
	// EXECUTE

	roomApproverMap, err := GetApprovalEntityMapping(db)
	if err != nil {
		t.Fatal(err)
	}

	statusMap, err := GetKRForCardTwoWeeks(db)

	// EVALUATE

	if len(statusMap) != 1 {
		t.Fatalf("expected 1 result and got %d", len(statusMap))
	}

	// Validate the approval status
	for _, roomEntityStatuses := range statusMap {
		for _, roomEntity := range roomEntityStatuses {
			for entity, status := range roomEntity {
				if entity.entityID == 2 && status.status != Approved {
					t.Fatalf("incorrect status; expected %d (Approved) and got %d", Approved, status.status)
				}
				// Should have no statuses
				if entity.entityID == 3 {
					t.Fatalf("incorrect status; expected %d (Approved) and got %d", Approved, status.status)
				}
			}
		}

	}

	needsUpdate := determineAlerts(statusMap, roomApproverMap)

	for formID, rooms := range needsUpdate {
		if formID != 1 {
			t.Fatalf("incorrect form id; expected 1 and got %d", formID)
		}
		if len(rooms) != 1 {
			t.Fatalf("incorrect number of rooms; expected 1 and got %d", len(rooms))
		}
		if rooms[0] != CARD_ONLY {
			t.Fatalf("incorrect room id; expected %d and got %d", CARD_ONLY, rooms[0])
		}
	}
}

func TestQueryApprovedRoomWithGroupApprover(t *testing.T) {
	// SET-UP
	setupTest(t)

	// Add a single group with multiple members

	if err := addGroupToRoom(ALL, GROUP_ALPHA_ID); err != nil {
		t.Fatal(err)
	}

	// Create form

	if err := createRequestFormExpiry14Days(); err != nil {
		t.Fatal(err)
	}

	// Attach Room and KRS to the form
	if err := addRoomsToForm(1, ALL); err != nil {
		t.Fatal(err)
	}

	if err := addStatusToKeyRequestWithGroup(1, ALL, "0", GROUP_ALPHA_ID); err != nil {
		t.Fatal(err)
	}

	// EXECUTE

	roomApproverMap, err := GetApprovalEntityMapping(db)
	if err != nil {
		t.Fatal(err)
	}

	statusMap, err := GetKRForCardTwoWeeks(db)

	// EVALUATE

	if len(statusMap) != 1 {
		t.Fatalf("expected 1 result and got %d", len(statusMap))
	}

	// Validate the approval status
	for _, roomEntityStatuses := range statusMap {
		for _, roomEntity := range roomEntityStatuses {
			for entity, status := range roomEntity {

				if entity.entityType != Group {
					t.Fatalf("incorrect entity; expected %s and got %s", Group, entity.entityType)
				}

				if entity.entityID != GROUP_ALPHA_ID {
					t.Fatalf("incorrect entity; expected %d and got %d", GROUP_ALPHA_ID, entity.entityID)

				}

				if status.status != Approved {
					t.Fatalf("incorrect status; expected %d (Approved) and got %d", Approved, status.status)
				}
			}
		}

	}

	needsUpdate := determineAlerts(statusMap, roomApproverMap)

	for formID, rooms := range needsUpdate {
		if formID != 1 {
			t.Fatalf("incorrect form id; expected 1 and got %d", formID)
		}
		if len(rooms) != 1 {
			t.Fatalf("incorrect number of rooms; expected 1 and got %d", len(rooms))
		}
		if rooms[0] != ALL {
			t.Fatalf("incorrect room id; expected %d and got %d", ALL, rooms[0])
		}
	}
}

func TestQueryFullyApprovedARoomWithGroupAndPIS(t *testing.T) {
	// SET-UP
	setupTest(t)

	// Add both group and manager
	if err := addGroupToRoom(ALL, GROUP_ALPHA_ID); err != nil {
		t.Fatal(err)
	}

	if err := addManagerToRoom(ALL, 1); err != nil {
		t.Fatal(err)
	}

	// Create form

	if err := createRequestFormExpiry14Days(); err != nil {
		t.Fatal(err)
	}

	// Attach Room and KRS to the form
	if err := addRoomsToForm(1, ALL); err != nil {
		t.Fatal(err)
	}

	if err := addStatusToKeyRequestWithGroup(1, ALL, "0", GROUP_ALPHA_ID); err != nil {
		t.Fatal(err)
	}

	if err := addStatusToKeyRequestWithManager(1, ALL, "0", 1); err != nil {
		t.Fatal(err)
	}

	// EXECUTE

	roomApproverMap, err := GetApprovalEntityMapping(db)
	if err != nil {
		t.Fatal(err)
	}

	statusMap, err := GetKRForCardTwoWeeks(db)

	// EVALUATE

	if len(statusMap) != 1 {
		t.Fatalf("expected 1 result and got %d", len(statusMap))
	}

	// Validate the approval status
	for _, roomEntityStatuses := range statusMap {
		for _, roomEntity := range roomEntityStatuses {
			if len(roomEntity) != 2 {
				t.Fatalf("incorrect number of entities; expected 2 and got %d", len(roomEntityStatuses))
			}
			for _, status := range roomEntity {
				if status.status != Approved {
					t.Fatalf("incorrect status; expected %d (Approved) and got %d", Approved, status.status)
				}
			}
		}

	}

	needsUpdate := determineAlerts(statusMap, roomApproverMap)

	for formID, rooms := range needsUpdate {
		if formID != 1 {
			t.Fatalf("incorrect form id; expected 1 and got %d", formID)
		}
		if len(rooms) != 1 {
			t.Fatalf("incorrect number of rooms; expected 1 and got %d", len(rooms))
		}
		if rooms[0] != ALL {
			t.Fatalf("incorrect room id; expected %d and got %d", ALL, rooms[0])
		}
	}
}

func TestQueryPartlyApprovedARoomWithGroupAndPIS(t *testing.T) {
	setupTest(t)

	// Add both group and manager
	if err := addGroupToRoom(ALL, GROUP_ALPHA_ID); err != nil {
		t.Fatal(err)
	}

	if err := addManagerToRoom(ALL, 1); err != nil {
		t.Fatal(err)
	}

	// Create form

	if err := createRequestFormExpiry14Days(); err != nil {
		t.Fatal(err)
	}

	// Attach Room and KRS to the form
	if err := addRoomsToForm(1, ALL); err != nil {
		t.Fatal(err)
	}

	if err := addStatusToKeyRequestWithGroup(1, ALL, "0", GROUP_ALPHA_ID); err != nil {
		t.Fatal(err)
	}

	if err := addStatusToKeyRequestWithManager(1, ALL, "1", 1); err != nil {
		t.Fatal(err)
	}

	// EXECUTE

	roomApproverMap, err := GetApprovalEntityMapping(db)
	if err != nil {
		t.Fatal(err)
	}

	statusMap, err := GetKRForCardTwoWeeks(db)

	// EVALUATE

	if len(statusMap) != 1 {
		t.Fatalf("expected 1 result and got %d", len(statusMap))
	}

	// Validate the approval status
	for _, roomEntityStatuses := range statusMap {
		for _, roomEntity := range roomEntityStatuses {
			if len(roomEntity) != 2 {
				t.Fatalf("incorrect number of entities; expected 2 and got %d", len(roomEntityStatuses))
			}
			for entity, status := range roomEntity {
				if entity.entityType == Manager && status.status != Declined {
					t.Fatalf("incorrect status; expected %d (Declined) and got %d", Declined, status.status)
				}
				if entity.entityType == Group && status.status != Approved {
					t.Fatalf("incorrect status; expected %d (Approved) and got %d", Approved, status.status)
				}
			}
		}

	}

	needsUpdate := determineAlerts(statusMap, roomApproverMap)

	if len(needsUpdate) != 0 {
		t.Fatalf("expected no forms which need an update but got %d", len(needsUpdate))
	}
}

// TESTING EMAIL CONTENT

func TestSendEmails(t *testing.T) {
	setupTest(t)

	if err := addManagerToRoom(ALL, 1); err != nil {
		t.Fatal(err)
	}

	// Create form

	if err := createRequestFormExpiry14Days(); err != nil {
		t.Fatal(err)
	}

	// Attach Room and KRS to the form
	if err := addRoomsToForm(1, ALL); err != nil {
		t.Fatal(err)
	}

	if err := addStatusToKeyRequestWithManager(1, ALL, "0", 1); err != nil {
		t.Fatal(err)
	}

	roomApproverMap, err := GetApprovalEntityMapping(db)

	// ========= Card EMAILS ===========

	statusMap, err := GetKRForCardTwoWeeks(db)

	if err != nil {
		log.Fatal(err)
	}

	keyUpdates := determineAlerts(statusMap, roomApproverMap)
	summary := sendEmails(keyUpdates, Card)

	if summary.Total != 1 {
		t.Fatalf("expected 1 card email but got %d", summary.Total)
	}

	if len(summary.Failures) != 0 {
		t.Fatalf("expected 0 card email errors but got %d", len(summary.Failures))
	}

	if summary.SuccessCount != 1 {
		t.Fatalf("expected 1 card email success but got %d", summary.SuccessCount)

	}

	// ========= ALARM EMAILS ===========

	statusMap, err = GetKRForAlarmTwoWeeks(db)

	if err != nil {
		log.Fatal(err)
	}

	keyUpdates = determineAlerts(statusMap, roomApproverMap)
	summary = sendEmails(keyUpdates, Alarm)

	if summary.Total != 1 {
		t.Fatalf("expected 1 alarm code email but got %d", summary.Total)
	}

	if len(summary.Failures) != 0 {
		t.Fatalf("expected 0 alarm code email errors but got %d", len(summary.Failures))
	}

	if summary.SuccessCount != 1 {
		t.Fatalf("expected 1 alarm code email success but got %d", summary.SuccessCount)

	}

	// ========= KEY EMAILS ===========

	statusMap, err = GetKRForKeyTwoWeeks(db)

	if err != nil {
		log.Fatal(err)
	}

	keyUpdates = determineAlerts(statusMap, roomApproverMap)
	summary = sendEmails(keyUpdates, Key)

	if summary.Total != 1 {
		t.Fatalf("expected 1 key email but got %d", summary.Total)
	}

	if len(summary.Failures) != 0 {
		t.Fatalf("expected 0 key email errors but got %d", len(summary.Failures))
	}

	if summary.SuccessCount != 1 {
		t.Fatalf("expected 1 key email success but got %d", summary.SuccessCount)

	}

	t.Log("Please check your email inbox to verify emails are formatted correctly.")

}
