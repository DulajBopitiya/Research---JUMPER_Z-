# 📂 Project Path & Environment Strategy

This project uses a "Smart Path" system in `src/core/config.py` to handle the transition between Development (Python) and Production (.exe).

## 🚀 Environment Detection
The app automatically detects its state using `sys.frozen`:
- **Development:** Running via `main.py`.
- **Production:** Running as a bundled `Jumper-Z.exe`.
         
## 📍 Directory Mapping

| Directory     | Development Path   | Production Path (Windows) | Purpose                    |
|---------------|--------------------|---------------------------|----------------------------|
| **Root**      | `/` (Project Root) | Folder containing `.exe`  | Application base           |
| **Assets**    | `/assets/`         | Internal Bundle           | Icons, Themes (Read-only)  |
| **Tools**     | `/tools/`          | Internal Bundle           | `arduino-cli.exe` (Engine) |
| **User Data** | `/runtime_dev/`    | `%LOCALAPPDATA%/JumperZ/` | Configs, Logs, Staging     |

## 🛠️ Key Folders in User Data
All volatile/writable data is stored in the **User Data** location:

1.  **/config/**: Stores `user_config.json` (Last project path, theme settings).
2.  **/runtime/logs/**: Stores `app.log` for debugging.
3.  **/runtime/staging/**: The **Temporary Workspace**. Files fetched from Wokwi are stored here before the user performs a "Save As".

## ⚠️ Important Notes
- **Never hardcode absolute paths** (e.g., `C:/Users/...`). Always import paths from `src.core.config`.
- **Read-Only vs. Writable:** Only folders under `DATA_BASE` (User Data) are writable. Files in `ASSET_DIR` or `TOOLS_DIR` must be treated as read-only once the app is packed.
