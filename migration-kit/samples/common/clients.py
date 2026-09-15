"""VCF 9.1 Python SDK（vcf-sdk）各元件的 client / stub_config 工廠。

需求：Python 3.10+（SDK 官方支援 3.10–3.14），`pip install vcf-sdk`。
寫法沿用官方 vcf-sdk-python-samples 的 helper，只是集中成一支。

拿到 stub_config 之後，任何一條 API 都能這樣呼叫：

    from vmware.sddc_manager.v1_client import Domains
    Domains(sddc_manager_stub_config(...)).get_domains()

Excel 逐條清單的「Python 範例」欄就是這個寫法。
"""
import requests
import urllib3

from vmware.vapi.bindings.stub import ApiClient
from vmware.vapi.lib.connect import get_requests_connector
from vmware.vapi.security.client.security_context_filter import (
    LegacySecurityContextFilter, SecurityContextFilter)
from vmware.vapi.security.http_authorization import \
    create_http_authorization_security_context
from vmware.vapi.security.oauth import create_oauth_security_context
from vmware.vapi.security.user_password import \
    create_user_password_security_context
from vmware.vapi.stdlib.client.factories import StubConfigurationFactory

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def _session(verify=False):
    s = requests.Session()
    s.verify = verify
    return s


# --------------------------------------------------------------- vCenter
def vsphere_client(server, username, password, verify=False):
    """vCenter / ESX / appliance / content / cis：base = https://<vc>/api"""
    from vmware.vapi.vsphere.client import create_vsphere_client
    return create_vsphere_client(server=server, username=username,
                                 password=password, session=_session(verify))


# ---------------------------------------------------------------- NSX
def nsx_stub_config(server, username, password, verify=False):
    """NSX Policy / MP / Global Manager 共用（HTTP Basic）。"""
    connector = get_requests_connector(session=_session(verify), msg_protocol="rest",
                                       url="https://" + server)
    connector.set_security_context(
        create_user_password_security_context(username, password))
    return StubConfigurationFactory.new_std_configuration(connector)


def nsx_policy_client(server, username, password, verify=False):
    from vcf.nsx.policy.api.v1_client import StubFactory
    return ApiClient(StubFactory(nsx_stub_config(server, username, password, verify)))


def nsx_manager_client(server, username, password, verify=False):
    from vcf.nsx.api.v1_client import StubFactory
    return ApiClient(StubFactory(nsx_stub_config(server, username, password, verify)))


# --------------------------------------------------------- SDDC Manager
class _BearerFilter(SecurityContextFilter):
    """SDDC Manager / VCF Installer：access token 過期時用 refresh token 換新的。"""

    def __init__(self, session, host_url, access_token, refresh_token, refresh_cls):
        SecurityContextFilter.__init__(self, None)
        self._session, self._host_url = session, host_url
        self._access_token, self._refresh_token = access_token, refresh_token
        self._refresh_cls = refresh_cls

    def get_max_retries(self):
        return 1

    def get_security_context(self, on_error):
        if on_error or not self._access_token:
            svc = self._refresh_cls(
                StubConfigurationFactory.new_std_configuration(
                    get_requests_connector(session=self._session, msg_protocol="rest",
                                           url=self._host_url)))
            self._access_token = svc.refresh_access_token(self._refresh_token)
        return create_oauth_security_context(self._access_token)

    def should_retry(self, error_value):
        if error_value and error_value.has_field("errorCode"):
            return error_value.get_field("errorCode").value in ("Unauthorized",
                                                                "Unauthenticated")
        return False


def sddc_manager_stub_config(server, username, password, verify=False):
    """POST /v1/tokens 換 accessToken，之後全部走 Bearer。"""
    from vmware.sddc_manager.model_client import TokenCreationSpec
    from vmware.sddc_manager.v1.tokens.access_token_client import Refresh
    from vmware.sddc_manager.v1_client import Tokens

    session, host_url = _session(verify), "https://" + server
    pair = Tokens(StubConfigurationFactory.new_std_configuration(
        get_requests_connector(session=session, msg_protocol="rest", url=host_url))
    ).create_token(token_creation_spec=TokenCreationSpec(username=username,
                                                         password=password))
    return StubConfigurationFactory.new_std_configuration(
        get_requests_connector(session=session, msg_protocol="rest", url=host_url,
                               provider_filter_chain=[
                                   _BearerFilter(session, host_url, pair.access_token,
                                                 pair.refresh_token.id, Refresh)]))


def sddc_manager_client(server, username, password, verify=False):
    from vmware.sddc_manager_client import StubFactory
    return ApiClient(StubFactory(sddc_manager_stub_config(server, username,
                                                          password, verify)))


# -------------------------------------------------------- VCF Installer
def vcf_installer_stub_config(server, username, password, verify=False):
    from vmware.vcf_installer.model_client import TokenCreationSpec
    from vmware.vcf_installer.v1.tokens.access_token_client import Refresh
    from vmware.vcf_installer.v1_client import Tokens

    session, host_url = _session(verify), "https://" + server
    pair = Tokens(StubConfigurationFactory.new_std_configuration(
        get_requests_connector(session=session, msg_protocol="rest", url=host_url))
    ).create_token(token_creation_spec=TokenCreationSpec(username=username,
                                                        password=password))
    return StubConfigurationFactory.new_std_configuration(
        get_requests_connector(session=session, msg_protocol="rest", url=host_url,
                               provider_filter_chain=[
                                   _BearerFilter(session, host_url, pair.access_token,
                                                 pair.refresh_token.id, Refresh)]))


# ------------------------------------------------------- VCF Operations
def vcf_operations_stub_config(server, username, password, verify=False):
    """base = https://<ops>/suite-api，認證標頭是 `Authorization: OpsToken <token>`。"""
    from vcf.operations.api.auth.token_client import Acquire
    from vcf.operations.model_client import UsernamePassword

    session, host_url = _session(verify), "https://%s/suite-api" % server
    token = Acquire(StubConfigurationFactory.new_std_configuration(
        get_requests_connector(session=session, msg_protocol="rest", url=host_url))
    ).acquire_token(username_password=UsernamePassword(auth_source=None,
                                                       username=username,
                                                       password=password)).token
    sec = create_http_authorization_security_context(authz_credentials=token,
                                                     authn_scheme="OpsToken")
    return StubConfigurationFactory.new_std_configuration(
        get_requests_connector(session=session, msg_protocol="rest", url=host_url,
                               provider_filter_chain=[
                                   LegacySecurityContextFilter(security_context=sec)]))


# --------------------------------------------- VCF Operations for Networks
def operations_networks_stub_config(server, token, verify=False):
    """base = https://<host>/api/ni，認證標頭是 `Authorization: NetworkInsight <token>`。"""
    sec = create_http_authorization_security_context(authz_credentials=token,
                                                     authn_scheme="NetworkInsight")
    return StubConfigurationFactory.new_std_configuration(
        get_requests_connector(session=_session(verify), msg_protocol="rest",
                               url="https://%s/api/ni" % server,
                               provider_filter_chain=[
                                   LegacySecurityContextFilter(security_context=sec)]))
