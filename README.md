# LCS Bridge
This repository contains code of the **LCS Bridge App**. This software is used to connect up to two LCS chambers to the LCSRP5 server.

---
## Basic Usage


### Installation
- Download Windows 11 setup here: [GitHub Releases](https://github.com/LCS-Development-Group/Bridge_app/releases/)
- Run it. In the wizard select the installation location. Default it recommended. Click install. Afterwards app is ready for use
- In case of new release simply download the new setup and run it. New version will overwrite the old
- Uninstall via standard windows interface

No additional software or libraries are necessary to use this app. For running on Linux see **Advanced** section.

### Usage
- Run the app
- Connect the chamber and click `Refresh COM`. Choose the appropriate COM Port and click connect. After successfull handshake between devices the status the chamber ID will be displayed. Connection to the server is established automatically.
- Click `Advanced View` to see raw messages between server and chamber. haking and ping messages are not displayed.
- Click Disconnect to disconnect.
---

## Advanced
This section is meant for development of the code, or running the code on linux (Ubuntu and Raspbian confirmed to be supported)
### Installation (Source code)
- Clone the repository or download source code from Releases.
- Install dependencies listed in `venv_requirements.txt`. Usage of **Virtual Environment** is highly recommended.
- Run the full app:
```bash
.venv/bin/python ./run_app.pyw
```
- Alternatively run just one bridge instance in the non-interactive way:
```bash
.venv/bin/python ./bridge.py <port>
```

## Version Control & Backups
After making changes to the scripts it is recommended to backup them using git. Recommended commit sequence:
```bash
git add -A
git commit -m "<commit text>"
git push <remote name> master
```
Please do this under admin's supervision.

### Deployment
Deployment (setup.exe creation) is performed via **pyinstaller** and **Inno Setup 6**.
- install requirements listed in `venv_pyinsaller.txt`
- run:
```bash
.venv/bin/python pyinstaller --noconsole --onedir --name LCS_Bridge_Win11 --collect-all customtkinter --add-data "icons;icons" --icon="icons/app.ico" app_run.pyw
```
- Full executable is available in the **dist/** directory
- Change the app version in the `setup.iss` in *OutputBaseFilename* and *AppVersion*
- Install **Inno Setup 6**
- Open the `setup.iss` in the Ino GUI. Compile it (`Ctrl+F9`)
- Setup executable is available in **Output/**
- [Admin] Upload it to Github as a Release
