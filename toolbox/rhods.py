import sys

from toolbox._common import RunAnsibleRole


ODS_CATALOG_IMAGE_DEFAULT = "quay.io/modh/qe-catalog-source"
ODS_CATALOG_IMAGE_VERSION_DEFAULT = "v160-8"
class RHODS:
    """
    Commands relating to RHODS
    """

    @staticmethod
    def deploy_ods(catalog_image=ODS_CATALOG_IMAGE_DEFAULT,
                   version=ODS_CATALOG_IMAGE_VERSION_DEFAULT):
        """
        Deploy ODS operator from its custom catalog

        Args:
          catalog_image: Optional. Container image containing ODS bundle.
          version: Optional. Version (catalog image tag) of ODS to deploy.
        """

        opts = {
            "rhods_deploy_ods_catalog_image": catalog_image,
            "rhods_deploy_ods_catalog_image_tag": version,
        }

        return RunAnsibleRole("rhods_deploy_ods", opts)

    @staticmethod
    def test_jupyterlab(username_prefix, user_count: int, secret_properties_file):
        """
        Test RHODS JupyterLab notebooks

        Args:
          user_count: Number of users to run in parallel
          secret_properties_file: Path of a file containing the properties of LDAP secrets. (See 'deploy_ldap' command)

        """
        opts = {
            "rhods_test_jupyterlab_username_prefix": username_prefix,
            "rhods_test_jupyterlab_user_count": user_count,
            "rhods_test_jupyterlab_secret_properties": secret_properties_file,
        }
        return RunAnsibleRole("rhods_test_jupyterlab", opts)

    @staticmethod
    def undeploy_ods():
        """
        Undeploy ODS operator
        """

        return RunAnsibleRole("rhods_undeploy_ods")

    @staticmethod
    def deploy_ldap(username_prefix, username_count: int, secret_properties_file):
        """
        Deploy OpenLDAP and LDAP Oauth

        Example of secret properties file:

        user_password=passwd
        admin_password=adminpasswd

        Args:
            username_prefix: Prefix for the creation of the users (suffix is 0..username_count)
            username_count: Number of users to create.
            secret_properties_file: Path of a file containing the properties of LDAP secrets.
        """

        opts = {
            "rhods_deploy_ldap_username_prefix": username_prefix,
            "rhods_deploy_ldap_username_count": username_count,
            "rhods_deploy_ldap_secret_properties": secret_properties_file,
        }

        return RunAnsibleRole("rhods_deploy_ldap", opts)

    @staticmethod
    def undeploy_ldap():
        """
        Undeploy OpenLDAP and LDAP Oauth
        """

        return RunAnsibleRole("rhods_undeploy_ldap")
