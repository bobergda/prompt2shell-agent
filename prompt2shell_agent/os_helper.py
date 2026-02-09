import os
import platform

import distro


class OSHelper:
    """Helper class for getting OS and shell information."""

    @staticmethod
    def get_os_and_shell_info():
        """Returns the OS and shell information."""
        os_name = platform.system()
        shell_name = os.path.basename(os.environ.get("SHELL", ""))
        if os_name == "Linux":
            os_name += f" {distro.name()}"
        elif os_name == "Darwin":
            os_name += f" {platform.mac_ver()[0]}"
        elif os_name == "Windows":
            os_name += f" {platform.release()}"
        return os_name, shell_name
