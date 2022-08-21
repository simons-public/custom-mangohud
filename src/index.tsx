import {
  ButtonItem,
  definePlugin,
  Menu,
  MenuItem,
  PanelSection,
  PanelSectionRow,
  ServerAPI,
  showContextMenu,
  staticClasses,
  ToggleField,
} from "decky-frontend-lib";
import { VFC, useState } from "react";
import { FaChartLine } from "react-icons/fa";

import * as backend from "./backend"

const Content: VFC<{ server: ServerAPI }> = ({server}) => {
  backend.setServer(server);

  const [CustomHUDToggleValue, setCustomHUDState] = useState<boolean>(false);

  backend.resolvePromise(backend.getCustomHUDState(), setCustomHUDState);


  return (
    <PanelSection title="Settings">
      <PanelSectionRow>
        <ToggleField
          label="Custom MangoHUD Config"
          description="Overrides config to ~/.config/mangohud.conf"
          checked={CustomHUDToggleValue}
          onChange={(value: boolean) => {
            backend.setCustomHUDState(value);
            setCustomHUDState(value);
          }}
          />
      </PanelSectionRow>

      <PanelSectionRow>
        <ButtonItem
          layout="below"
          onClick={(e) =>
            showContextMenu(
              <Menu label="Menu" cancelText="Return" onCancel={() => {}}>
                <MenuItem onSelected={() => {}}>Item #1</MenuItem>
                <MenuItem onSelected={() => {}}>Item #2</MenuItem>
                <MenuItem onSelected={() => {}}>Item #3</MenuItem>
              </Menu>,
              e.currentTarget ?? window
            )
          }
        >
          Modify Configuration
        </ButtonItem>
      </PanelSectionRow>
    </PanelSection>
  );
};

export default definePlugin((server: ServerAPI) => {
  return {
    title: <div className={staticClasses.Title}>MangoHUD</div>,
    content: <Content server={server} />,
    icon: <FaChartLine />,
    onDismount() {
      server.routerHook.removeRoute("/custom-mangohud");
    },
  };
});
