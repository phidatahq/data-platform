from pathlib import Path
from typing import Dict

from phi.app.group import AppGroup

from phi.k8s.app.airflow import (
    AirflowFlower,
    AirflowScheduler,
    AirflowWebserver,
    AirflowWorker,
    ImagePullPolicy,
)
from phi.k8s.app.postgres import PostgresDb, AppVolumeType
from phi.k8s.app.redis import Redis

from workspace.prd.aws.s3_buckets import prd_logs_s3_bucket
from workspace.prd.aws.eks_cluster import (
    services_ng_label,
    workers_ng_label,
    topology_spread_key,
    topology_spread_max_skew,
    topology_spread_when_unsatisfiable,
)
from workspace.prd.airflow.aws_resources import (
    use_rds,
    use_elasticache,
    prd_airflow_rds_db,
    prd_airflow_db_volume,
    prd_airflow_redis_volume,
    prd_airflow_redis_cluster,
)
from workspace.prd.airflow.docker_resources import prd_airflow_image

# from workspace.prd.postgres import prd_postgres_airflow_connections
from workspace.settings import ws_settings

#
# -*- Airflow Kubernetes resources
#

# -*- Airflow db: A postres instance to use as the database for airflow
prd_airflow_db = PostgresDb(
    name="af-db",
    enabled=(not use_rds),
    volume_type=AppVolumeType.AwsEbs,
    ebs_volume=prd_airflow_db_volume,
    secrets_file=ws_settings.ws_root.joinpath(
        "workspace/secrets/prd_airflow_db_secrets.yml"
    ),
    pod_node_selector=services_ng_label,
)

# -*- Airflow redis: A redis instance to use as the celery backend for airflow
prd_airflow_redis = Redis(
    name="af-redis",
    enabled=(not use_elasticache),
    volume_type=AppVolumeType.AwsEbs,
    ebs_volume=prd_airflow_redis_volume,
    command=["redis-server", "--save", "60", "1"],
    pod_node_selector=services_ng_label,
)

# -*- Settings
# waits for airflow-db to be ready before starting app
wait_for_db: bool = True
# waits for airflow-redis to be ready before starting app
wait_for_redis: bool = True
# Airflow executor to use
executor: str = "CeleryExecutor"
# Mount the workspace repo using git-sync
mount_workspace: bool = True
# Enabe git-sync to load the workspace repo from git
enable_gitsync: bool = False
# Read secrets from secrets/prd_airflow_secrets.yml
prd_airflow_secrets_file: Path = ws_settings.ws_root.joinpath(
    "workspace/secrets/prd_airflow_secrets.yml"
)
# Environment variables for airflow containers
airflow_env: Dict[str, str] = {
    "AIRFLOW__WEBSERVER__BASE_URL": f"https://airflow.{ws_settings.prd_domain}",
    "AIRFLOW__WEBSERVER__EXPOSE_CONFIG": "True",
    "AIRFLOW__WEBSERVER__EXPOSE_HOSTNAME": "True",
    "AIRFLOW__WEBSERVER__EXPOSE_STACKTRACE": "True",
    "AIRFLOW__WEBSERVER__ENABLE_PROXY_FIX": "True",
    # Create aws_default connection_id
    "AWS_DEFAULT_REGION": ws_settings.aws_region,
    "AIRFLOW_CONN_AWS_DEFAULT": "aws://",
    # Enable remote logging using s3
    "AIRFLOW__LOGGING__REMOTE_LOGGING": "True",
    "AIRFLOW__LOGGING__REMOTE_BASE_LOG_FOLDER": f"s3://{prd_logs_s3_bucket.name}/airflow",
    "AIRFLOW__LOGGING__REMOTE_LOG_CONN_ID": "aws_default",
}

# -*- Database configuration
db_user = (
    prd_airflow_rds_db.get_master_username()
    if use_rds
    else prd_airflow_db.get_db_user()
)
db_password = (
    prd_airflow_rds_db.get_master_user_password()
    if use_rds
    else prd_airflow_db.get_db_password()
)
db_schema = (
    prd_airflow_rds_db.get_db_name() if use_rds else prd_airflow_db.get_db_schema()
)
db_driver = "postgresql"
# NOTE: Add DATABASE_HOST & DATABASE_PORT env variables to secrets for RDS
db_host = None if use_rds else prd_airflow_db.get_db_host()
db_port = None if use_rds else prd_airflow_db.get_db_port()

# -*- Redis configuration
redis_password = (
    prd_airflow_redis_cluster.get_auth_token()
    if use_elasticache
    else prd_airflow_redis.get_db_password()
)
redis_schema = "0"
redis_driver = "rediss" if redis_password else "redis"
# NOTE: Add REDIS_HOST & REDIS_PORT env variables to secrets
redis_host = None if use_elasticache else prd_airflow_redis.get_db_host()
redis_port = None if use_elasticache else prd_airflow_redis.get_db_port()

