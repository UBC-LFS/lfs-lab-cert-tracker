build-image:
	docker build -t lfs-lab-cert-tracker .

run-container:
	docker run -p 8000:8000 lfs-lab-cert-tracker
