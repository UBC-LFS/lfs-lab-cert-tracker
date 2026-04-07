package main

import (
	"database/sql"
	"time"
	"trms_scheduler/utils"
)

type ExpirySearchResult struct {
	UserID       int
	LabName      string
	CertName     string
	ExpiryDate   time.Time
	SupervisorID sql.NullInt64
}

// Before the expiry date
func GetExpiringTrainings(db utils.Database, days int) ([]ExpirySearchResult, error) {
	query := `WITH latest_user_certs AS (
        SELECT
            uc.*,
            ROW_NUMBER() OVER (
                PARTITION BY uc.user_id, uc.cert_id
                ORDER BY uc.completion_date DESC
            ) AS rn
        FROM lfs_lab_cert_tracker_usercert uc
		)
		SELECT
			u.id AS user_id,
			l.name AS lab_name,
			c.name AS cert_name,
			luc.expiry_date AS user_expiry_date,
			sup.id AS supervisor_id
		FROM lfs_lab_cert_tracker_lab l
		JOIN lfs_lab_cert_tracker_labcert lc 
			ON lc.lab_id = l.id
		JOIN lfs_lab_cert_tracker_cert c 
			ON c.id = lc.cert_id
		JOIN lfs_lab_cert_tracker_userlab ul 
			ON ul.lab_id = l.id
		JOIN auth_user u 
			ON u.id = ul.user_id AND u.is_active = TRUE
		JOIN latest_user_certs luc
			ON luc.user_id = u.id AND luc.cert_id = c.id AND luc.rn = 1
		LEFT JOIN lfs_lab_cert_tracker_userlab ul_sup
			ON ul_sup.lab_id = l.id AND ul_sup.role = 1
		LEFT JOIN auth_user sup
			ON sup.id = ul_sup.user_id AND sup.is_active = TRUE
		WHERE luc.expiry_date = CURRENT_DATE + ($1 || ' days')::interval
		ORDER BY l.id, u.id;`

	rows, err := db.Conn.Query(query, days)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	results := []ExpirySearchResult{}

	for rows.Next() {
		var r ExpirySearchResult
		err := rows.Scan(
			&r.UserID,
			&r.LabName,
			&r.CertName,
			&r.ExpiryDate,
			&r.SupervisorID,
		)
		if err != nil {
			return nil, err
		}
		results = append(results, r)
	}

	return results, nil
}
