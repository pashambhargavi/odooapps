/** @odoo-module **/

import { registry } from "@web/core/registry";

export const omniThemeService = {
    dependencies: ["rpc"],
    async start(env, { rpc }) {
        try {
            const config = await rpc("/web/dataset/call_kw", {
                model: "omni.theme.config",
                method: "get_user_active_theme_config",
                args: [],
                kwargs: {},
            });

            if (config && config.theme_key) {
                document.documentElement.setAttribute("data-omni-theme", config.theme_key);
                if (config.button_radius) {
                    document.documentElement.style.setProperty("--omni-button-radius", config.button_radius);
                }
            }
        } catch (e) {
            console.warn("[OmniTheme] Could not load theme config dynamically:", e);
        }
    },
};

registry.category("services").add("omniThemeService", omniThemeService);
