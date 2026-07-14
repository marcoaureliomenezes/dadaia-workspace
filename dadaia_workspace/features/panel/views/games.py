"""Games tab markup for the panel's local games."""

from __future__ import annotations


def render_games_section() -> str:
    """Render Snake (Codex), Breakout (PI), Pong (Codex), and Tetris (PI)."""
    return """
    <section id="section-games" class="section games-section" aria-label="Games" role="tabpanel"
      tabindex="0" aria-labelledby="tab-games">
      <header class="section-header games-header">
        <h2>Games</h2>
        <div class="games-switch" role="tablist" aria-label="Choose game">
          <button type="button" class="game-choice active" data-game="snake" role="tab"
            aria-selected="true">Snake <span>Codex</span></button>
          <button type="button" class="game-choice" data-game="breakout" role="tab"
            aria-selected="false">Breakout (PI)</button>
          <button type="button" class="game-choice" data-game="pong" role="tab"
            aria-selected="false">Pong (Codex)</button>
          <button type="button" class="game-choice" data-game="tetris" role="tab"
            aria-selected="false">Tetris <span>PI</span></button>
        </div>
      </header>
      <div class="games-stage">
        <article class="game-panel active" data-game-panel="snake" aria-label="Snake by Codex">
          <div class="game-meta"><strong>Snake</strong><span>Codex</span><output id="snake-score">0</output></div>
          <canvas id="snake-canvas" width="400" height="400" tabindex="0"
            aria-label="Snake game board"></canvas>
          <div class="game-toolbar">
            <button type="button" class="game-icon" data-action="snake-toggle" title="Start or pause"
              aria-label="Start or pause Snake">&#9654;</button>
            <button type="button" class="game-icon" data-action="snake-reset" title="Reset"
              aria-label="Reset Snake">&#8635;</button>
          </div>
          <div class="game-dpad" aria-label="Snake direction controls">
            <button type="button" data-snake-dir="up" aria-label="Up">&#8593;</button>
            <button type="button" data-snake-dir="left" aria-label="Left">&#8592;</button>
            <button type="button" data-snake-dir="down" aria-label="Down">&#8595;</button>
            <button type="button" data-snake-dir="right" aria-label="Right">&#8594;</button>
          </div>
        </article>
        <article class="game-panel" data-game-panel="breakout" aria-label="Breakout by PI" hidden>
          <div class="game-meta"><strong>Breakout</strong><span>PI</span><output id="breakout-score">0</output></div>
          <canvas id="breakout-canvas" width="480" height="320" tabindex="0"
            aria-label="Breakout game board"></canvas>
          <div class="game-toolbar">
            <button type="button" class="game-icon" data-action="breakout-toggle" title="Start or pause"
              aria-label="Start or pause Breakout">&#9654;</button>
            <button type="button" class="game-icon" data-action="breakout-reset" title="Reset"
              aria-label="Reset Breakout">&#8635;</button>
          </div>
          <div class="game-dpad" aria-label="Breakout direction controls">
            <button type="button" data-breakout-dir="left" aria-label="Left">&#8592;</button>
            <button type="button" data-breakout-dir="right" aria-label="Right">&#8594;</button>
          </div>
        </article>
        <article class="game-panel" data-game-panel="pong" aria-label="Pong by Codex" hidden>
          <div class="game-meta"><strong>Pong</strong><span>Codex</span><output id="pong-score">0</output></div>
          <canvas id="pong-canvas" width="480" height="320" tabindex="0"
            aria-label="Pong game board"></canvas>
          <div class="game-toolbar">
            <button type="button" class="game-icon" data-action="pong-toggle" title="Start or pause"
              aria-label="Start or pause Pong">&#9654;</button>
            <button type="button" class="game-icon" data-action="pong-reset" title="Reset"
              aria-label="Reset Pong">&#8635;</button>
          </div>
          <div class="game-dpad" aria-label="Pong direction controls">
            <button type="button" data-pong-dir="up" aria-label="Up">&#8593;</button>
            <button type="button" data-pong-dir="down" aria-label="Down">&#8595;</button>
          </div>
        </article>
        <article class="game-panel" data-game-panel="tetris" aria-label="Tetris by PI" hidden>
          <div class="game-meta"><strong>Tetris</strong><span>PI</span><output id="tetris-score">0</output></div>
          <canvas id="tetris-canvas" width="300" height="600" tabindex="0"
            aria-label="Tetris game board"></canvas>
          <div class="game-toolbar">
            <button type="button" class="game-icon" data-action="tetris-toggle" title="Start or pause"
              aria-label="Start or pause Tetris">&#9654;</button>
            <button type="button" class="game-icon" data-action="tetris-reset" title="Reset"
              aria-label="Reset Tetris">&#8635;</button>
          </div>
          <div class="game-controls" aria-label="Tetris controls">
            <button type="button" data-tetris-action="left" aria-label="Move left">&#8592;</button>
            <button type="button" data-tetris-action="rotate" aria-label="Rotate">&#8635;</button>
            <button type="button" data-tetris-action="right" aria-label="Move right">&#8594;</button>
            <button type="button" data-tetris-action="down" aria-label="Move down">&#8595;</button>
            <button type="button" data-tetris-action="drop" aria-label="Drop">&#8659;</button>
          </div>
        </article>
      </div>
    </section>"""
