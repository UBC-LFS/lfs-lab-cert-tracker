package main

import (
	"fmt"
	"sort"
	"trms_scheduler/utils"

	"github.com/lib/pq"
)

/* Missing Training for Users */

type MissingTrainingResult struct {
	LabID        int
	LabName      string
	UserID       int
	MissingCerts []string
	Supervisors  []string
}

type UserCertItem struct {
	User      string   `json:"User"`
	FirstName string   `json:"FirstName"`
	LastName  string   `json:"LastName"`
	Certs     []string `json:"Certs"`
}

func GetUsersWithMissingCerts(db utils.Database) ([]MissingTrainingResult, error) {
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
		missing_certs AS (
			SELECT ul.lab_id, ul.user_id, l.name AS lab_name, array_agg(c.name) FILTER (WHERE luc.cert_id IS NULL) AS missing_cert_names
			FROM lfs_lab_cert_tracker_userlab ul
			JOIN lfs_lab_cert_tracker_lab l ON l.id = ul.lab_id
			JOIN lfs_lab_cert_tracker_labcert lc ON lc.lab_id = ul.lab_id
			JOIN lfs_lab_cert_tracker_cert c ON c.id = lc.cert_id
			LEFT JOIN latest_usercert luc ON luc.user_id = ul.user_id AND luc.cert_id = lc.cert_id
			JOIN auth_user u ON u.id = ul.user_id
			WHERE u.is_active = TRUE AND c.is_lfs = TRUE
			GROUP BY ul.lab_id, ul.user_id, l.name
		)
		SELECT
			m.lab_id,
			m.lab_name,
			m.user_id,
			m.missing_cert_names AS missing_certs
		FROM missing_certs m
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

		err := rows.Scan(&r.LabID, &r.LabName, &r.UserID, &missing_certs)
		if err != nil {
			return nil, fmt.Errorf("scan error: %w", err)
		}

		r.MissingCerts = missing_certs
		results = append(results, r)
	}

	return results, nil
}

/* Missing Training for Supervisors */

func GetSupervisorsWithMissingCerts(db utils.Database) (map[string]map[string][]UserCertItem, error) {
	query := `
		SELECT
			sup.username,
			l.name,
			member.username,
			member.first_name,
        	member.last_name,
			c.name
		FROM lfs_lab_cert_tracker_lab l
		JOIN lfs_lab_cert_tracker_userlab ul_member ON ul_member.lab_id = l.id AND ul_member.role IN (0, 1)
		JOIN auth_user member ON member.id = ul_member.user_id AND member.is_active = TRUE
		JOIN lfs_lab_cert_tracker_labcert lc ON lc.lab_id = l.id
		JOIN lfs_lab_cert_tracker_cert c ON c.id = lc.cert_id
		JOIN lfs_lab_cert_tracker_userlab ul_sup ON ul_sup.lab_id = l.id AND ul_sup.role = 1
		JOIN auth_user sup ON sup.id = ul_sup.user_id AND sup.is_active = TRUE
		WHERE NOT EXISTS (
			SELECT 1
			FROM lfs_lab_cert_tracker_usercert uc
			WHERE uc.user_id = member.id AND uc.cert_id = c.id
		) AND c.is_lfs = TRUE
		ORDER BY sup.username, l.name, member.username, c.name;`

	rows, err := db.Conn.Query(query)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	temp := make(map[string]map[string]map[string]*UserCertItem)

	for rows.Next() {
		var supervisorName, labName string
		var username, firstName, lastName, certName string

		err := rows.Scan(
			&supervisorName,
			&labName,
			&username,
			&firstName,
			&lastName,
			&certName,
		)
		if err != nil {
			return nil, err
		}

		if _, ok := temp[supervisorName]; !ok {
			temp[supervisorName] = make(map[string]map[string]*UserCertItem)
		}

		if _, ok := temp[supervisorName][labName]; !ok {
			temp[supervisorName][labName] = make(map[string]*UserCertItem)
		}

		if _, ok := temp[supervisorName][labName][username]; !ok {
			temp[supervisorName][labName][username] = &UserCertItem{
				User:      username,
				FirstName: firstName,
				LastName:  lastName,
				Certs:     []string{},
			}
		}

		temp[supervisorName][labName][username].Certs = append(temp[supervisorName][labName][username].Certs, certName)
	}

	if err := rows.Err(); err != nil {
		return nil, err
	}

	result := make(map[string]map[string][]UserCertItem)

	for sup, labs := range temp {
		result[sup] = make(map[string][]UserCertItem)

		for lab, users := range labs {
			userList := make([]UserCertItem, 0, len(users))
			for _, u := range users {
				sort.Strings(u.Certs)
				userList = append(userList, *u)
			}

			sort.Slice(userList, func(i, j int) bool {
				if userList[i].LastName == userList[j].LastName {
					return userList[i].FirstName < userList[j].FirstName
				}
				return userList[i].LastName < userList[j].LastName
			})

			result[sup][lab] = userList
		}
	}

	return result, nil
}
