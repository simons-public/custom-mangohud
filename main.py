import os
import subprocess
from logging import DEBUG, INFO, getLogger

import getpass

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

    @staticmethod
    def _create_service_files() -> None:
        """" helper to create the service files """
        os.makedirs(SYSTEMD_PATH, exist_ok=True)
        with open(PATH_FILE, 'w') as f:
            f.writelines(PATH_SOURCE)
        with open(SERVICE_FILE, 'w') as f:
            f.writelines(SERVICE_SOURCE)

    @staticmethod
    def _create_starter_config() -> None:
        """ create a default custom configuration """
        with open(MANGO_CONFIG_FILE, "w") as f:
            f.writelines(STARTER_CONFIG)

    @staticmethod
    def _get_mangoapp_pid() -> int:
        """ return the pid of mangoapp """
        # get all pids in /proc
        pids = [int(f.name) for f in os.scandir("/proc") if
            f.is_dir() and f.name.isnumeric()]

        # read the cmdline of all pids
        try:
            for pid in pids:
                with open(f"/proc/{pid}/cmdline", 'r') as f:
                    if 'mangoapp' in f.read():
                        return pid

        # ignore pids that have died before being read
        except FileNotFoundError:
            pass

    @staticmethod
    def _get_steam_mango_config_file() -> str:
        """ returns the MANGOHUD_CONFIG variable from the mangoapp pid """
        with open(f"/proc/{Plugin._get_mangoapp_pid()}/environ", 'r') as f:
            env = [e for e in f.read().split("\x00") if 'MANGOHUD_CONFIGFILE' in e]
            return env.pop().split("=")[-1]

    @staticmethod
    def _get_current_config_id() -> str:
        """ returns the mktmp extension for use with the systemd units """
        return Plugin._get_steam_mango_config_file().split(".")[-1]

    @staticmethod
    def _touch_config():
        """ mangohud doesn't seem to update unless the file modification date changes """
        logger.debug(f"touching file: {Plugin._get_steam_mango_config_file()}")
        os.utime(Plugin._get_steam_mango_config_file())

    @staticmethod
    def _backup_config():
        """ backup the current config file """
        logger.debug(f"copying {Plugin._get_steam_mango_config_file()} to {MANGO_CONFIG_BACKUP}")
        with open(Plugin._get_steam_mango_config_file(), 'r') as src:
            buffer = src.read()

        with open(MANGO_CONFIG_BACKUP, 'w') as dst:
            dst.write(buffer)
            dst.flush()

    @staticmethod
    def _restore_config():
        """ restore the previous config file """
        logger.debug(f"copying {MANGO_CONFIG_BACKUP} to {Plugin._get_steam_mango_config_file()}")
        with open(MANGO_CONFIG_BACKUP, 'r') as src:
            buffer = src.read()

        with open(Plugin._get_steam_mango_config_file(), 'w') as dst:
            dst.write(buffer)
            dst.flush()

        with open(Plugin._get_steam_mango_config_file(), 'r') as dst:
            print(dst.read())

    async def get_custom_hud_state(self) -> bool:
        """ returns true if custom hud is active """
        logger.debug("getting custom hud state")
        try:
            Plugin._touch_config()
            return subprocess.Popen(
                f"/usr/bin/systemctl is-active --user customhud@{Plugin._get_current_config_id()}.path",
                stdout=subprocess.PIPE, shell=True, env=ENV).communicate()[0] == b'active\n'
        except:
            logger.exception("traceback:")

    async def set_custom_hud_state(self, state) -> None:
        """ enable or disable the custom hud """
        if state:
            logger.info("Turning on custom MangoHUD")
            try:
                Plugin._backup_config()
                subprocess.Popen(
                    f"/usr/bin/systemctl enable --now --user customhud@{Plugin._get_current_config_id()}.path",
                    stdout=subprocess.PIPE, shell=True, env=ENV).wait()
                Plugin._touch_config()
                return
            except:
                logger.exception("traceback:")
        else:
            logger.info("Turning off custom MangoHUD")
            try:
                Plugin._restore_config()
                subprocess.Popen(
                    f"/usr/bin/systemctl disable --now --user customhud@{Plugin._get_current_config_id()}.path",
                    stdout=subprocess.PIPE, shell=True, env=ENV).wait()
                Plugin._touch_config()
                return
            except:
                logger.exception("traceback:")

    async def _main(self):
        """ plugin startup routine """
        logger.info("Starting Custom MangoHUD Plugin")
        
        # drop privileges (required until #152 gets merged)
        os.setgid(1000)
        os.setuid(1000)

        if (not os.path.exists(PATH_FILE)) or (not os.path.exists(SERVICE_FILE)):
            Plugin._create_service_files()

        if not os.path.exists(MANGO_CONFIG_FILE):
            Plugin._create_starter_config()