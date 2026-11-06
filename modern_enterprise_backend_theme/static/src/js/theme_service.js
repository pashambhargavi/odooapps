/** @odoo-module **/

import { registry } from "@web/core/registry";

export const themeService = {
    dependencies: ["orm"],
    async start(env, { orm }) {
        // 1. Check local storage or user preference for dark mode
        const storedDark = localStorage.getItem("odoo_theme_dark_mode");
        if (storedDark === "dark") {
            document.body.classList.add("o_theme_dark");
        } else if (storedDark === "light") {
            document.body.classList.remove("o_theme_dark");
        }

        // 2. Fetch active theme config from backend
        try {
            const config = await orm.call("theme.config", "get_active_theme_config", []);
            if (config) {
                const root = document.documentElement;
                if (config.primary_color) root.style.setProperty("--theme-primary", config.primary_color);
                if (config.accent_color) root.style.setProperty("--theme-accent", config.accent_color);
                if (config.navbar_bg_color) root.style.setProperty("--theme-navbar-bg", config.navbar_bg_color);
                if (config.sidebar_bg_color) root.style.setProperty("--theme-sidebar-bg", config.sidebar_bg_color);
                if (config.active_item_color) root.style.setProperty("--theme-active-item", config.active_item_color);

                if (config.border_radius_size === "sharp") root.style.setProperty("--theme-border-radius", "0px");
                else if (config.border_radius_size === "subtle") root.style.setProperty("--theme-border-radius", "4px");
                else if (config.border_radius_size === "modern") root.style.setProperty("--theme-border-radius", "8px");
                else if (config.border_radius_size === "smooth") root.style.setProperty("--theme-border-radius", "12px");

                if (config.layout_mode === "modern_sidebar") {
                    document.body.classList.add("o_theme_sidebar_layout");
                }
            }
        } catch (e) {
            console.debug("Theme configuration loaded with defaults", e);
        }
    },
};

registry.category("services").add("themeService", themeService);
