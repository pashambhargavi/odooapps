/** @odoo-module **/

import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

export const chromaThemeService = {
    dependencies: [],
    async start(env) {
        try {
            const config = await rpc("/web/dataset/call_kw/chroma.theme.config/get_active_chroma_config", {
                model: "chroma.theme.config",
                method: "get_active_chroma_config",
                args: [],
                kwargs: {},
            });

            if (config) {
                const root = document.documentElement;
                if (config.header_bg) root.style.setProperty("--chroma-header-bg", config.header_bg);
                if (config.accent_color) root.style.setProperty("--chroma-accent", config.accent_color);

                const shapeMap = { modern: '8px', pill: '20px', sharp: '4px' };
                if (config.button_shape) {
                    root.style.setProperty("--chroma-btn-radius", shapeMap[config.button_shape] || '8px');
                }

                document.body.classList.add('chroma-pristine-theme');
            }
        } catch (e) {
            console.warn("Chroma Theme Service: Could not load configuration", e);
        }
    },
};

registry.category("services").add("chroma_theme_service", chromaThemeService);
