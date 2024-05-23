# Quick start

Install Azure CLI and Kubernetes CLI, as instructed [here](https://learn.microsoft.com/en-us/azure/aks/tutorial-kubernetes-deploy-cluster?tabs=azure-cli).

Then log into Azure ...

`az login`

Then log into [the cluster](https://portal.azure.com/#@DataKindO365.onmicrosoft.com/resource/subscriptions/21fe0672-504b-4b05-b7e1-a154142c9fd4/resourceGroups/dk-ds-prototypes/providers/Microsoft.ContainerService/managedClusters/dkprototypesaks/workloads) ...

`az aks get-credentials --resource-group DK-DS-Prototypes --name dkprototypesaks`

Then all  the commands mentioned the useful commands section below should work. 

So a workflow would look like ...

1. git checkout matt-azure-kubernetes-service-deployment (it's on a branch for now)
2. Do some work, change some code, or adjust the Kubernetes configuration files in `./deployment`
3. Run deployment script to push to container registry: `python3 deploy_azure.py`
4. Go to the URL, to find it click under "Services and Ingresses" in the Azure portal


# Useful commands

To Deploy using kubectl ...

One service:

`kubectl apply -f env-configmap.yaml -n colandr-api`

All if in a directory (eg ../deployment)

`kubectl apply -f . -n colandr-api`

Restart all sevices (useful if the code is the only change, ie Kubernetes config files haven't changed) ...

`kubectl rollout restart deployment/colandr-api -n colandr-api`

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