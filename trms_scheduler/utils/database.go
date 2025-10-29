package utils

import (
	"database/sql"
	"fmt"
	"log"
	"os"

	_ "github.com/lib/pq" // PostgreSQL driver
)

var USER = os.Getenv("LFS_LAB_CERT_TRACKER_DB_USER")
var PASSWORD = os.Getenv("LFS_LAB_CERT_TRACKER_DB_PASSWORD")
var HOST = os.Getenv("LFS_LAB_CERT_TRACKER_DB_HOST")
var PORT = os.Getenv("LFS_LAB_CERT_TRACKER_DB_PORT")
var DATABASE = os.Getenv("LFS_LAB_CERT_TRACKER_DB_NAME")

var SSL_MODE = "verify-full"

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
	log.Println("✅ Database connected successfully")
	return nil
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

func (db *Database) Close() {
	if db.Conn != nil {
		db.Conn.Close()
		log.Println("🔒 Database connection closed")
	}
}
