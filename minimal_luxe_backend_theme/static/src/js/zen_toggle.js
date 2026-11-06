/** @odoo-module **/

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

export class LuxeZenToggle extends Component {
    static template = "minimal_luxe_backend_theme.LuxeZenToggle";

    async onClickToggleZen() {
        try {
            const res = await rpc("/web/dataset/call_kw/res.users/toggle_zen_mode", {
                model: "res.users",
                method: "toggle_zen_mode",
                args: [],
                kwargs: {},
            });

            if (res) {
                if (res.zen_mode_active) {
                    document.body.classList.add('luxe-zen-mode-active');
                } else {
                    document.body.classList.remove('luxe-zen-mode-active');
                }
            }
        } catch (e) {
            console.error("Failed to toggle Zen mode:", e);
        }
    }
}

registry.category("systray").add("LuxeZenToggle", {
    Component: LuxeZenToggle,
}, { sequence: 47 });
