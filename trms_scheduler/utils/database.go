package utils

import (
	"database/sql"
	"fmt"
	"log"
	"os"

	"github.com/lib/pq"
	_ "github.com/lib/pq" // PostgreSQL driver
)

var USER = os.Getenv("LFS_LAB_CERT_TRACKER_DB_USER")
var PASSWORD = os.Getenv("LFS_LAB_CERT_TRACKER_DB_PASSWORD")
var HOST = os.Getenv("LFS_LAB_CERT_TRACKER_DB_HOST")
var PORT = os.Getenv("LFS_LAB_CERT_TRACKER_DB_PORT")
var DATABASE = os.Getenv("LFS_LAB_CERT_TRACKER_DB_NAME")

// Database is like a class that manages DB operations
type Database struct {
	Conn *sql.DB
}

// Connect opens the database connection
func (db *Database) Connect(ssl_mode string) error {
	DB_URL := fmt.Sprintf("postgres://%s:%s@%s:%s/%s?sslmode=%s", USER, PASSWORD, HOST, PORT, DATABASE, ssl_mode)

	if DB_URL == "" {
		return fmt.Errorf("DB_URL environment variable not set")
	}

	conn, err := sql.Open("postgres", DB_URL)
	if err != nil {
		return fmt.Errorf("error opening database: %v", err)
	}

	// Test connection
	if err := conn.Ping(); err != nil {
		return fmt.Errorf("error connecting to database: %v", err)
	}

	db.Conn = conn
	log.Println("Database connected successfully")
	return nil
}

func (db *Database) Close() {
	if db.Conn != nil {
		db.Conn.Close()
		log.Println("Database connection closed")
	}
}

func (db *Database) GetUsers() (map[int]map[string]interface{}, error) {
	q := `SELECT * FROM auth_user WHERE is_active = TRUE;`
	rows, err := db.Conn.Query(q)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	columns, err := rows.Columns()
	if err != nil {
		return nil, fmt.Errorf("failed to get columns: %v", err)
	}

	results := make(map[int]map[string]interface{})
	for rows.Next() {
		values := make([]interface{}, len(columns))
		valuePtrs := make([]interface{}, len(columns))
		for i := range columns {
			valuePtrs[i] = &values[i]
		}

		// Scan the row into value pointers
		if err := rows.Scan(valuePtrs...); err != nil {
			return nil, fmt.Errorf("failed to scan row: %v", err)
		}

		rowMap := make(map[string]interface{})
		var userID int
		for i, col := range columns {
			var v interface{}
			val := values[i]

			// Convert []byte to string for readability
			b, ok := val.([]byte)
			if ok {
				v = string(b)
			} else {
				v = val
			}
			if col == "id" {
				// fmt.Printf("The type of myVar is: %T\n", v)
				userID = int(v.(int64))
			}
			rowMap[col] = v
		}
		results[userID] = rowMap
	}

	return results, nil
}

func (db *Database) GetUsersWithMissingCerts() (map[int][]string, int, error) {
	q := `
		SELECT
			u.id AS user_id,
			u.username,
			COALESCE(
				-- remove any NULL elements just in case
				array_remove(array_agg(DISTINCT c.name) FILTER (WHERE uc.cert_id IS NULL AND c.name IS NOT NULL), NULL),
				'{}'::text[]
			) AS missing_certs,
			COUNT(DISTINCT c.id) FILTER (WHERE uc.cert_id IS NULL) AS missing_count
		FROM auth_user u
		LEFT JOIN lfs_lab_cert_tracker_userlab ul ON ul.user_id = u.id
		LEFT JOIN lfs_lab_cert_tracker_labcert lc ON lc.lab_id = ul.lab_id
		LEFT JOIN lfs_lab_cert_tracker_cert c ON c.id = lc.cert_id
		LEFT JOIN lfs_lab_cert_tracker_usercert uc ON uc.user_id = u.id AND uc.cert_id = c.id
		WHERE u.is_active = TRUE
		GROUP BY u.id, u.username
		ORDER BY u.id;`

	rows, err := db.Conn.Query(q)
	if err != nil {
		return nil, 0, err
	}
	defer rows.Close()

	result := make(map[int][]string)
	totalUsersWithMissing := 0

	for rows.Next() {
		var userID int
		var username sql.NullString
		var missingCerts pq.StringArray // pq.StringArray implements Scanner
		var missingCount sql.NullInt64

		if err := rows.Scan(&userID, &username, &missingCerts, &missingCount); err != nil {
			return nil, 0, fmt.Errorf("scan error: %w", err)
		}

		// Convert pq.StringArray to plain []string
		certs := []string(missingCerts)

		result[userID] = certs
		if missingCount.Valid && missingCount.Int64 > 0 {
			totalUsersWithMissing++
		}
	}

	if err := rows.Err(); err != nil {
		return nil, 0, err
	}

	return result, totalUsersWithMissing, nil
}

