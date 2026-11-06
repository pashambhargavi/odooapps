/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class NeonToggle extends Component {
    static template = "apex_glassmorphism_dark_theme.NeonToggle";

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            active: true,
        });
    }

    async cycleMood() {
        try {
            const res = await this.orm.call("res.users", "cycle_neon_mood", []);
            const mood = res.new_mood;
            const moodMap = {
                'electric_cyan': '#00F0FF',
                'cyber_magenta': '#FF007F',
                'neon_emerald': '#10B981',
                'ultraviolet': '#8B5CF6',
                'solar_gold': '#F59E0B',
            };
            const neonCol = moodMap[mood] || '#00F0FF';
            document.documentElement.style.setProperty('--apex-neon', neonCol);
            document.documentElement.style.setProperty('--apex-neon-glow', `${neonCol}66`);
            localStorage.setItem("apex_neon_color", neonCol);
        } catch (e) {
            console.debug("Neon mood cycled locally", e);
        }
    }
}

export const systrayItem = {
    Component: NeonToggle,
    isDisplayed: () => true,
};

registry.category("systray").add("ApexNeonToggle", systrayItem, { sequence: 42 });
