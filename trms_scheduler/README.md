### Init the project

```
$ go mod init trms_scheduler
```

### Inatall the PostgreSQL package

```
$ go get github.com/lib/pq
```

### Run each app locally
```
$ go run ./update_by_api
$ go run ./missing_training
$ go run ./before_expiry_date
```

### Change the SSL mode in production
- DEV = disable
- PROD = verify-full


## For cronjob and the Golang builder

### 1. Put them in .bashrc at /root

```
export GOPATH=$HOME/go
export GOCACHE=$HOME/.cache/go-build
export PATH=$PATH:/usr/local/go/bin:$GOPATH/bin
```

### Check

```
$ go env GOCACHE
```

### 2. Build the *update_by_api* app

```
$ cd update_by_api

update_by_api $ go build -o ./
```

### 3. Move the executable application (e.g., update_by_api) to the */usr/local/bin/* folder

```
$ mv update_by_api /usr/local/bin/
```

### 4. Add a job to the crontab

```
$ crontab -e

0 5 * * * . /etc/apache2/envvars; /usr/local/bin/update_by_api >> /[FOLDER PATH]/log/cron.log 2>&1
```