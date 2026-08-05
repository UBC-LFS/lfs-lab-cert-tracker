package utils

import (
	"database/sql"
	"fmt"
	"log"
	"os"

	_ "github.com/lib/pq" // PostgreSQL driver
)

// Database Settings
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
	DB_URL := fmt.Sprintf("host=%s port=%s user=%s password='%s' dbname=%s sslmode=%s", HOST, PORT, USER, PASSWORD, DATABASE, ssl_mode)

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

func (db *Database) GetUsers() (map[int]map[string]interface{}, map[string]int, error) {
	rows, err := db.Conn.Query(`SELECT * FROM auth_user WHERE is_active = TRUE;`)
	if err != nil {
		return nil, nil, err
	}
	defer rows.Close()

	columns, err := rows.Columns()
	if err != nil {
		return nil, nil, fmt.Errorf("failed to get columns: %v", err)
	}

	items := make(map[int]map[string]interface{})
	items_by_username := make(map[string]int)
	for rows.Next() {
		values := make([]interface{}, len(columns))
		valuePtrs := make([]interface{}, len(columns))
		for i := range columns {
			valuePtrs[i] = &values[i]
		}

		// Scan the row into value pointers
		if err := rows.Scan(valuePtrs...); err != nil {
			return nil, nil, fmt.Errorf("failed to scan row: %v", err)
		}

		rowMap := make(map[string]interface{})
		var id int
		var username string
		for i, col := range columns {
			var v interface{}
			val := values[i]

			b, ok := val.([]byte)
			if ok {
				v = string(b)
			} else {
				v = val
			}
			if col == "id" {
				id = int(v.(int64))
			} else if col == "username" {
				username = v.(string)
			}

			rowMap[col] = v
		}

		items[id] = rowMap
		items_by_username[username] = id
	}

	return items, items_by_username, nil
}

func (db *Database) GetAdmins() (map[int]map[string]interface{}, error) {
	rows, err := db.Conn.Query(`SELECT * FROM auth_user WHERE is_active = TRUE AND is_superuser = TRUE;`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	columns, err := rows.Columns()
	if err != nil {
		return nil, fmt.Errorf("failed to get columns: %v", err)
	}

	items := make(map[int]map[string]interface{})
	items_by_username := make(map[string]int)
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
		var id int
		var username string
		for i, col := range columns {
			var v interface{}
			val := values[i]

			b, ok := val.([]byte)
			if ok {
				v = string(b)
			} else {
				v = val
			}
			if col == "id" {
				id = int(v.(int64))
			} else if col == "username" {
				username = v.(string)
			}

			rowMap[col] = v
		}

		items[id] = rowMap
		items_by_username[username] = id
	}

	return items, nil
}

func (db *Database) GetTrainings() (map[string]map[string]interface{}, map[int]map[string]interface{}, map[string]map[string]interface{}, error) {
	rows, err := db.Conn.Query(`SELECT * FROM lfs_lab_cert_tracker_cert;`)
	if err != nil {
		return nil, nil, nil, err
	}
	defer rows.Close()

	columns, err := rows.Columns()
	if err != nil {
		return nil, nil, nil, fmt.Errorf("failed to get columns: %v", err)
	}

	items_by_name := make(map[string]map[string]interface{})
	items_by_id := make(map[int]map[string]interface{})
	items_by_unique_id := make(map[string]map[string]interface{})
	for rows.Next() {
		values := make([]interface{}, len(columns))
		valuePtrs := make([]interface{}, len(columns))
		for i := range columns {
			valuePtrs[i] = &values[i]
		}

		// Scan the row into value pointers
		if err := rows.Scan(valuePtrs...); err != nil {
			return nil, nil, nil, fmt.Errorf("failed to scan row: %v", err)
		}

		rowMap := make(map[string]interface{})
		var name string
		var id int
		var unique_id string
		for i, col := range columns {
			var v interface{}
			val := values[i]

			b, ok := val.([]byte)
			if ok {
				v = string(b)
			} else {
				v = val
			}

			if col == "id" {
				id = int(v.(int64))
			} else if col == "name" {
				name = string(v.(string))
			} else if col == "unique_id" {
				if v == nil {
					unique_id = ""
				} else {
					unique_id = v.(string)
				}
			}
			rowMap[col] = v
		}

		items_by_name[name] = rowMap
		items_by_id[id] = rowMap
		if unique_id != "" {
			items_by_unique_id[unique_id] = rowMap
		}
	}

	return items_by_name, items_by_id, items_by_unique_id, nil
}
