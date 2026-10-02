"""Authentication fails closed; dev bypass cannot reach production."""

import os
import unittest
from unittest import mock

from fastapi import HTTPException
from starlette.requests import Request

from app.auth import AuthConfigError, auth_mode, identity_from_request


def request(headers=None):
    raw = [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]
    return Request({"type": "http", "method": "GET", "path": "/", "headers": raw, "query_string": b""})


class AuthModeTest(unittest.TestCase):
    def test_unset_means_unconfigured(self):
        self.assertEqual(auth_mode({}), "")

    def test_dev_bypass_refused_outside_development(self):
        for env in ({"DEV_BYPASS_AUTH": "true"}, {"DEV_BYPASS_AUTH": "true", "GROUNDED_ENV": "production"},
                    {"AUTH_MODE": "dev"}, {"AUTH_MODE": "dev", "GROUNDED_ENV": "development"}):
            with self.assertRaises(AuthConfigError, msg=env):
                auth_mode(env)
        self.assertEqual(auth_mode({"DEV_BYPASS_AUTH": "true", "GROUNDED_ENV": "development"}), "dev")

    def test_unknown_mode_refused(self):
        with self.assertRaises(AuthConfigError):
            auth_mode({"AUTH_MODE": "none"})


class IdentityTest(unittest.TestCase):
    def test_unconfigured_returns_503(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(HTTPException) as caught:
                identity_from_request(request())
        self.assertEqual(caught.exception.status_code, 503)

    def test_trusted_header_requires_proxy_secret(self):
        secret = "s" * 40
        env = {"AUTH_MODE": "trusted-header", "AUTH_PROXY_SECRET": secret}
        with mock.patch.dict(os.environ, env, clear=True):
            with self.assertRaises(HTTPException) as caught:
                identity_from_request(request({"X-Authenticated-User": "a@corp.internal"}))
            self.assertEqual(caught.exception.status_code, 401)
            with self.assertRaises(HTTPException):
                identity_from_request(request({"X-Authenticated-User": "a@corp.internal", "X-Proxy-Secret": "wrong"}))
            identity = identity_from_request(request({"X-Authenticated-User": "a@corp.internal", "X-Proxy-Secret": secret}))
        self.assertEqual(identity.email, "a@corp.internal")

    def test_short_proxy_secret_is_misconfiguration(self):
        with mock.patch.dict(os.environ, {"AUTH_MODE": "trusted-header", "AUTH_PROXY_SECRET": "short"}, clear=True):
            with self.assertRaises(HTTPException) as caught:
                identity_from_request(request({"X-Authenticated-User": "a", "X-Proxy-Secret": "short"}))
        self.assertEqual(caught.exception.status_code, 503)

    def test_oidc_requires_bearer(self):
        with mock.patch.dict(os.environ, {"AUTH_MODE": "oidc"}, clear=True):
            with self.assertRaises(HTTPException) as caught:
                identity_from_request(request())
        self.assertEqual(caught.exception.status_code, 401)

    def test_oidc_jwks_must_be_internal(self):
        from app import auth

        auth._JWKS_CACHE.clear()
        env = {"AUTH_MODE": "oidc", "OIDC_ISSUER": "i", "OIDC_AUDIENCE": "a", "OIDC_JWKS_URL": "https://login.example.com/jwks"}
        with mock.patch.dict(os.environ, env, clear=True):
            from grounded.policy import EgressError

            with self.assertRaises((EgressError, HTTPException)):
                auth._jwks()


if __name__ == "__main__":
    unittest.main()
