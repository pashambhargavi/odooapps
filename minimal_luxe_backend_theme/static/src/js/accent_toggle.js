/** @odoo-module **/

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

export class LuxeAccentToggle extends Component {
    static template = "minimal_luxe_backend_theme.LuxeAccentToggle";

    async onClickCycleAccent() {
        try {
            const res = await rpc("/web/dataset/call_kw/res.users/cycle_luxury_accent", {
                model: "res.users",
                method: "cycle_luxury_accent",
                args: [],
                kwargs: {},
            });

            if (res && res.accent_hex) {
                document.documentElement.style.setProperty("--luxe-accent", res.accent_hex);
            }
        } catch (e) {
            console.error("Failed to cycle luxury accent:", e);
        }
    }
}

registry.category("systray").add("LuxeAccentToggle", {
    Component: LuxeAccentToggle,
}, { sequence: 48 });
