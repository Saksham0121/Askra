"""
Application Bootstrap.
"""

from src.services.startup_service import StartupService


# Starts the application and performs initial setup.
class Bootstrap:
    """
    Bootstraps the application.
    """

    # Initializes the startup service object.
    def __init__(self) -> None:
        self.startup_service = StartupService()

    # Starts the application and initializes services
    def run(self) -> None:
        """
        Start the application.
        """

        self.startup_service.initialize()