from phi.aws.resources import AwsResources
from phi.docker.resources import DockerResources
from phi.k8s.resources import K8sResources

from workspace.prd.aws.s3_buckets import prd_s3_buckets
from workspace.prd.aws.eks_cluster import prd_eks_cluster_resources
from workspace.prd.aws.acm_certificate import prd_acm_certificate
from workspace.prd.airflow.aws_resources import prd_airflow_aws_resources
from workspace.prd.airflow.docker_resources import prd_airflow_image
from workspace.prd.airflow.k8s_resources import prd_airflow_apps
from workspace.settings import ws_settings

# -*- Production docker resources defined using a DockerResources object
prd_docker_resources = DockerResources(
    env=ws_settings.prd_env,
    network=ws_settings.ws_name,
    resources=[prd_airflow_image],
)

# -*- Production AWS resources defined using a AwsResources object
prd_aws_resources = AwsResources(
    env=ws_settings.prd_env,
    resources=[
        prd_s3_buckets,
        prd_airflow_aws_resources,
        prd_acm_certificate,
        prd_eks_cluster_resources,
    ],
)

# -*- Production kubernetes resources defined using a K8sResources object
prd_k8s_resources = K8sResources(
    env=ws_settings.prd_env,
    network=ws_settings.ws_name,
    apps=[prd_airflow_apps],
)
