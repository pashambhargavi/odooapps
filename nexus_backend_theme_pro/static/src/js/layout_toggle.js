/** @odoo-module **/

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

export class NexusLayoutToggle extends Component {
    static template = "nexus_backend_theme_pro.NexusLayoutToggle";

    async onClickCycleLayout() {
        try {
            const res = await rpc("/web/dataset/call_kw/res.users/cycle_layout_mode", {
                model: "res.users",
                method: "cycle_layout_mode",
                args: [],
                kwargs: {},
            });

            if (res && res.new_layout) {
                document.body.classList.remove('nexus-layout-sidebar', 'nexus-layout-topbar', 'nexus-layout-minirail');
                document.body.classList.add(`nexus-layout-${res.new_layout}`);
            }
        } catch (e) {
            console.error("Failed to cycle layout mode:", e);
        }
    }
}

registry.category("systray").add("NexusLayoutToggle", {
    Component: NexusLayoutToggle,
}, { sequence: 46 });
