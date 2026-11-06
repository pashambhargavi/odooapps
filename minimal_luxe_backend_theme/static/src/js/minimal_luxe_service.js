/** @odoo-module **/

import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

export const minimalLuxeService = {
    dependencies: [],
    async start(env) {
        try {
            const config = await rpc("/web/dataset/call_kw/minimal.luxe.config/get_active_luxe_config", {
                model: "minimal.luxe.config",
                method: "get_active_luxe_config",
                args: [],
                kwargs: {},
            });

            if (config) {
                const root = document.documentElement;
                if (config.accent_hex) root.style.setProperty("--luxe-accent", config.accent_hex);

                document.body.classList.remove('luxe-obsidian-dark', 'luxe-chalk-light', 'luxe-warm-zinc');
                document.body.classList.add(`luxe-${config.theme_mode.replace('_', '-') || 'obsidian-dark'}`);

                if (config.zen_mode_active) {
                    document.body.classList.add('luxe-zen-mode-active');
                } else {
                    document.body.classList.remove('luxe-zen-mode-active');
                }
            }
        } catch (e) {
            console.warn("Minimal Luxe Service: Could not load configuration", e);
        }
    },
};

registry.category("services").add("minimal_luxe_service", minimalLuxeService);