func (db *Database) GetUsersWithExpiredCerts() (map[int][]string, int, error) {
	q := `
		SELECT
			u.id AS user_id,
			u.username,
			COALESCE(
				array_remove(
				array_agg(DISTINCT c.name)
					FILTER (WHERE uc.expiry_date IS NOT NULL
							AND uc.completion_date IS NOT NULL
							AND uc.expiry_date <> uc.completion_date),
				NULL
				),
				'{}'::text[]
			) AS expired_certs,
			COUNT(DISTINCT c.id)
				FILTER (WHERE uc.expiry_date IS NOT NULL
						AND uc.completion_date IS NOT NULL
						AND uc.expiry_date <> uc.completion_date) AS expired_count
		FROM auth_user u
		JOIN lfs_lab_cert_tracker_usercert uc ON uc.user_id = u.id
		JOIN lfs_lab_cert_tracker_cert c ON c.id = uc.cert_id
		WHERE u.is_active = TRUE
		GROUP BY u.id, u.username
		ORDER BY u.id;`

	rows, err := db.Conn.Query(q)
	if err != nil {
		return nil, 0, err
	}
	defer rows.Close()

	result := make(map[int][]string)
	totalUsers := 0

	for rows.Next() {
		var userID int
		var username sql.NullString
		var expiredCerts pq.StringArray
		var expiredCount sql.NullInt64

		if err := rows.Scan(&userID, &username, &expiredCerts, &expiredCount); err != nil {
			return nil, 0, fmt.Errorf("scan error: %w", err)
		}

		certs := []string(expiredCerts)
		result[userID] = certs
		if expiredCount.Valid && expiredCount.Int64 > 0 {
			totalUsers++
		}
	}

	if err := rows.Err(); err != nil {
		return nil, 0, err
	}

	return result, totalUsers, nil
}

type UserLab struct {
	UserID int
	LabID  int
}

type LabCert struct {
	LabID    int
	CertID   int
	CertName string
}

type UserCert struct {
	UserID   int
	CertID   int
	CertName string
}

func (db *Database) GetUserAreas() ([]UserLab, error) {
	userLabs := []UserLab{}
	rows, err := db.Conn.Query(`SELECT user_id, lab_id FROM lfs_lab_cert_tracker_userlab`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	for rows.Next() {
		var ul UserLab
		if err := rows.Scan(&ul.UserID, &ul.LabID); err != nil {
			return nil, err
		}
		userLabs = append(userLabs, ul)
	}
	return userLabs, nil
}

func (db *Database) GetAreaTrainings() ([]LabCert, error) {
	labCerts := []LabCert{}
	rows, err := db.Conn.Query(`
		SELECT lc.lab_id, c.id AS cert_id, c.name AS cert_name
		FROM lfs_lab_cert_tracker_labcert lc
		JOIN lfs_lab_cert_tracker_cert c ON lc.cert_id = c.id
	`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	for rows.Next() {
		var lc LabCert
		if err := rows.Scan(&lc.LabID, &lc.CertID, &lc.CertName); err != nil {
			return nil, err
		}
		labCerts = append(labCerts, lc)
	}
	return labCerts, nil
}

func (db *Database) GetUserTrainings() ([]UserCert, error) {
	userCerts := []UserCert{}
	rows, err := db.Conn.Query(`
		SELECT uc.user_id, c.id AS cert_id, c.name AS cert_name
		FROM lfs_lab_cert_tracker_usercert uc
		JOIN lfs_lab_cert_tracker_cert c ON uc.cert_id = c.id
	`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	for rows.Next() {
		var uc UserCert
		if err := rows.Scan(&uc.UserID, &uc.CertID, &uc.CertName); err != nil {
			return nil, err
		}
		userCerts = append(userCerts, uc)
	}
	return userCerts, nil
}

func (db *Database) QueryData(query string) ([]map[string]interface{}, error) {
	if db.Conn == nil {
		return nil, fmt.Errorf("database not connected")
	}

	rows, err := db.Conn.Query(query)
	if err != nil {
		return nil, fmt.Errorf("query error: %v", err)
	}

	defer rows.Close()

	columns, err := rows.Columns()
	if err != nil {
		return nil, fmt.Errorf("failed to get columns: %v", err)
	}

	results := []map[string]interface{}{}

	for rows.Next() {
		// Create a slice of interface{}'s to represent each column
		values := make([]interface{}, len(columns))
		valuePtrs := make([]interface{}, len(columns))
		for i := range columns {
			valuePtrs[i] = &values[i]
		}

		// Scan the row into value pointers
		if err := rows.Scan(valuePtrs...); err != nil {
			return nil, fmt.Errorf("failed to scan row: %v", err)
		}

		// Build a map for the row
		rowMap := make(map[string]interface{})
		for i, col := range columns {
			var v interface{}
			val := values[i]

			// Convert []byte to string for readability
			b, ok := val.([]byte)
			if ok {
				v = string(b)
			} else {
				v = val
			}

			rowMap[col] = v
		}

		results = append(results, rowMap)
	}

	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("row iteration error: %v", err)
	}

	return results, nil
}
