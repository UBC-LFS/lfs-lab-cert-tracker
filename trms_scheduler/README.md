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
$ go run ./trms_update_by_api
$ go run ./trms_missing_training
$ go run ./trms_before_expiry_date
$ go run ./trms_after_expiry_date
```

### Change the SSL mode in production
- DEV = disable
- PROD = require


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

### 2. Build apps

```
$ cd update_by_api
trms_update_by_api $ go build -o ./
trms_missing_training $ go build -o ./
trms_before_expiry_date $ go build -o ./
trms_after_expiry_date $ go build -o ./
```

### 3. Move the executable application (e.g., update_by_api) to the */usr/local/bin/* folder

```
$ mv trms_update_by_api /usr/local/bin/
$ mv trms_missing_training /usr/local/bin/
$ mv trms_before_expiry_date /usr/local/bin/
$ mv trms_after_expiry_date /usr/local/bin/
```

### 4. Add a job to the crontab

```
$ crontab -e

0 5 * * * . /etc/apache2/envvars; /usr/local/bin/trms_update_by_api >> /[FOLDER PATH]/log/cron.log 2>&1

30 10 1 * * . /etc/apache2/envvars; /usr/local/bin/trms_missing_training >> /[FOLDER PATH]/log/cron.log 2>&1
30 10 15 * * . /etc/apache2/envvars; /usr/local/bin/trms_missing_training >> /[FOLDER PATH]/log/cron.log 2>&1

0 9 * * * . /etc/apache2/envvars; /usr/local/bin/trms_before_expiry_date >> /[FOLDER PATH]/log/cron.log 2>&1

0 10 1 * * . /etc/apache2/envvars; /usr/local/bin/trms_after_expiry_date >> /[FOLDER PATH]/log/cron.log 2>&1
0 10 15 * * . /etc/apache2/envvars; /usr/local/bin/trms_after_expiry_date >> /[FOLDER PATH]/log/cron.log 2>&1
```