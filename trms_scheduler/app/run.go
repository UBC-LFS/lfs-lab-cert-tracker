package app

func Run(ssl_mode string) {
	Update_by_API(ssl_mode)

	// for _, row := range users {
	// 	fmt.Println(row)
	// }

	// userAreas, err := db.GetUserAreas()
	// if err != nil {
	// 	log.Fatal(err)
	// }

	// for _, row := range userAreas {
	// 	fmt.Println(row)
	// }

	// areaTrainings, err := db.GetAreaTrainings()
	// if err != nil {
	// 	log.Fatal(err)
	// }

	// for _, row := range areaTrainings {
	// 	fmt.Println(row)
	// }

	// userTrainings, err := db.GetUserTrainings()
	// if err != nil {
	// 	log.Fatal(err)
	// }

	// for _, row := range userTrainings {
	// 	fmt.Println(row)
	// }

	// userToLabs := make(map[int][]int)
	// for _, ul := range userAreas {
	// 	userToLabs[ul.UserID] = append(userToLabs[ul.UserID], ul.LabID)
	// }

	// labToCerts := make(map[int]map[int]string)
	// for _, lc := range areaTrainings {
	// 	if labToCerts[lc.LabID] == nil {
	// 		labToCerts[lc.LabID] = make(map[int]string)
	// 	}
	// 	labToCerts[lc.LabID][lc.CertID] = lc.CertName
	// }

	// userToCerts := make(map[int]map[int]string)
	// for _, uc := range userTrainings {
	// 	if userToCerts[uc.UserID] == nil {
	// 		userToCerts[uc.UserID] = make(map[int]string)
	// 	}
	// 	userToCerts[uc.UserID][uc.CertID] = uc.CertName
	// }

	// result := make(map[int][]string)

	// for userID, labs := range userToLabs {
	// 	required := make(map[int]string)
	// 	for _, labID := range labs {
	// 		for certID, certName := range labToCerts[labID] {
	// 			required[certID] = certName
	// 		}
	// 	}

	// 	userCertSet := userToCerts[userID]
	// 	var missing []string
	// 	for certID, certName := range required {
	// 		if userCertSet == nil || userCertSet[certID] == "" {
	// 			missing = append(missing, certName)
	// 		}
	// 	}
	// 	result[userID] = missing
	// }

	// fmt.Println(len(result))

}
