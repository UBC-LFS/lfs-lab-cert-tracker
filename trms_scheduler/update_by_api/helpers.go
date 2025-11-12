package main

import (
	"fmt"
	"strings"
	"time"
)

func getExpiryDate(completionDate string, traingID int, trainings map[int]map[string]interface{}) string {
	t, err := time.Parse(time.RFC3339, completionDate)
	if err != nil {
		fmt.Println("Error parsing date:", err)
		return ""
	}

	expiry_in_years := int(trainings[traingID]["expiry_in_years"].(int64))
	newTime := t.AddDate(expiry_in_years, 0, 0)
	newDateStr := newTime.Format("2006-01-02")
	return newDateStr
}

func findValue(m map[string]int, target string) (int, bool) {
	for key, val := range m {
		for _, part := range strings.Split(key, ",") {
			if strings.TrimSpace(part) == target {
				return val, true
			}
		}
	}
	return 0, false
}

func getKeys(items map[int][]string) []int {
	var keys []int
	for key := range items {
		if len(items[key]) > 0 {
			keys = append(keys, key)
		}
	}
	return keys
}

// Convert a slice to a set
func toSet[T comparable](arr []T) map[T]struct{} {
	set := make(map[T]struct{})
	for _, v := range arr {
		set[v] = struct{}{}
	}
	return set
}

// Union of two sets
func union[T comparable](a, b map[T]struct{}) map[T]struct{} {
	union := make(map[T]struct{})
	for k := range a {
		union[k] = struct{}{}
	}
	for k := range b {
		union[k] = struct{}{}
	}
	return union
}
