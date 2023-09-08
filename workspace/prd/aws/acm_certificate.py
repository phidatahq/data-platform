from phi.aws.resource.acm import AcmCertificate

from workspace.settings import ws_settings

# -*- ACM certificate for production domain
prd_acm_certificate = AcmCertificate(
    name=f"{ws_settings.prd_key}-acm-cert",
    enabled=False,
    domain_name=ws_settings.prd_domain,
    subject_alternative_names=[f"*.{ws_settings.prd_domain}"],
    # Store the certificate ARN in the certificate_summary_file
    store_cert_summary=True,
    certificate_summary_file=ws_settings.ws_root.joinpath(
        "workspace", "aws", "acm", ws_settings.prd_domain
    ),
    skip_delete=True,
    save_output=True,
)
