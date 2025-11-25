package main

import (
	"database/sql"
	"fmt"
	"time"
	"trms_scheduler/utils"

	"github.com/lib/pq"
)

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

func GetUserAreas(db *utils.Database) ([]UserLab, error) {
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

func GetAreaTrainings(db *utils.Database) ([]LabCert, error) {
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

func GetUserTrainings(db *utils.Database) ([]UserCert, error) {
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

func GetUserTrainingKeys(db utils.Database) (map[string]bool, error) {
	existing := make(map[string]bool)

	rows, err := db.Conn.Query(`SELECT user_id, cert_id, completion_date FROM lfs_lab_cert_tracker_usercert;`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	for rows.Next() {
		var userID, certID int64
		var completionDate time.Time
		if err := rows.Scan(&userID, &certID, &completionDate); err != nil {
			return nil, err
		}

		key := fmt.Sprintf("%d-%d-%s", userID, certID, completionDate.Format("2006-01-02"))
		existing[key] = true
	}

	return existing, nil
}

func GetUsersWithMissingTrainings(db utils.Database) (map[int][]string, int, error) {
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

func GetUsersWithExpiredTrainings(db utils.Database) (map[int][]string, error) {
	query := `
		SELECT
			u.id AS user_id,
			u.username,
			COALESCE(
				array_remove(
					array_agg(DISTINCT c.name)
					FILTER (
						WHERE latest.expiry_date IS NOT NULL
						  AND latest.completion_date IS NOT NULL
						  AND latest.expiry_date <> latest.completion_date
						  AND latest.expiry_date < NOW()
					),
				NULL),
				'{}'::text[]
			) AS expired_certs,
			COUNT(DISTINCT c.id)
				FILTER (
					WHERE latest.expiry_date IS NOT NULL
					  AND latest.completion_date IS NOT NULL
					  AND latest.expiry_date <> latest.completion_date
					  AND latest.expiry_date < NOW()
				) AS expired_count
		FROM auth_user u
		JOIN (
			SELECT DISTINCT ON (uc.user_id, uc.cert_id)
				uc.user_id,
				uc.cert_id,
				uc.expiry_date,
				uc.completion_date
			FROM lfs_lab_cert_tracker_usercert uc
			ORDER BY uc.user_id, uc.cert_id, uc.expiry_date DESC
		) AS latest
			ON latest.user_id = u.id
		JOIN lfs_lab_cert_tracker_cert c
			ON c.id = latest.cert_id
		WHERE u.is_active = TRUE
		GROUP BY u.id, u.username
		ORDER BY u.id;`

	rows, err := db.Conn.Query(query)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	results := make(map[int][]string)
	for rows.Next() {
		var userID int
		var username string
		var expiredCerts pq.StringArray
		var expiredCount int

		err := rows.Scan(&userID, &username, &expiredCerts, &expiredCount)
		if err != nil {
			return nil, err
		}

		certs := []string(expiredCerts)
		results[userID] = certs
	}
	return results, nil
}
