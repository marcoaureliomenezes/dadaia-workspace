"""Panel Games tab styles."""

GAMES_CSS: str = """
.games-header { align-items: center; }
.games-switch { display: flex; gap: var(--space-2xs); border: 1px solid var(--color-border); padding: var(--space-2xs); border-radius: var(--radius-card); }
.game-choice { min-height: var(--control-height); padding: var(--control-pad-y) var(--control-pad-x); border: 0; border-radius: var(--radius); background: transparent; color: var(--color-muted); font: inherit; cursor: pointer; }
.game-choice span { margin-left: var(--space-xs); font-family: var(--font-mono); font-size: var(--text-xs); }
.game-choice.active { background: var(--color-heading); color: var(--color-surface); }
.game-choice:focus-visible, .game-icon:focus-visible, .game-dpad button:focus-visible, .game-controls button:focus-visible { outline: var(--focus-ring-width) solid var(--color-accent-dark); outline-offset: var(--focus-ring-offset); }
.games-stage { display: grid; place-items: start center; }
.game-panel { width: min(100%, 520px); border: 1px solid var(--color-border-card); border-radius: var(--radius-card); background: var(--color-surface); padding: var(--space-md); box-shadow: var(--shadow-card-rest); }
.game-panel[hidden] { display: none; }
.game-meta { display: grid; grid-template-columns: 1fr auto auto; align-items: baseline; gap: var(--space-md); margin-bottom: var(--space-sm); }
.game-meta strong { font-size: var(--text-xl); }
.game-meta span { color: var(--color-muted); font-family: var(--font-mono); font-size: var(--text-sm); }
.game-meta output { min-width: 5ch; text-align: right; font: var(--font-weight-semibold) var(--text-lg) var(--font-mono); }
.game-panel canvas { display: block; width: min(100%, 400px); height: auto; aspect-ratio: 1; margin: 0 auto; background: #101713; border: 1px solid var(--color-border-strong); border-radius: var(--radius); image-rendering: pixelated; }
.game-panel[data-game-panel="tetris"] canvas { width: min(100%, 300px); aspect-ratio: 1 / 2; }
.game-toolbar { display: flex; justify-content: center; gap: var(--space-sm); margin-top: var(--space-sm); }
.game-icon, .game-dpad button, .game-controls button { display: inline-grid; place-items: center; width: 42px; height: 42px; border: 1px solid var(--color-border); border-radius: var(--radius); background: var(--color-surface); color: var(--color-heading); font-size: var(--text-xl); cursor: pointer; }
.game-icon:hover, .game-dpad button:hover, .game-controls button:hover { background: var(--color-primary-bg); border-color: var(--color-accent-dark); }
.game-dpad { width: 134px; margin: var(--space-sm) auto 0; display: grid; grid-template-columns: repeat(3, 42px); grid-template-rows: repeat(2, 42px); gap: 4px; }
.game-dpad [data-snake-dir="up"] { grid-column: 2; }
.game-dpad [data-snake-dir="left"] { grid-column: 1; grid-row: 2; }
.game-dpad [data-snake-dir="down"] { grid-column: 2; grid-row: 2; }
.game-dpad [data-snake-dir="right"] { grid-column: 3; grid-row: 2; }
.game-controls { display: flex; flex-wrap: wrap; justify-content: center; gap: var(--space-xs); margin-top: var(--space-sm); }
@media (max-width: 640px) { .games-header { align-items: flex-start; } .games-switch { width: 100%; } .game-choice { flex: 1; } .game-panel { padding: var(--space-sm); } }
"""
