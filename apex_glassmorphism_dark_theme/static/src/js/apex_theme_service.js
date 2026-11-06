/** @odoo-module **/

import { registry } from "@web/core/registry";

export const apexThemeService = {
    dependencies: ["orm"],
    async start(env, { orm }) {
        document.body.classList.add("o_apex_theme_active");

        // Load cached neon color if available
        const cachedColor = localStorage.getItem("apex_neon_color");
        if (cachedColor) {
            document.documentElement.style.setProperty('--apex-neon', cachedColor);
            document.documentElement.style.setProperty('--apex-neon-glow', `${cachedColor}66`);
        }

        try {
            const config = await orm.call("theme.apex.config", "get_active_apex_config", []);
            if (config) {
                const root = document.documentElement;
                if (config.neon_color) {
                    root.style.setProperty("--apex-neon", config.neon_color);
                    root.style.setProperty("--apex-neon-glow", config.neon_glow_color || `${config.neon_color}66`);
                }
                if (config.glass_card_bg) root.style.setProperty("--apex-glass-bg", config.glass_card_bg);
                if (config.glass_surface_border) root.style.setProperty("--apex-glass-border", config.glass_surface_border);

                if (config.glass_blur_strength === "subtle_8px") root.style.setProperty("--apex-glass-blur", "8px");
                else if (config.glass_blur_strength === "frosted_16px") root.style.setProperty("--apex-glass-blur", "16px");
                else if (config.glass_blur_strength === "deep_24px") root.style.setProperty("--apex-glass-blur", "24px");
            }
        } catch (e) {
            console.debug("Apex theme configuration loaded with defaults", e);
        }
    },
};

registry.category("services").add("apexThemeService", apexThemeService);
