import os
import sys
import platform

from typing import List, ClassVar
from pathlib import Path
from pydantic import InstanceOf, Field, field_validator, model_validator
from rich import print

from django.conf import settings

from plugantic.base_plugin import BasePlugin
from plugantic.base_configset import BaseConfigSet, ConfigSectionName
from plugantic.base_hook import BaseHook


###################### Config ##########################


class ShellConfig(BaseConfigSet):
    section: ClassVar[ConfigSectionName] = 'SHELL_CONFIG'

    DEBUG: bool                         = Field(default=False)
    
    IS_TTY: bool                        = Field(default=sys.stdout.isatty())
    USE_COLOR: bool                     = Field(default=lambda c: c.IS_TTY)
    SHOW_PROGRESS: bool                 = Field(default=lambda c: (c.IS_TTY and platform.system() != 'darwin'))  # progress bars are buggy on mac, disable for now
    
    IN_DOCKER: bool                     = Field(default=False)
    IN_QEMU: bool                       = Field(default=False)
    
    PUID: int                           = Field(default=os.getuid())
    PGID: int                           = Field(default=os.getgid())
    
    @model_validator(mode='after')
    def validate_not_running_as_root(self):
        attempted_command = ' '.join(sys.argv[:3])
        if self.PUID == 0 and attempted_command != 'setup':
            # stderr('[!] ArchiveBox should never be run as root!', color='red')
            # stderr('    For more information, see the security overview documentation:')
            # stderr('        https://github.com/ArchiveBox/ArchiveBox/wiki/Security-Overview#do-not-run-as-root')
            print('[red][!] ArchiveBox should never be run as root![/red]', file=sys.stderr)
            print('    For more information, see the security overview documentation:', file=sys.stderr)
            print('        https://github.com/ArchiveBox/ArchiveBox/wiki/Security-Overview#do-not-run-as-root', file=sys.stderr)
            
            if self.IN_DOCKER:
                print('[red][!] When using Docker, you must run commands with [green]docker run[/green] instead of [yellow3]docker exec[/yellow3], e.g.:', file=sys.stderr)
                print('        docker compose run archivebox {attempted_command}', file=sys.stderr)
                print(f'        docker run -it -v $PWD/data:/data archivebox/archivebox {attempted_command}', file=sys.stderr)
                print('        or:', file=sys.stderr)
                print(f'        docker compose exec --user=archivebox archivebox /bin/bash -c "archivebox {attempted_command}"', file=sys.stderr)
                print(f'        docker exec -it --user=archivebox <container id> /bin/bash -c "archivebox {attempted_command}"', file=sys.stderr)
            raise SystemExit(2)
        
        return self

SHELL_CONFIG = ShellConfig()


class StorageConfig(BaseConfigSet):
    section: ClassVar[ConfigSectionName] = 'STORAGE_CONFIG'

    OUTPUT_PERMISSIONS: str             = Field(default='644')
    RESTRICT_FILE_NAMES: str            = Field(default='windows')
    ENFORCE_ATOMIC_WRITES: bool         = Field(default=True)

STORAGE_CONFIG = StorageConfig()


class GeneralConfig(BaseConfigSet):
    section: ClassVar[ConfigSectionName] = 'GENERAL_CONFIG'
        
    TAG_SEPARATOR_PATTERN: str          = Field(default=r'[,]')


GENERAL_CONFIG = GeneralConfig()


class ServerConfig(BaseConfigSet):
    section: ClassVar[ConfigSectionName] = 'SERVER_CONFIG'

    SECRET_KEY: str                     = Field(default=None)
    BIND_ADDR: str                      = Field(default=lambda: ['127.0.0.1:8000', '0.0.0.0:8000'][SHELL_CONFIG.IN_DOCKER])
    ALLOWED_HOSTS: str                  = Field(default='*')
    CSRF_TRUSTED_ORIGINS: str           = Field(default=lambda c: 'http://localhost:8000,http://127.0.0.1:8000,http://0.0.0.0:8000,http://{}'.format(c.BIND_ADDR))
    
    SNAPSHOTS_PER_PAGE: int             = Field(default=40)
    FOOTER_INFO: str                    = Field(default='Content is hosted for personal archiving purposes only.  Contact server owner for any takedown requests.')
    CUSTOM_TEMPLATES_DIR: Path          = Field(default=None)

    PUBLIC_INDEX: bool                  = Field(default=True)
    PUBLIC_SNAPSHOTS: bool              = Field(default=True)
    PUBLIC_ADD_VIEW: bool               = Field(default=False)
    
    ADMIN_USERNAME: str                 = Field(default=None)
    ADMIN_PASSWORD: str                 = Field(default=None)
    REVERSE_PROXY_USER_HEADER: str      = Field(default='Remote-User')
    REVERSE_PROXY_WHITELIST: str        = Field(default='')
    LOGOUT_REDIRECT_URL: str            = Field(default='/')
    PREVIEW_ORIGINALS: bool             = Field(default=True)
    
