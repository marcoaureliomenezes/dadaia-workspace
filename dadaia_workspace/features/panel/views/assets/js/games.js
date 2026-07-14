(function () {
  'use strict';

  var snakeCanvas = document.getElementById('snake-canvas');
  var tetrisCanvas = document.getElementById('tetris-canvas');
  if (!snakeCanvas || !tetrisCanvas) { return; }

  var snakeCtx = snakeCanvas.getContext('2d');
  var snake = [];
  var food = { x: 14, y: 10 };
  var snakeDir = { x: 1, y: 0 };
  var snakeNext = { x: 1, y: 0 };
  var snakeTimer = null;
  var snakeScore = 0;

  function resetSnake() {
    if (snakeTimer) { clearInterval(snakeTimer); snakeTimer = null; }
    snake = [{ x: 8, y: 10 }, { x: 7, y: 10 }, { x: 6, y: 10 }];
    snakeDir = { x: 1, y: 0 }; snakeNext = { x: 1, y: 0 }; snakeScore = 0;
    food = { x: 14, y: 10 };
    document.getElementById('snake-score').value = snakeScore;
    drawSnake();
  }

  function placeFood() {
    do { food = { x: Math.floor(Math.random() * 20), y: Math.floor(Math.random() * 20) }; }
    while (snake.some(function (p) { return p.x === food.x && p.y === food.y; }));
  }

  function drawSnake() {
    snakeCtx.fillStyle = '#101713'; snakeCtx.fillRect(0, 0, 400, 400);
    snakeCtx.strokeStyle = '#1d2921';
    for (var i = 20; i < 400; i += 20) { snakeCtx.beginPath(); snakeCtx.moveTo(i, 0); snakeCtx.lineTo(i, 400); snakeCtx.stroke(); snakeCtx.beginPath(); snakeCtx.moveTo(0, i); snakeCtx.lineTo(400, i); snakeCtx.stroke(); }
    snakeCtx.fillStyle = '#f7af63'; snakeCtx.fillRect(food.x * 20 + 3, food.y * 20 + 3, 14, 14);
    snake.forEach(function (p, idx) { snakeCtx.fillStyle = idx === 0 ? '#f4fff9' : '#9cddc8'; snakeCtx.fillRect(p.x * 20 + 2, p.y * 20 + 2, 16, 16); });
  }

  function snakeTick() {
    snakeDir = snakeNext;
    var head = { x: snake[0].x + snakeDir.x, y: snake[0].y + snakeDir.y };
    if (head.x < 0 || head.x >= 20 || head.y < 0 || head.y >= 20 || snake.some(function (p) { return p.x === head.x && p.y === head.y; })) { resetSnake(); return; }
    snake.unshift(head);
    if (head.x === food.x && head.y === food.y) { snakeScore += 10; document.getElementById('snake-score').value = snakeScore; placeFood(); } else { snake.pop(); }
    drawSnake();
  }

  function setSnakeDir(name) {
    var dirs = { up: { x: 0, y: -1 }, down: { x: 0, y: 1 }, left: { x: -1, y: 0 }, right: { x: 1, y: 0 } };
    var next = dirs[name];
    if (next && !(next.x === -snakeDir.x && next.y === -snakeDir.y)) { snakeNext = next; }
  }

  function toggleSnake() { if (snakeTimer) { clearInterval(snakeTimer); snakeTimer = null; } else { snakeTimer = setInterval(snakeTick, 115); snakeCanvas.focus(); } }

  var tetrisCtx = tetrisCanvas.getContext('2d');
  var board, piece, tetrisTimer, tetrisScore;
  var shapes = [
    [[1, 1, 1, 1]], [[1, 1], [1, 1]], [[0, 1, 0], [1, 1, 1]],
    [[1, 0, 0], [1, 1, 1]], [[0, 0, 1], [1, 1, 1]], [[0, 1, 1], [1, 1, 0]], [[1, 1, 0], [0, 1, 1]]
  ];
  var colors = ['#9cddc8', '#ddd9ab', '#f7af63', '#bfd8ad', '#e98778', '#8ab7d8', '#c6a8d8'];

  function newPiece() { var idx = Math.floor(Math.random() * shapes.length); return { shape: shapes[idx], color: colors[idx], x: 3, y: 0 }; }
  function resetTetris() { if (tetrisTimer) { clearInterval(tetrisTimer); tetrisTimer = null; } board = Array.from({ length: 20 }, function () { return Array(10).fill(null); }); piece = newPiece(); tetrisScore = 0; document.getElementById('tetris-score').value = tetrisScore; drawTetris(); }
  function collides(candidate) { return candidate.shape.some(function (row, y) { return row.some(function (cell, x) { var bx = candidate.x + x, by = candidate.y + y; return cell && (bx < 0 || bx >= 10 || by >= 20 || (by >= 0 && board[by][bx])); }); }); }
  function lockPiece() { piece.shape.forEach(function (row, y) { row.forEach(function (cell, x) { if (cell && piece.y + y >= 0) { board[piece.y + y][piece.x + x] = piece.color; } }); }); var before = board.length; board = board.filter(function (row) { return row.some(function (cell) { return !cell; }); }); var cleared = before - board.length; while (board.length < 20) { board.unshift(Array(10).fill(null)); } if (cleared) { tetrisScore += [0, 100, 300, 500, 800][cleared]; document.getElementById('tetris-score').value = tetrisScore; } piece = newPiece(); if (collides(piece)) { resetTetris(); } }
  function movePiece(dx, dy) { var next = { shape: piece.shape, color: piece.color, x: piece.x + dx, y: piece.y + dy }; if (!collides(next)) { piece = next; return true; } if (dy > 0) { lockPiece(); } return false; }
  function rotatePiece() { var rotated = piece.shape[0].map(function (_, i) { return piece.shape.map(function (row) { return row[i]; }).reverse(); }); var next = { shape: rotated, color: piece.color, x: piece.x, y: piece.y }; if (!collides(next)) { piece = next; } }
  function tetrisAction(action) { if (action === 'left') { movePiece(-1, 0); } else if (action === 'right') { movePiece(1, 0); } else if (action === 'down') { movePiece(0, 1); } else if (action === 'rotate') { rotatePiece(); } else if (action === 'drop') { while (movePiece(0, 1)) {} } drawTetris(); }
  function drawCell(x, y, color) { tetrisCtx.fillStyle = color; tetrisCtx.fillRect(x * 30 + 1, y * 30 + 1, 28, 28); }
  function drawTetris() { tetrisCtx.fillStyle = '#101713'; tetrisCtx.fillRect(0, 0, 300, 600); board.forEach(function (row, y) { row.forEach(function (cell, x) { if (cell) { drawCell(x, y, cell); } }); }); piece.shape.forEach(function (row, y) { row.forEach(function (cell, x) { if (cell) { drawCell(piece.x + x, piece.y + y, piece.color); } }); }); }
  function toggleTetris() { if (tetrisTimer) { clearInterval(tetrisTimer); tetrisTimer = null; } else { tetrisTimer = setInterval(function () { movePiece(0, 1); drawTetris(); }, 500); tetrisCanvas.focus(); } }

  document.querySelectorAll('.game-choice').forEach(function (button) { button.addEventListener('click', function () { var game = button.dataset.game; document.querySelectorAll('.game-choice').forEach(function (b) { var active = b === button; b.classList.toggle('active', active); b.setAttribute('aria-selected', active ? 'true' : 'false'); }); document.querySelectorAll('[data-game-panel]').forEach(function (panel) { var active = panel.dataset.gamePanel === game; panel.classList.toggle('active', active); panel.hidden = !active; }); }); });
  document.querySelectorAll('[data-snake-dir]').forEach(function (button) { button.addEventListener('click', function () { setSnakeDir(button.dataset.snakeDir); }); });
  document.querySelectorAll('[data-tetris-action]').forEach(function (button) { button.addEventListener('click', function () { tetrisAction(button.dataset.tetrisAction); }); });
  document.querySelector('[data-action="snake-toggle"]').addEventListener('click', toggleSnake);
  document.querySelector('[data-action="snake-reset"]').addEventListener('click', resetSnake);
  document.querySelector('[data-action="tetris-toggle"]').addEventListener('click', toggleTetris);
  document.querySelector('[data-action="tetris-reset"]').addEventListener('click', resetTetris);
  document.addEventListener('keydown', function (event) { var snakePanel = document.querySelector('[data-game-panel="snake"]'); if (!snakePanel.hidden && ['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(event.key)) { event.preventDefault(); setSnakeDir(event.key.replace('Arrow', '').toLowerCase()); } else if (!document.querySelector('[data-game-panel="tetris"]').hidden) { var map = { ArrowLeft: 'left', ArrowRight: 'right', ArrowDown: 'down', ArrowUp: 'rotate', ' ': 'drop' }; if (map[event.key]) { event.preventDefault(); tetrisAction(map[event.key]); } } });

  resetSnake(); resetTetris();
})();
