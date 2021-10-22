package main

import (
	"bufio"
	"encoding/json"
	"io/ioutil"
	"log"
	"os"
	"strconv"
	"sync"
	"time"
)

type JsonObject struct {
	author     string
	createdUtc int
}

type JsonFile struct {
	fileName string
	jsonObjects []JsonObject
}

func main() {

	before := time.Now()

	// have workers read in all the files in the dataFiles directory
	fileInfos, _ := ioutil.ReadDir("./dataFiles")

	fileNameChannel := make(chan string, len(fileInfos))

	jsonFileChannel := make(chan JsonFile, len(fileInfos))

	for element := range fileInfos{
		fileNameChannel <- fileInfos[element].Name()
	}

	close(fileNameChannel)

	var secondGroup sync.WaitGroup

	go func() {
		for jsonFile := range jsonFileChannel {
			jsonFile := jsonFile
			go func() {
				secondGroup.Add(1)
				makeJsonFile(jsonFile)
				secondGroup.Done()
			}()
		}
	}()

	for item := range fileNameChannel {
		item := item
		processFile(item, jsonFileChannel)
	}

	close(jsonFileChannel)

	secondGroup.Wait()

	after := time.Now()

	print("Time elapsed: " + (after.Sub(before).String()) + "\n")
}

func processFile(filename string, jsonFiles chan JsonFile) {
	file, err := os.Open("./dataFiles/" + filename)
	checkError(err)
	scanner := bufio.NewScanner(file)
	scanner.Split(bufio.ScanLines)
	var jsonFile = JsonFile{filename, make([]JsonObject, 0)}
	fileContentsChan := make(chan string)
	jsonObjectsChan := make(chan JsonObject)
	var group sync.WaitGroup
	group.Add(1)

	go func() {
		defer close(fileContentsChan)
		for scanner.Scan() {
			jsonString := scanner.Text()
			fileContentsChan <- jsonString
		}
		group.Done()
	}()

	go func() {
		for {
			res, ok := <-fileContentsChan
			if ok == false {
				break
			} else {
				group.Add(1)
				go func() {
					processJsonString(res, jsonObjectsChan)
					group.Done()
				}()
			}
		}
		time.Sleep(5)
		close(jsonObjectsChan)
	}()

	var jsonGroup sync.WaitGroup

	jsonGroup.Add(1)
	go func() {
		for item := range jsonObjectsChan {
			item := item
			jsonFile.jsonObjects = append(jsonFile.jsonObjects, item)
		}
		jsonGroup.Done()
	}()



	print("Waiting for group to be done! FileName: " + filename + " \n")
	group.Wait()
	print("Processing Json now! Filename: " + filename + " \n")
	jsonGroup.Wait()
	print("all threads done for Filename: " + filename + "\n")

	jsonFiles<-jsonFile
}

func makeJsonFile(jsonFile JsonFile) {
	print("creating file: " + jsonFile.fileName + "\n")
	jsonObjects := jsonFile.jsonObjects
	file, err := os.Create("./jsonFiles/" + jsonFile.fileName + ".json")
	if err != nil {
		return
	}
	w := bufio.NewWriter(file)
	for integer := range jsonObjects {
		jsonObject := jsonObjects[integer]
		_, _ = w.WriteString("{\"author\":\"" + jsonObject.author + "\",\"created_utc\":\"" + strconv.Itoa(jsonObject.createdUtc) + "\"}\n")
	}

	err = w.Flush()
	if err != nil {
		return
	}
	print("Wrote file: " + jsonFile.fileName + "\n")
	checkError(err)
}

func processJsonString(jsonString string, jsonObjects chan JsonObject) {
	var jsonMap map[string]interface{}
	err := json.Unmarshal([]byte(jsonString), &jsonMap)
	checkError(err)
	var author string
	var createdDateTime int
	author = jsonMap["author"].(string)
	i := jsonMap["created_utc"]
	switch i.(type) {
	case string:
		createdDateTime, _ = strconv.Atoi(i.(string))
	case float64:
		createdDateTime = int(i.(float64))
	default:
		print("createdDatetime is 0")
		createdDateTime = 0
	}
	checkError(err)
	if author != "[deleted]" {
		js := JsonObject{author, createdDateTime}
		jsonObjects <- js
	}
}

func checkError(err error) {
	if err != nil {
		log.Fatal(err)
	}
}

