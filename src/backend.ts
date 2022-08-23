import {ServerAPI} from "decky-frontend-lib"

var server: ServerAPI | undefined = undefined;

export function resolvePromise(promise: Promise<any>, callback: any) {
    (async function () {
        let data = await promise;
        if (data.success)
            callback(data.result);
    })();
}

export function callBackendFunction(promise: Promise<any>) {
    (async function () {
        await promise;
    })();
}

export function setServer(s: ServerAPI) {
    server = s;
}

export function setCustomHUDState(state: boolean) : Promise<any> {
    return server!.callPluginMethod("set_custom_hud_state", { "state": state});
}

export function getCustomHUDState(): Promise<any> {
    return server!.callPluginMethod("get_custom_hud_state", {});
}