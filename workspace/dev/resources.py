from phi.docker.resources import DockerResources

from workspace.dev.airflow.resources import dev_airflow_apps
from workspace.dev.jupyter.resources import dev_jupyter
from workspace.dev.postgres import dev_postgres
from workspace.settings import ws_settings

# -*- Dev docker resources defined using a DockerResources object
dev_docker_resources = DockerResources(
    env=ws_settings.dev_env,
    network=ws_settings.ws_name,
    apps=[dev_airflow_apps, dev_jupyter, dev_postgres],
)
