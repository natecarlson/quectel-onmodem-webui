pyinstaller app/main.py --add-data app/webserver:webserver --add-data config.yml:. --hidden-import at.commands
