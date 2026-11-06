/** @odoo-module **/

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

export class NexusChatterToggle extends Component {
    static template = "nexus_backend_theme_pro.NexusChatterToggle";

    async onClickToggleChatter() {
        try {
            const res = await rpc("/web/dataset/call_kw/res.users/toggle_chatter_position", {
                model: "res.users",
                method: "toggle_chatter_position",
                args: [],
                kwargs: {},
            });

            if (res && res.new_position) {
                document.body.classList.remove('nexus-chatter-sided', 'nexus-chatter-bottom');
                document.body.classList.add(`nexus-chatter-${res.new_position}`);
            }
        } catch (e) {
            console.error("Failed to toggle chatter position:", e);
        }
    }
}

registry.category("systray").add("NexusChatterToggle", {
    Component: NexusChatterToggle,
}, { sequence: 45 });
