#
# This Python script is used to tag and push Docker images to Azure Container Registry.
#
# Befor running you'll need to have the Azure command line tools installed and logged in. To log in ..
#
#  az login
#
#  az acr login --name dkcontainerregistryus
#

# 0. docker compose up -d, made note of image names, updated deploy_azure.py which I copied over from another repo I did
# 1. az webapp create --resource-group DK-DS-Prototypes --plan DK-DS-Prototypes --name colandr-api --multicontainer-config-type compose --multicontainer-config-file compose.yml 
# 2. Navigated to app in Azure portal and environment variables as sent to me by Larry. I changed 'localhost' to be 'db'
#    As this would be the hostname on the docker network
# 3. In portal went to deployment center and configured container registry
# 4. Pasted in docker-compose.yml
# 5. Edited it to change ...
#      - images in compose directives to point at registry, e.g. colandr.azurecr.io/colandr-api:db. These were set by deploy script.
#      - Commented out any bind mounts and builds
#      - Changed API Port to 80     
# 7. Copied web webhook URL
# 8. Created web hook under resources in colandr container service
# 9. Created docker-compose-deploy.yml to use linux/amd64 platform (on a Mac push fails)
# 10. Modified deploy_azure.py to push images to registry and use docker-compose-deploy.yml
# 11. Ran deploy_azure.py
# 12. Went to web app, used Developer tools > Kudo to tail logs in LogFile
# 13. Checked site was up using https://colandr-api.azurewebsites.net/


# If you want local filesystem storage, you can use  ${WEBAPP_STORAGE_HOME}



import os
import sys

import docker
from dotenv import load_dotenv

load_dotenv()

container_registry = "dkdsprototypesreg01.azurecr.io"
repo = "colandr-api"

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
    4. Pulls the latest images from the Docker Compose file using the 'docker compose pull' command.
    5. Builds the Docker images using the 'docker compose build' command.
    6. Tags and pushes the Docker images to the Azure Container Registry.
    7. Reverts to the host architecture by stopping and removing containers again.
    8. Pulls the latest images from the Docker Compose file.
    9. Builds and starts the containers using the 'docker compose up -d' command.
    10. Prints the URL to trigger the deployment.

    Note: The variables 'container_registry', 'repo', 'azure_platform', and 'docker_compose_file'
    should be defined before calling this function.
    """
    tags = {
        "colandr-back-api": [f"{container_registry}/{repo}", "colandr-api"],
        "colandr-back-worker": [f"{container_registry}/{repo}", "colandr-worker"],
        #"postgres:16": [
        #    f"{container_registry}/{repo}",
        #    "db",
        #],
        #"axllent/mailpit:v1.17": [f"{container_registry}/{repo}", "colandr-email"],
        #"redis:7.0": [f"{container_registry}/{repo}", "colandr-broker"],
    }

    run_cmd("az login")
    run_cmd(f"az acr login --name {container_registry}")

    run_cmd(f"docker compose -f {docker_compose_file} down")
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

    #run_cmd(f"docker compose -f {docker_compose_file} down")
    #run_cmd(f"docker compose -f {docker_compose_file} pull")
    #run_cmd(f"docker compose -f {docker_compose_file} build")
    #run_cmd(f"docker compose -f {docker_compose_file} up -d")


if __name__ == "__main__":
    deploy()
