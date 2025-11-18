package main

import (
	"fmt"
	"trms_scheduler/utils"

	"github.com/lib/pq"
)

type MissingCertRecord struct {
	LabID        int
	LabName      string
	UserID       int
	MissingCerts []string
	Supervisors  []string
}

func GetUsersWithMissingCerts(db utils.Database) ([]MissingCertRecord, error) {
	q := `
		WITH latest_usercert AS (
			-- pick the most recent completion_date per user+cert
			SELECT DISTINCT ON (uc.user_id, uc.cert_id)
				uc.user_id,
				uc.cert_id,
				uc.completion_date,
				uc.expiry_date
			FROM lfs_lab_cert_tracker_usercert uc
			ORDER BY uc.user_id, uc.cert_id, uc.completion_date DESC
		),

		lab_supervisors AS (
			SELECT
				ul.lab_id,
				array_agg(u.id) AS supervisors
			FROM lfs_lab_cert_tracker_userlab ul
			JOIN auth_user u ON u.id = ul.user_id
			WHERE ul.role = 1
			AND u.is_active = TRUE
			GROUP BY ul.lab_id
		),

		missing_certs AS (
			SELECT
				ul.lab_id,
				ul.user_id,
				l.name AS lab_name,
				
				-- collect required certs that the user is missing
				array_agg(c.name) FILTER (
					WHERE luc.cert_id IS NULL
				) AS missing_cert_names
			FROM lfs_lab_cert_tracker_userlab ul
			JOIN lfs_lab_cert_tracker_lab l ON l.id = ul.lab_id
			JOIN lfs_lab_cert_tracker_labcert lc ON lc.lab_id = ul.lab_id
			JOIN lfs_lab_cert_tracker_cert c ON c.id = lc.cert_id
			LEFT JOIN latest_usercert luc
				ON luc.user_id = ul.user_id
				AND luc.cert_id = lc.cert_id
			JOIN auth_user u ON u.id = ul.user_id
			WHERE u.is_active = TRUE
			GROUP BY ul.lab_id, ul.user_id, l.name
		)

		SELECT
			m.lab_id,
			m.lab_name,
			m.user_id,
			m.missing_cert_names AS missing_certs,
			ls.supervisors
		FROM missing_certs m
		LEFT JOIN lab_supervisors ls ON m.lab_id = ls.lab_id
		WHERE m.missing_cert_names IS NOT NULL;`

	rows, err := db.Conn.Query(q)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	results := []MissingCertRecord{}

	for rows.Next() {
		var r MissingCertRecord
		var missing pq.StringArray
		var supervisors pq.StringArray

		err := rows.Scan(
			&r.LabID,
			&r.LabName,
			&r.UserID,
			&missing,
			&supervisors,
		)
		if err != nil {
			return nil, fmt.Errorf("scan error: %w", err)
		}

		r.MissingCerts = missing
		r.Supervisors = supervisors
		results = append(results, r)
	}

	return results, nil
}
