import ssl

from django.conf import settings
from django.core.mail.backends.smtp import EmailBackend
from django.utils.functional import cached_property


class ConfigurableTLSBackend(EmailBackend):
    @cached_property
    def ssl_context(self):
        if getattr(settings, "EMAIL_SSL_VERIFY", True):
            return super().ssl_context
        return ssl._create_unverified_context()
