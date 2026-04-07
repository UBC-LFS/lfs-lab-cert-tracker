package main

import (
	"database/sql"
	"slices"
	"strings"
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

// After the expiry date
func GetExpiredTrainings(db utils.Database) ([]ExpirySearchResult, error) {
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

func GetUsersAndPIsForExpiryDate(data []ExpirySearchResult, allUsers map[int]map[string]interface{}) (map[string][]string, map[string][]map[string]interface{}) {
	users := make(map[string][]string)
	temp_pis := make(map[string][]map[string]interface{})

	for _, value := range data {
		user := allUsers[value.UserID]
		userName := utils.DisplayUserInfo(user, "")
		trainingInfo := utils.DisplayExpiryInfo(value.CertName, value.ExpiryDate)

		found := slices.Contains(users[userName], trainingInfo)
		if !found {
			users[userName] = append(users[userName], trainingInfo)
		}

		if value.SupervisorID.Valid {
			pi := allUsers[int(value.SupervisorID.Int64)]
			piName := utils.DisplayUserInfo(pi, "")

			item := map[string]interface{}{
				"user":     value.UserID,
				"area":     value.LabName,
				"training": trainingInfo,
			}

			temp_pis[piName] = append(temp_pis[piName], item)
		}
	}

	pis := make(map[string][]map[string]interface{})
	for pi, items := range temp_pis {
		trainings := make(map[string][]string)
		for _, item := range items {
			key := utils.CombineAreaAndUser(item["area"].(string), item["user"].(int))
			trainings[key] = append(trainings[key], item["training"].(string))
		}

		for key, value := range trainings {
			info := strings.Split(key, "|")
			areaName := info[0]
			userID_int := utils.StrToInt(info[1])

			user := allUsers[userID_int]
			userName := utils.DisplayUserInfo(user, "no-email")

			item := map[string]interface{}{
				"area":      areaName,
				"user":      userName,
				"trainings": value,
			}
			pis[pi] = append(pis[pi], item)
		}
	}
	return users, pis
}
