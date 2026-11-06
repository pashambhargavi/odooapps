/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class OmniSystrayToggle extends Component {
    static template = "omni_theme_multi_studio.OmniSystrayToggle";

    setup() {
        this.rpc = useService("rpc");
        this.user = useService("user");
        this.state = useState({
            activeKey: "emerald_aurora",
            activeName: "Emerald Aurora",
            activeIcon: "🌿",
            themes: [],
            allowSwitching: true,
        });

        onWillStart(async () => {
            try {
                const config = await this.rpc("/web/dataset/call_kw", {
                    model: "omni.theme.config",
                    method: "get_user_active_theme_config",
                    args: [],
                    kwargs: {},
                });
                if (config) {
                    this.state.activeKey = config.theme_key;
                    this.state.activeName = config.name.split(" (")[0];
                    this.state.themes = config.all_themes || [];
                    this.state.allowSwitching = config.allow_user_switching !== false;

                    const curTheme = this.state.themes.find((t) => t.key === config.theme_key);
                    if (curTheme) {
                        this.state.activeIcon = curTheme.icon;
                    }
                }
            } catch (e) {
                console.warn("[OmniTheme] Error fetching theme config for systray:", e);
            }
        });
    }

    async switchTheme(themeKey) {
        if (!this.state.allowSwitching) {
            return;
        }

        const selected = this.state.themes.find((t) => t.key === themeKey);
        if (selected) {
            this.state.activeKey = themeKey;
            this.state.activeName = selected.name;
            this.state.activeIcon = selected.icon;
            document.documentElement.setAttribute("data-omni-theme", themeKey);
        }

        try {
            await this.rpc("/web/dataset/call_kw", {
                model: "res.users",
                method: "action_switch_omni_theme",
                args: [this.user.userId, themeKey],
                kwargs: {},
            });
        } catch (e) {
            console.error("[OmniTheme] Error persisting theme selection:", e);
        }
    }
}

registry.category("systray").add("omni_systray_toggle", {
    Component: OmniSystrayToggle,
    sequence: 50,
});
