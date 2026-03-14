import json
import shutil
from pathlib import Path

# Import the professional paths from your new config
from src.core.config import (
    USER_CONFIG_PATH, 
    STAGING_DIR, 
    ARDUINO_CLI_PATH
)
from src.services.arduino_service import ArduinoService

class ProjectContext:
    """
    Manages the current active project files and Wokwi integration.
    This is the 'Source of Truth' for what the user is currently editing.
    """
    
    def __init__(self):
        # Initialize the Arduino Service with the path from config
        self.arduino_service = ArduinoService(cli_path=ARDUINO_CLI_PATH)

    def get_active_project_path(self) -> Path:
        """
        Returns the last used project folder from user_config.json.
        If no config exists, defaults to the STAGING_DIR (temporary area).
        """
        if USER_CONFIG_PATH.exists():
            try:
                data = json.loads(USER_CONFIG_PATH.read_text())
                path = Path(data.get("last_project_folder", ""))
                if path.exists():
                    return path.resolve()
            except (json.JSONDecodeError, KeyError, Exception):
                pass
        
        return STAGING_DIR.resolve()

    def save_active_project_path(self, path: Path):
        """Updates user_config.json with the new project location."""
        config_data = {"last_project_folder": str(path.resolve())}
        USER_CONFIG_PATH.write_text(json.dumps(config_data, indent=2), encoding='utf-8')

    def update_staging_from_wokwi(self, files: dict):
        """
        Takes files from Wokwi (dict of filename: content) and 
        overwrites the staging area.
        """
        for filename, content in files.items():
            file_path = STAGING_DIR / filename
            file_path.write_text(content, encoding='utf-8')
        print(f"🚀 Staging updated: {STAGING_DIR}")

    def export_staging_to_user_path(self, target_folder: Path):
        """
        Copies the temporary Wokwi files to a permanent user-selected folder.
        """
        target_folder.mkdir(parents=True, exist_ok=True)
        for item in STAGING_DIR.iterdir():
            if item.is_file():
                shutil.copy2(item, target_folder / item.name)
        
        # Update the config so the app reopens this folder next time
        self.save_active_project_path(target_folder)

# Singleton instance to be imported by UI and other logic
project_context = ProjectContext()
# Helper for direct access to the service
arduino_service = project_context.arduino_service
