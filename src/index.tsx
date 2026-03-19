import { PanelSection, PanelSectionRow, ToggleField } from "@decky/ui";
import { callable, definePlugin } from "@decky/api";
import { useState, useEffect } from "react";

const getStatus = callable<[], boolean>("get_status");
const enableExternal = callable<[], boolean>("enable_external");
const disableExternal = callable<[], boolean>("disable_external");

function ControllerIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 36 36" fill="currentColor" style={{width: "1em", height: "1em"}}>
      <path d="M26 8H10C5.6 8 2 11.6 2 16s3.6 8 8 8h1.8l1.6 2.4c.4.6 1 .6 1.4 0L16.4 24h3.2l1.6 2.4c.4.6 1 .6 1.4 0L24.2 24H26c4.4 0 8-3.6 8-8s-3.6-8-8-8zm-14 9h-2v2H8v-2H6v-2h2v-2h2v2h2v2zm7 1a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3zm3-3a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3zm3 3a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3z"/>
    </svg>
  );
}

function Content() {
  const [externalMode, setExternalMode] = useState(false);

  useEffect(() => {
    getStatus().then((val) => {
      setExternalMode(val);
    }).catch((e) => {
      console.error("getStatus failed:", e);
    });
  }, []);

  const toggle = async (value: boolean) => {
    try {
      if (value) {
        await enableExternal();
      } else {
        await disableExternal();
      }
      setExternalMode(value);
    } catch(e) {
      console.error("toggle failed:", e);
    }
  };

  return (
    <PanelSection title="Controller Mode">
      <PanelSectionRow>
        <ToggleField
          label="External Controller Mode"
          description={externalMode ? "Built-in controller disabled" : "Built-in controller enabled"}
          checked={externalMode}
          onChange={toggle}
        />
      </PanelSectionRow>
    </PanelSection>
  );
}

export default definePlugin(() => ({
  name: "Toggle Ally Controller",
  content: <Content />,
  icon: <ControllerIcon />,
}));
