# Setting up AKS for colandr-api

Below is a brief log and list of useful commands I worked through in deploying to Azure Kubernetes service.

PLEASE NOTE: THIS IS ONLY A BASIC DEPLOYMENT, FOLLOWUP IS NEEDED TO SECURE THE SITE

Specifically, outstanding steps are:

- Adjust passwords, and save them as AKS secrets instead of in the files in folder `./kubernetes`
- For consistent, names need to be wteaked so they all start with 'colandr-`
- Cost analysis, this might be pricey!
- Refactoring of this into GitHub actions for CI/CD
- Removal of this branch 

# Setup log

My first time with AKS, so some steps may not be optimal, but here is what I did ...

I first did [this tutorial](https://learn.microsoft.com/en-us/azure/aks/tutorial-kubernetes-deploy-cluster?tabs=azure-cli). 

This tutorial gets you set up with Azure and Kubernetes CLI.

I then did the following ...

1. Created an AKS service

```
az aks create \
    --resource-group  DK-DS-Prototypes \
    --name dkprototypesaks \
    --node-count 2 \
    --generate-ssh-keys \
    --attach-acr dkdsprototypesreg01
```


2. Attached a container registry (where the DOcker images will come from)

`az aks update  --attach-acr dkdsprototypesreg01 --resource-group  DK-DS-Prototypes --name dkprototypesaks`

3. Set up credentials

```
az aks get-credentials --resource-group DK-DS-Prototypes --name dkprototypesaks

az acr list --resource-group DK-DS-Prototypes --query "[].{acrLoginServer:loginServer}" --output table
```

4. Created namespace in portal colandr-api

5. Enabled insights under 'Insights' on AKS to get granular logging

6. Converted Docker compose to Kubernetes services and deployment files

Installed [kompose](https://kompose.io/), then ran

`kompose convert`

This creates a set of Kubernetes files. These are used to deploy services to AKS.

These can be sent to AKS with `kubectl applf -f <filename>`, I did this a lot. 

```
kubectl apply -f worker-deployment.yaml -n colandr-api
kubectl apply -f worker-service.yaml -n colandr-api
kubectl apply -f broker-service.yaml -n colandr-api
kubectl apply -f broker-deployment.yaml -n colandr-api
kubectl apply -f broker-data-persistentvolumeclaim.yaml -n colandr-api
kubectl apply -f api-service.yaml -n colandr-api
kubectl apply -f api-deployment.yaml -n colandr-api
kubectl apply -f api-cm0-configmap.yaml -n colandr-api
kubectl apply -f db-deployment.yaml -n colandr-api
kubectl apply -f db-service.yaml -n colandr-api
kubectl apply -f db-data-persistentvolumeclaim.yaml -n colandr-api
kubectl apply -f db-data-persistentvolumeclaim.yaml -n colandr-api 
kubectl apply -f env-configmap.yaml -n colandr-api 
```

You can also
do `-f .` to do all files in a directory. You can also restart if debgging the docker build, even 
when deployment hasn't changed

`kubectl rollout restart deployment/colandr-api -n colandr-api`

NOTE: For now, all files in sub-folder 'kubernetes', these would need to be moved according to devops setup.

7. Wrote a deploy script

For locally built images (api and worker) we need to push to Azure container registry. I Wrote
a simple script to tag and push these images. 

**IMPORTANT:** Azure expects amd64 images, so the script forces this build but using `docker-compose-deploy.yaml`.

I ran the script .... a LOT.

8. Created some secrets

`create secret generic colandr-db-password --from-literal=password='<SECRET>'`
`create secret generic colandr-database-uri --from-literal=password='<SECRET>'`

8. Adjusted the AKS files

The files created by kompose did not work out of the box, due to idiosyncracies on colandr-api. hereis what I adjusted ...

- Edited worker to add ports directive, otherwise service not created
- Added registry image dkdsprototypesreg01.azurecr.io/colandr-api:api and one for worker for worker and api in `docker compose-deploy.yml`
- Changed 'arg' to 'command' on deployment for worker
- Split `Dockerfile` into `Dockerfile.worker` and `Dockerfile.api` so fglask environment didn't pollute celery setup
- Removed mount for api
- To avoid image caching, set imagePullPolicy: Always
- Temporarily set CMD ["tail", "-f", "/dev/null"], so I could debug the running container's environment for the API
- Was getting error from running FLask about not finding Python package psycopg2, terrible error, it was actually that DB URI was incorrect
- Edited db-deployment.yaml to get POSTGRES from env-configmap.yaml. This is not ideal, should create AKS secrets and get from there
- Added load balancer directive to api service to get public IP
- Made PGDATA subdirectory of mount point so folder was empty

# Useful commands

Get list of pods, you need the name for getting logs and exec commands ...

`kubectl get pods -n colandr-api`

Get logs ...

`kubectl logs <POD>  -n colandr-api`

Get logs in one line of any that have word 'api' in them ...

`kubectl get pods --no-headers -o custom-columns=":metadata.name" -n colandr-api | grep api | xargs -I{} kubectl logs {} -n colandr-api`

Get details on pods ...

```
kubectl describe pod <POD> -n colandr-api
kubectl describe configmap env -n colandr-api
```

Test a pushed image ...

```
docker compose -f docker-compose-deploy.yml up -d --build 
docker exec -it colandr-worker /bin/bash
docker tag colandr-back-worker dkdsprototypesreg01.azurecr.io/colandr-api:worker
docker exec -it dkdsprototypesreg01.azurecr.io/colandr-api:worker /bin/bash
docker push dkdsprototypesreg01.azurecr.io/colandr-api:worker
docker pull dkdsprototypesreg01.azurecr.io/colandr-api:worker
docker run --env-file .env -it -e "COLANDR_DATABASE_URI=postgresql+psycopg://${COLANDR_DB_USER}:${COLANDR_DB_PASSWORD}@host.docker.internal:5432/${COLANDR_DB_NAME}" --rm dkdsprototypesreg01.azurecr.io/colandr-api:worker /bin/bash
```

.... Then run the docker compose 'command' or entry point for this container, eg celery --app=make_celery.celery_app worker --loglevel=info

Run a container ...

`kubectl run -i --tty --rm debug --image=dkdsprototypesreg01.azurecr.io/colandr-api:worker -- bash`

To Get running container's env ...

`kubectl exec -it  worker-98b947488-bdhhb  -n colandr-api -- env`

Trick to get a failing container up, so you can exec into it and debug, temporarily change the CMD in the Dockerfile to ...

`CMD ["tail", "-f", "/dev/null"]`

You can then run the command interactively.