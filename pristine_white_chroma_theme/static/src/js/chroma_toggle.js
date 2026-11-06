/** @odoo-module **/

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

export class ChromaToggle extends Component {
    static template = "pristine_white_chroma_theme.ChromaToggle";

    async onClickCycleChroma() {
        try {
            const res = await rpc("/web/dataset/call_kw/res.users/cycle_chroma_preset", {
                model: "res.users",
                method: "cycle_chroma_preset",
                args: [],
                kwargs: {},
            });

            if (res && res.header_bg) {
                document.documentElement.style.setProperty("--chroma-header-bg", res.header_bg);
                if (res.accent_color) {
                    document.documentElement.style.setProperty("--chroma-accent", res.accent_color);
                }
            }
        } catch (e) {
            console.error("Failed to cycle Chroma header color:", e);
        }
    }
}

registry.category("systray").add("ChromaToggle", {
    Component: ChromaToggle,
}, { sequence: 44 });