SERVER_CONFIG = ServerConfig()


class ArchivingConfig(BaseConfigSet):
    section: ClassVar[ConfigSectionName] = 'ARCHIVING_CONFIG'
    
    ONLY_NEW: bool                      = Field(default=True)
    
    TIMEOUT: int                        = Field(default=60)
    MEDIA_TIMEOUT: int                  = Field(default=3600)

    MEDIA_MAX_SIZE: str                 = Field(default='750m')
    RESOLUTION: str                     = Field(default='1440,2000')
    CHECK_SSL_VALIDITY: bool            = Field(default=True)
    USER_AGENT: str                     = Field(default='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 ArchiveBox/{VERSION} (+https://github.com/ArchiveBox/ArchiveBox/)')
    COOKIES_FILE: Path | None           = Field(default=None)
    
    URL_DENYLIST: str                   = Field(default=r'\.(css|js|otf|ttf|woff|woff2|gstatic\.com|googleapis\.com/css)(\?.*)?$', alias='URL_BLACKLIST')
    URL_ALLOWLIST: str | None           = Field(default=None, alias='URL_WHITELIST')
    
    # GIT_DOMAINS: str                    = Field(default='github.com,bitbucket.org,gitlab.com,gist.github.com,codeberg.org,gitea.com,git.sr.ht')
    # WGET_USER_AGENT: str                = Field(default=lambda c: c['USER_AGENT'] + ' wget/{WGET_VERSION}')
    # CURL_USER_AGENT: str                = Field(default=lambda c: c['USER_AGENT'] + ' curl/{CURL_VERSION}')
    # CHROME_USER_AGENT: str              = Field(default=lambda c: c['USER_AGENT'])
    # CHROME_USER_DATA_DIR: str | None    = Field(default=None)
    # CHROME_TIMEOUT: int                 = Field(default=0)
    # CHROME_HEADLESS: bool               = Field(default=True)
    # CHROME_SANDBOX: bool                = Field(default=lambda: not SHELL_CONFIG.IN_DOCKER)

    @field_validator('TIMEOUT', mode='after')
    def validate_timeout(cls, v):
        print(f'[red][!] Warning: TIMEOUT is set too low! (currently set to TIMEOUT={v} seconds)[/red]', file=sys.stderr)
        print('    You must allow *at least* 5 seconds for indexing and archive methods to run succesfully.', file=sys.stderr)
        print('    (Setting it to somewhere between 30 and 3000 seconds is recommended)', file=sys.stderr)
        print(file=sys.stderr)
        print('    If you want to make ArchiveBox run faster, disable specific archive methods instead:', file=sys.stderr)
        print('        https://github.com/ArchiveBox/ArchiveBox/wiki/Configuration#archive-method-toggles', file=sys.stderr)
        print(file=sys.stderr)
        return v
    
    @field_validator('CHECK_SSL_VALIDITY', mode='after')
    def validate_check_ssl_validity(cls, v):
        """SIDE EFFECT: disable "you really shouldnt disable ssl" warnings emitted by requests"""
        if not v:
            import requests
            import urllib3
            requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        return v

ARCHIVING_CONFIG = ArchivingConfig()


class SearchBackendConfig(BaseConfigSet):
    section: ClassVar[ConfigSectionName] = 'SEARCH_BACKEND_CONFIG'

    USE_INDEXING_BACKEND: bool          = Field(default=True)
    USE_SEARCHING_BACKEND: bool         = Field(default=True)
    
    SEARCH_BACKEND_ENGINE: str          = Field(default='ripgrep')
    SEARCH_PROCESS_HTML: bool           = Field(default=True)
    SEARCH_BACKEND_TIMEOUT: int         = Field(default=10)

SEARCH_BACKEND_CONFIG = SearchBackendConfig()


class ConfigPlugin(BasePlugin):
    app_label: str = 'config'
    verbose_name: str = 'Configuration'

    hooks: List[InstanceOf[BaseHook]] = [
        SHELL_CONFIG,
        GENERAL_CONFIG,
        STORAGE_CONFIG,
        SERVER_CONFIG,
        ARCHIVING_CONFIG,
        SEARCH_BACKEND_CONFIG,
    ]


PLUGIN = ConfigPlugin()
PLUGIN.register(settings)
DJANGO_APP = PLUGIN.AppConfig