# -*- Airflow webserver
prd_airflow_ws = AirflowWebserver(
    replicas=2,
    image_name=prd_airflow_image.name,
    image_tag=prd_airflow_image.tag,
    executor=executor,
    wait_for_db=wait_for_db,
    db_user=db_user,
    db_password=db_password,
    db_schema=db_schema,
    db_driver=db_driver,
    db_host=db_host,
    db_port=db_port,
    wait_for_redis=wait_for_redis,
    redis_password=redis_password,
    redis_schema=redis_schema,
    redis_driver=redis_driver,
    redis_host=redis_host,
    redis_port=redis_port,
    mount_workspace=mount_workspace,
    enable_gitsync=enable_gitsync,
    gitsync_repo=ws_settings.ws_repo,
    gitsync_ref=ws_settings.prd_branch,
    env_vars=airflow_env,
    # db_connections=prd_postgres_airflow_connections,
    secrets_file=prd_airflow_secrets_file,
    image_pull_policy=ImagePullPolicy.ALWAYS,
    use_cache=ws_settings.use_cache,
    pod_node_selector=services_ng_label,
    topology_spread_key=topology_spread_key,
    topology_spread_max_skew=topology_spread_max_skew,
    topology_spread_when_unsatisfiable=topology_spread_when_unsatisfiable,
    # Wait for scheduler to migrate airflow db -- mark as false after first run
    wait_for_db_migrate=True,
)

# -*- Airflow scheduler
prd_airflow_scheduler = AirflowScheduler(
    replicas=2,
    image_name=prd_airflow_image.name,
    image_tag=prd_airflow_image.tag,
    executor=executor,
    wait_for_db=wait_for_db,
    db_user=db_user,
    db_password=db_password,
    db_schema=db_schema,
    db_driver=db_driver,
    db_host=db_host,
    db_port=db_port,
    wait_for_redis=wait_for_redis,
    redis_password=redis_password,
    redis_schema=redis_schema,
    redis_driver=redis_driver,
    redis_host=redis_host,
    redis_port=redis_port,
    mount_workspace=mount_workspace,
    enable_gitsync=enable_gitsync,
    gitsync_repo=ws_settings.ws_repo,
    gitsync_ref=ws_settings.prd_branch,
    env_vars=airflow_env,
    secrets_file=prd_airflow_secrets_file,
    image_pull_policy=ImagePullPolicy.ALWAYS,
    use_cache=ws_settings.use_cache,
    pod_node_selector=services_ng_label,
    topology_spread_key=topology_spread_key,
    topology_spread_max_skew=topology_spread_max_skew,
    topology_spread_when_unsatisfiable=topology_spread_when_unsatisfiable,
    # Init/Upgrade airflow db on container start -- mark as false after first run
    db_migrate=True,
    # Creates airflow user: admin, pass: admin -- mark as false after first run or when using oauth
    create_airflow_admin_user=True,
)

# -*- Airflow workers serving the default & tier_1 workflows
prd_airflow_worker = AirflowWorker(
    replicas=2,
    queue_name="default,tier_1",
    image_name=prd_airflow_image.name,
    image_tag=prd_airflow_image.tag,
    executor=executor,
    wait_for_db=wait_for_db,
    db_user=db_user,
    db_password=db_password,
    db_schema=db_schema,
    db_driver=db_driver,
    db_host=db_host,
    db_port=db_port,
    wait_for_redis=wait_for_redis,
    redis_password=redis_password,
    redis_schema=redis_schema,
    redis_driver=redis_driver,
    redis_host=redis_host,
    redis_port=redis_port,
    mount_workspace=mount_workspace,
    enable_gitsync=enable_gitsync,
    gitsync_repo=ws_settings.ws_repo,
    gitsync_ref=ws_settings.prd_branch,
    env_vars=airflow_env,
    secrets_file=prd_airflow_secrets_file,
    image_pull_policy=ImagePullPolicy.ALWAYS,
    use_cache=ws_settings.use_cache,
    pod_node_selector=workers_ng_label,
    topology_spread_key=topology_spread_key,
    topology_spread_max_skew=topology_spread_max_skew,
    topology_spread_when_unsatisfiable=topology_spread_when_unsatisfiable,
    # Wait for scheduler to migrate airflow db -- mark as false after first run
    wait_for_db_migrate=True,
)

# -*- Airflow flower
prd_airflow_flower = AirflowFlower(
    replicas=1,
    image_name=prd_airflow_image.name,
    image_tag=prd_airflow_image.tag,
    executor=executor,
    wait_for_db=wait_for_db,
    db_user=db_user,
    db_password=db_password,
    db_schema=db_schema,
    db_driver=db_driver,
    db_host=db_host,
    db_port=db_port,
    wait_for_redis=wait_for_redis,
    redis_password=redis_password,
    redis_schema=redis_schema,
    redis_driver=redis_driver,
    redis_host=redis_host,
    redis_port=redis_port,
    mount_workspace=mount_workspace,
    enable_gitsync=enable_gitsync,
    gitsync_repo=ws_settings.ws_repo,
    gitsync_ref=ws_settings.prd_branch,
    env_vars=airflow_env,
    secrets_file=prd_airflow_secrets_file,
    image_pull_policy=ImagePullPolicy.ALWAYS,
    use_cache=ws_settings.use_cache,
    pod_node_selector=services_ng_label,
    topology_spread_key=topology_spread_key,
    topology_spread_max_skew=topology_spread_max_skew,
    topology_spread_when_unsatisfiable=topology_spread_when_unsatisfiable,
    # Wait for scheduler to migrate airflow db -- mark as false after first run
    wait_for_db_migrate=True,
)

# -*- AppGroup for the airflow resources
prd_airflow_apps = AppGroup(
    name="airflow",
    enabled=ws_settings.prd_airflow_enabled,
    apps=[
        prd_airflow_db,
        prd_airflow_redis,
        prd_airflow_ws,
        prd_airflow_scheduler,
        prd_airflow_worker,
        prd_airflow_flower,
    ],
)
