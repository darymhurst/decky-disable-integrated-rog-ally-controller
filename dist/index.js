// Decky Loader will pass this api in, it's versioned to allow for backwards compatibility.
// @ts-ignore

// Prevents it from being duplicated in output.
const manifest = {"name":"Toggle Ally Controller"};
const API_VERSION = 1;
const internalAPIConnection = window.__DECKY_SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED_deckyLoaderAPIInit;
// Initialize
if (!internalAPIConnection) {
    throw new Error('[@decky/api]: Failed to connect to the loader as as the loader API was not initialized. This is likely a bug in Decky Loader.');
}
const api = internalAPIConnection.connect(API_VERSION, manifest.name);
const callable = api.callable;
const definePlugin = (fn) => {
    return (...args) => {
        // TODO: Maybe wrap this
        return fn(...args);
    };
};

const getStatus = callable("get_status");
const enableExternal = callable("enable_external");
const disableExternal = callable("disable_external");
function ControllerIcon() {
    return (SP_JSX.jsx("svg", { xmlns: "http://www.w3.org/2000/svg", viewBox: "0 0 36 36", fill: "currentColor", style: { width: "1em", height: "1em" }, children: SP_JSX.jsx("path", { d: "M26 8H10C5.6 8 2 11.6 2 16s3.6 8 8 8h1.8l1.6 2.4c.4.6 1 .6 1.4 0L16.4 24h3.2l1.6 2.4c.4.6 1 .6 1.4 0L24.2 24H26c4.4 0 8-3.6 8-8s-3.6-8-8-8zm-14 9h-2v2H8v-2H6v-2h2v-2h2v2h2v2zm7 1a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3zm3-3a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3zm3 3a1.5 1.5 0 1 1 0-3 1.5 1.5 0 0 1 0 3z" }) }));
}
function Content() {
    const [externalMode, setExternalMode] = SP_REACT.useState(false);
    SP_REACT.useEffect(() => {
        getStatus().then((val) => {
            setExternalMode(val);
        }).catch((e) => {
            console.error("getStatus failed:", e);
        });
    }, []);
    const toggle = async (value) => {
        try {
            if (value) {
                await enableExternal();
            }
            else {
                await disableExternal();
            }
            setExternalMode(value);
        }
        catch (e) {
            console.error("toggle failed:", e);
        }
    };
    return (SP_JSX.jsx(DFL.PanelSection, { title: "Controller Mode", children: SP_JSX.jsx(DFL.PanelSectionRow, { children: SP_JSX.jsx(DFL.ToggleField, { label: "External Controller Mode", description: externalMode ? "Built-in controller hidden" : "Built-in controller active", checked: externalMode, onChange: toggle }) }) }));
}
var index = definePlugin(() => ({
    name: "Toggle Ally Controller",
    content: SP_JSX.jsx(Content, {}),
    icon: SP_JSX.jsx(ControllerIcon, {}),
}));

export { index as default };
//# sourceMappingURL=index.js.map
