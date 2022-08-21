import os
import subprocess
from logging import DEBUG, INFO, getLogger

logger = getLogger("custom-mangohud")

SYSTEMD_PATH="/home/deck/.config/systemd/user"
PATH_FILE=f"{SYSTEMD_PATH}/customhud@.path"
SERVICE_FILE=f"{SYSTEMD_PATH}/customhud@.service"
MANGO_CONFIG_FILE="/home/deck/.config/mangohud.conf"
MANGO_CONFIG_BACKUP="/tmp/steam_mangohud_backup"
ENV=os.environ.copy()
ENV.update({'DBUS_SESSION_BUS_ADDRESS': 'unix:path=/run/user/1000/bus'})

PATH_SOURCE="""# customhud@.path
[Unit]
Description="Monitor the mangohud config file for changes"

[Path]
PathChanged=/tmp/mangohud.%i
Unit=customhud@%i.service
TriggerLimitBurst=1000

[Install]
WantedBy=default.target
"""

SERVICE_SOURCE="""# customhud@.service
[Unit]
Description="Set mangohud configuration"
StartLimitBurst=1000

[Service]
Type=oneshot
ExecStart=/usr/bin/cp -v /home/deck/mangohud.conf /tmp/mangohud.%i
ExecStartPost=/usr/bin/touch /tmp/mangohud.%i
"""

# starter configuration at ~/.config/mangohud.conf,
# can be modified after initial creation
STARTER_CONFIG="""control=mangohud
fsr_steam_sharpness=5
nis_steam_sharpness=10
battery
cpu_stats=0
gpu_stats=0
frame_timing=0
battery_icon
font_scale=0.6
table_columns=5
width=300
media_player=1
media_player_format={artist} - {title}
font_scale_media_player=1
background_alpha=0
"""

class Plugin:
    """ backend plugin class """

    def _create_service_files():
        """" helper to create the service files """
        os.makedirs(SYSTEMD_PATH, exist_ok=True)
        with open(PATH_FILE, 'w') as f:
            f.writelines(PATH_SOURCE)
        with open(SERVICE_FILE, 'w') as f:
            f.writelines(SERVICE_SOURCE)
    
    def _create_starter_config():
        """ create a default custom configuration """
        with open(MANGO_CONFIG_FILE, "w") as f:
            f.writelines(STARTER_CONFIG)

    def _get_steam_mango_config_file(self):
        """ this gets the last modified file (sometimes there are multiple)
        in the future this should grab the envirionment variable from the mangoapp process """
        files = [f for f in os.scandir("/tmp") if 'mangohud.' in f.name]
        latest = max(files, key=os.path.getmtime)
        return f"/tmp/{latest.name}"

    def _get_current_config_id(self):
        """ gets the mktmp extension for use with the systemd units """
        return self._get_steam_mango_config_file(self).split(".")[-1]

    def touch_config(self):
        """ mangohud doesn't update unless the file modification date changes """
        logger.info(f"touching file: {self._get_steam_mango_config_file(self)}")
        os.utime(self._get_steam_mango_config_file(self))

    async def get_custom_hud_state(self):
        self.touch_config(self)
        try:
            return subprocess.Popen(
                f"/usr/bin/systemctl is-active --user customhud@{self._get_current_config_id(self)}.path",
                stdout=subprocess.PIPE, shell=True, env=ENV).communicate()[0] == b'active\n'
        except:
            logger.exception("traceback:")

    async def set_custom_hud_state(self, state):
        if state:
            logger.info("turning on custom mangohud")
            try:
                # backup existing config
                with open(self._get_steam_mango_config_file(self), 'r') as src:
                    with open(MANGO_CONFIG_BACKUP, 'w') as dst:
                        logger.info(f"copying {src.name} to {dst.name}")
                        dst.writelines(src.readlines())

                ret = subprocess.Popen(
                    f"/usr/bin/systemctl enable --now --user customhud@{self._get_current_config_id(self)}.path",
                    stdout=subprocess.PIPE, shell=True, env=ENV).wait()
                self.touch_config(self)
                return ret
            except:
                logger.exception("traceback:")
        else:
            logger.info("turning off custom mangohud")
            try:
                # restore existing config
                with open(self._get_steam_mango_config_file(self), 'w') as dst:
                    with open(MANGO_CONFIG_BACKUP, 'r') as src:
                        logger.info(f"copying {src.name} to {dst.name}")
                        buffer = src.readlines()
                        dst.writelines(buffer)

                ret = subprocess.Popen(
                    f"/usr/bin/systemctl disable --now --user customhud@{self._get_current_config_id(self)}.path",
                    stdout=subprocess.PIPE, shell=True, env=ENV).wait()
                self.touch_config(self)    
                return ret
            except:
                logger.exception("traceback:")



    async def _main(self):
        """ plugin startup routine """
        if (not os.path.exists(PATH_FILE)) or (not os.path.exists(SERVICE_FILE)):
            self._create_service_files()

        if not os.path.exists(MANGO_CONFIG_FILE):
            self._create_starter_config()