"""Installation, Host configuration, repair, and uninstall support."""

from .manager import (
    InstallationError,
    configure_host,
    installation_doctor,
    installation_plan,
    installation_status,
    mcp_check,
    plugin_check,
    repair_installation,
    uninstall_installation,
)

__all__ = [
    "InstallationError",
    "configure_host",
    "installation_doctor",
    "installation_plan",
    "installation_status",
    "mcp_check",
    "plugin_check",
    "repair_installation",
    "uninstall_installation",
]
