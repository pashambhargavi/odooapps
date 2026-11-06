/** @odoo-module **/

import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

export const nexusThemeService = {
    dependencies: [],
    async start(env) {
        try {
            const config = await rpc("/web/dataset/call_kw/nexus.theme.config/get_active_nexus_config", {
                model: "nexus.theme.config",
                method: "get_active_nexus_config",
                args: [],
                kwargs: {},
            });

            if (config) {
                const root = document.documentElement;
                if (config.primary_color) root.style.setProperty("--nexus-primary", config.primary_color);
                if (config.accent_color) root.style.setProperty("--nexus-accent", config.accent_color);
                if (config.sidebar_bg) root.style.setProperty("--nexus-sidebar-bg", config.sidebar_bg);
                if (config.header_bg) root.style.setProperty("--nexus-header-bg", config.header_bg);

                const radiusMap = { none: '0px', small: '4px', medium: '8px', large: '14px' };
                if (config.border_radius) {
                    root.style.setProperty("--nexus-border-radius", radiusMap[config.border_radius] || '8px');
                }

                // Apply body layout and productivity classes
                document.body.classList.remove('nexus-layout-sidebar', 'nexus-layout-topbar', 'nexus-layout-minirail');
                document.body.classList.add(`nexus-layout-${config.layout_mode || 'sidebar'}`);

                document.body.classList.remove('nexus-chatter-sided', 'nexus-chatter-bottom');
                document.body.classList.add(`nexus-chatter-${config.chatter_position || 'sided'}`);

                document.body.classList.remove('nexus-density-compact', 'nexus-density-standard', 'nexus-density-spacious');
                document.body.classList.add(`nexus-density-${config.table_density || 'standard'}`);
            }
        } catch (e) {
            console.warn("Nexus Pro Theme Service: Could not load configuration", e);
        }
    },
};

registry.category("services").add("nexus_theme_service", nexusThemeService);
