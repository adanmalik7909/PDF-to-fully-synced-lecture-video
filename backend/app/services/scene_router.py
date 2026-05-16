import os
import jinja2
from PIL import Image
import io
from app.utils.logger import log_info, log_error

# Provide the JS bridge to control CSS animations from Playwright
JS_BRIDGE = """
window.triggerData = null;
window.wordTimestamps = [];
window.animationDuration = 0;
window.isPaused = false;
window.currentTime = 0;
window.executedActions = new Set();

window.startAnimation = function(data, timestamps) {
    console.log("[JS_BRIDGE] Starting V9.0 Timeline Engine", data);
    window.triggerData = data;
    window.wordTimestamps = timestamps || [];
    window.animationDuration = data.duration_sec || 0;
    
    // Reset executed actions for new scene
    window.executedActions.clear();
    
    // Initialize elements
    document.querySelectorAll('.bullet-item').forEach(b => b.style.opacity = '0');
    
    requestAnimationFrame(renderFrame);
};

window.setTime = function(t) {
    window.currentTime = t;
    processTimeline(t);
    updateSubtitles(t, window.wordTimestamps);
};

function processTimeline(t) {
    if (!window.triggerData || !window.triggerData.timeline) return;

    window.triggerData.timeline.forEach((entry, index) => {
        const actionId = `action_${index}_${entry.time_sec}`;
        if (t >= entry.time_sec && !window.executedActions.has(actionId)) {
            executeAction(entry);
            window.executedActions.add(actionId);
        }
    });
}

function executeAction(entry) {
    console.log("[Timeline] Executing:", entry.action, "on", entry.target);
    
    switch(entry.action) {
        case 'heading_glow':
            const heading = document.getElementById(entry.target);
            if (heading) heading.classList.add('pulse-glow-active');
            break;
            
        case 'bullet_reveal':
            const bullet = document.getElementById(entry.target);
            if (bullet) {
                bullet.style.opacity = '1';
                bullet.classList.add('slide-in-right');
                // Dim others
                document.querySelectorAll('.bullet-item').forEach(b => {
                    if (b.id !== entry.target) b.classList.add('dimmed');
                    else b.classList.remove('dimmed');
                });
            }
            break;
            
        case 'word_pulse':
            const goldWord = document.querySelector('.gold-word');
            if (goldWord) {
                goldWord.classList.add('active-pulse');
                setTimeout(() => goldWord.classList.remove('active-pulse'), 1000);
            }
            break;
            
        case 'diagram_zoom':
            const diagram = document.getElementById('diagram-container');
            if (diagram) diagram.classList.add('ken-burns-zoom');
            break;
            
        case 'diagram_callout':
            document.querySelectorAll('.callout').forEach(c => {
                c.style.opacity = '0';
                c.style.zIndex = '10';
            });
            const callout = document.getElementById(entry.target);
            if (callout) {
                callout.style.opacity = '1';
                callout.style.transform = 'scale(1.1)';
                callout.style.zIndex = '100';
            }
            break;
    }
}

function updateSubtitles(t, wordTimestamps) {
    const container = document.getElementById('subtitle-container');
    if (!container || !wordTimestamps || wordTimestamps.length === 0) return;
    
    let activeIdx = -1;
    for (let i = 0; i < wordTimestamps.length; i++) {
        let wt = wordTimestamps[i];
        if (t >= wt.start_sec && t <= (wt.start_sec + wt.duration)) {
            activeIdx = i;
            break;
        }
    }
    
    if (activeIdx >= 0) {
        let startIdx = Math.max(0, activeIdx - 3);
        let endIdx = Math.min(wordTimestamps.length, activeIdx + 4);
        let html = "";
        for (let i = startIdx; i < endIdx; i++) {
            let wt = wordTimestamps[i];
            if (i === activeIdx) {
                html += `<span style="color: #FBBF24; font-weight: 800; transform: scale(1.1); display: inline-block; transition: all 0.05s;">${wt.word}</span> `;
            } else {
                html += `<span style="color: rgba(255,255,255,0.9); font-weight: 500;">${wt.word}</span> `;
            }
        }
        container.innerHTML = html;
        container.style.opacity = '1';
    } else {
        container.style.opacity = '0';
    }
}

function renderFrame() {
    // Sync loop for Playwright
    if (!window.isPaused) {
        processTimeline(window.currentTime);
    }
    if (window.currentTime <= window.animationDuration + 1.0) {
        requestAnimationFrame(renderFrame);
    }
}
"""

class SceneRouter:
    """Routes Blueprint scenes to specific Jinja2 HTML templates."""
    
    def __init__(self):
        template_dir = os.path.join(os.path.dirname(__file__), "templates")
        self.jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(template_dir))

    TEMPLATE_MAP = {
        'intro':         'concept.html.j2', # Fallback to concept until intro is built
        'concept':       'concept.html.j2',
        'diagram_focus': 'diagram_focus.html.j2',
        'comparison':    'concept.html.j2', # Fallback
        'process':       'concept.html.j2', # Fallback
        'summary':       'concept.html.j2', # Fallback
    }

    def _get_avatar_config(self, scene_type: str) -> dict:
        """Returns size and positioning for the avatar based on scene type."""
        configs = {
            'intro':         {'size': 340, 'position': 'center', 'ring': '#C9B99A', 'visible': True},
            'concept':       {'size': 260, 'position': 'bottom-left', 'ring': '#4F8EF7', 'visible': True},
            'diagram_focus': {'size': 100, 'position': 'bottom-left', 'ring': '#1D9E75', 'visible': True},
            'summary':       {'size': 300, 'position': 'center', 'ring': '#C9B99A', 'visible': True},
        }
        return configs.get(scene_type, configs['concept'])

    def render_scene_html(self, scene: dict) -> str:
        """Generates the final HTML string for the scene."""
        scene_type = scene.get('scene_type', 'concept')
        template_name = self.TEMPLATE_MAP.get(scene_type, 'concept.html.j2')
        
        try:
            template = self.jinja_env.get_template(template_name)
            html = template.render(
                scene=scene,
                avatar_config=self._get_avatar_config(scene_type),
                JS_BRIDGE=JS_BRIDGE
            )
            return html
        except Exception as e:
            log_error(f"Failed to render Jinja2 template {template_name}: {e}")
            return ""
