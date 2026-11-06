/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class DarkModeToggle extends Component {
    static template = "modern_enterprise_backend_theme.DarkModeToggle";

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            isDark: document.body.classList.contains("o_theme_dark"),
        });
    }

    async toggle() {
        const next = !this.state.isDark;
        this.state.isDark = next;
        if (next) {
            document.body.classList.add("o_theme_dark");
            localStorage.setItem("odoo_theme_dark_mode", "dark");
        } else {
            document.body.classList.remove("o_theme_dark");
            localStorage.setItem("odoo_theme_dark_mode", "light");
        }
        try {
            await this.orm.call("res.users", "toggle_dark_mode", []);
        } catch (e) {
            console.debug("Dark mode preference saved locally", e);
        }
    }
}

export const systrayItem = {
    Component: DarkModeToggle,
    isDisplayed: () => true,
};

registry.category("systray").add("DarkModeToggle", systrayItem, { sequence: 40 });
