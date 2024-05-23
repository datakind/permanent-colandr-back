import os
import sys

import docker
from dotenv import load_dotenv


load_dotenv()

container_registry = "dkdsprototypesreg01.azurecr.io"
repo = "colandr-api"
aks_cluster="dkprototypesaks"
aks_namespace ="colandr-api"
azure_resource_group="DK-DS-Prototypes"

# Script is run from top directory
docker_compose_file = "docker-compose-deploy.yml"
azure_platform = "linux/amd64"

if sys.platform == "darwin":
    print("Running on Mac")
    client = docker.DockerClient(
        base_url=f"unix:///Users/{os.getenv('LOGNAME')}/.docker/run/docker.sock "
    )
else:
    client = docker.from_env()


def run_cmd(cmd):
    """
    Executes a command in the shell and prints the command before executing.

    Args:
        cmd (str): The command to be executed.

    Returns:
        None
    """
    print(cmd)
    os.system(cmd)


def deploy():
    """
    Deploys the application to Azure using Docker Compose.

    This function performs the following steps:
    1. Logs into Azure using the 'az login' command.
    2. Logs into the Azure Container Registry using the 'az acr login' command.
    3. Stops and removes any existing containers using the 'docker compose down' command.
    4. Pulls the latest images from the Docker Compose file using the 'docker compose pull' command, for chosen architecture
    5. Builds the Docker images using the 'docker compose build' command.
    6. Tags and pushes the Docker images to the Azure Container Registry.
    7. Deploys any changes AKS services/deployments
    8. Restarts AKS services (required for when code changes but not AKS deployment files)

    """
    tags = {
        "colandr-back-api": [f"{container_registry}/{repo}", "colandr-api"],
        "colandr-back-worker": [f"{container_registry}/{repo}", "colandr-worker"],
        # Kubernetes can pull these directly, see deployment files in ./deployment
        #"postgres:16": [
        #    f"{container_registry}/{repo}",
        #    "db",
        #],
        #"axllent/mailpit:v1.17": [f"{container_registry}/{repo}", "colandr-email"],
        #"redis:7.0": [f"{container_registry}/{repo}", "colandr-broker"],
    }

    # Log in
    run_cmd("az login")
    run_cmd(f"az acr login --name {container_registry}")
    run_cmd(f"az aks get-credentials --resource-group {azure_resource_group} --name {aks_cluster}")
    run_cmd(f"docker compose -f {docker_compose_file} down")

    # Force build on linux/amd64 for Azure
    print(f"Building docker images for {azure_platform} ...")
    run_cmd(
        f"DOCKER_DEFAULT_PLATFORM={azure_platform} && docker compose -f {docker_compose_file} pull"
    )
    run_cmd(
        f"DOCKER_DEFAULT_PLATFORM={azure_platform} && docker compose -f {docker_compose_file} build"
    )

    run_cmd(f"docker compose -f {docker_compose_file} up -d --build")

    for image in tags.keys():
        print(f"Tagging {image} image ... with tag {tags[image][0]}:{tags[image][1]}")
        client.images.get(image).tag(tags[image][0], tags[image][1])
        print(f"Pushing {image} image ... to {tags[image][0]}:{tags[image][1]}")
        client.images.push(tags[image][0], tags[image][1])

    print("Deploying kubernetes any changed services and config ...")
    run_cmd(f"cd deployment && kubectl apply -f . -n {aks_namespace}")
    print("Restarting kubernetes services to pick up code changes ...")
    run_cmd(f"cd deployment && kubectl rollout restart deployment/{aks_namespace} -n {aks_namespace}")


    # If you want to bring system back up on host architecture
    #run_cmd(f"docker compose -f {docker_compose_file} down")
    #run_cmd(f"docker compose -f {docker_compose_file} pull")
    #run_cmd(f"docker compose -f {docker_compose_file} build")
    #run_cmd(f"docker compose -f {docker_compose_file} up -d")


if __name__ == "__main__":
    deploy()
