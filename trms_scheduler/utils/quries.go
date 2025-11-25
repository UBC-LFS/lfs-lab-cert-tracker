package utils

import (
	"database/sql"
	"fmt"
	"time"

	"github.com/lib/pq"
)

/* Missing Training */

type MissingTrainingResult struct {
	LabID        int
	LabName      string
	UserID       int
	MissingCerts []string
	Supervisors  []string
}

func GetUsersWithMissingCerts(db Database) ([]MissingTrainingResult, error) {
	query := `
		WITH latest_usercert AS (
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

	rows, err := db.Conn.Query(query)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	results := []MissingTrainingResult{}

	for rows.Next() {
		var r MissingTrainingResult
		var missing_certs pq.StringArray
		var supervisors pq.StringArray

		err := rows.Scan(
			&r.LabID,
			&r.LabName,
			&r.UserID,
			&missing_certs,
			&supervisors,
		)
		if err != nil {
			return nil, fmt.Errorf("scan error: %w", err)
		}

		r.MissingCerts = missing_certs
		r.Supervisors = supervisors
		results = append(results, r)
	}

	return results, nil
}

/* Expiry Date */

type ExpirySearchResult struct {
	UserID       int
	LabName      string
	CertName     string
	ExpiryDate   time.Time
	SupervisorID sql.NullInt64
}

// Before the expiry date
func GetExpiringTrainings(db Database, days int) ([]ExpirySearchResult, error) {
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

// After the expiry date
func GetExpiredTrainings(db Database) ([]ExpirySearchResult, error) {
	query := `
        WITH latest_user_certs AS (
			SELECT
				uc.*,
				ROW_NUMBER() OVER(
					PARTITION BY uc.user_id, uc.cert_id
					ORDER BY uc.completion_date DESC
				) AS rn
			FROM lfs_lab_cert_tracker_usercert uc
		),
		expired_users AS (
            SELECT
                ul.lab_id,
                ul.user_id AS expired_user_id,
                luc.cert_id,
                luc.expiry_date
            FROM lfs_lab_cert_tracker_userlab ul
			JOIN auth_user au 
        		ON au.id = ul.user_id
            JOIN lfs_lab_cert_tracker_labcert lc 
				ON lc.lab_id = ul.lab_id
            JOIN latest_user_certs luc
                ON luc.user_id = ul.user_id
       			AND luc.cert_id = lc.cert_id
            WHERE
				luc.rn = 1 AND
				au.is_active = TRUE AND 
				luc.completion_date <> luc.expiry_date AND 
				luc.expiry_date < CURRENT_DATE
        ),
		lab_supervisors AS (
			SELECT
				ul.lab_id,
				ul.user_id AS supervisor_id
			FROM lfs_lab_cert_tracker_userlab ul
			JOIN auth_user au 
				ON au.id = ul.user_id
			WHERE 
				ul.role = 1 AND au.is_active = TRUE
		)
        SELECT
			eu.expired_user_id,
            l.name AS lab_name,
            c.name AS cert_name,
            eu.expiry_date,
            ls.supervisor_id
        FROM expired_users eu
		JOIN lfs_lab_cert_tracker_lab l 
    		ON l.id = eu.lab_id
		JOIN lfs_lab_cert_tracker_cert c
    		ON c.id = eu.cert_id    
        LEFT JOIN lab_supervisors ls
            ON ls.lab_id = eu.lab_id
        ORDER BY eu.lab_id, eu.expired_user_id;`

	rows, err := db.Conn.Query(query)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var results []ExpirySearchResult
	for rows.Next() {
		var r ExpirySearchResult
		if err := rows.Scan(
			&r.UserID,
			&r.LabName,
			&r.CertName,
			&r.ExpiryDate,
			&r.SupervisorID,
		); err != nil {
			return nil, err
		}
		results = append(results, r)
	}

	return results, nil
}
