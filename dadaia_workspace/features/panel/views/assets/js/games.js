(function () {
  'use strict';

  var snakeCanvas = document.getElementById('snake-canvas');
  var tetrisCanvas = document.getElementById('tetris-canvas');
  var pongCanvas = document.getElementById('pong-canvas');
  var breakoutCanvas = document.getElementById('breakout-canvas');
  if (!snakeCanvas || !tetrisCanvas) { return; }

  var hasPong = !!pongCanvas;
  var hasBreakout = !!breakoutCanvas;

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
    // Wall crossings WRAP to the opposite side (v0.2.5 wall-wrap semantics);
    // only self-collision resets the round.
    var head = {
      x: (snake[0].x + snakeDir.x + 20) % 20,
      y: (snake[0].y + snakeDir.y + 20) % 20
    };
    if (snake.some(function (p) { return p.x === head.x && p.y === head.y; })) { resetSnake(); return; }
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
  function drawTetris() { tetrisCtx.fillStyle = '#101713'; tetrisCtx.fillRect(0, 0, 300, 600); board.forEach(function (row, y) { row.forEach(function (cell, x) { if (cell) { drawCell(x, y, cell); } }); }); piece.shape.forEach(function (row, y) { row.forEach(function (cell, x) { if (cell) { drawCell(piece.x + x, piece.y + y, piece.color); } }); } ); }
  function toggleTetris() { if (tetrisTimer) { clearInterval(tetrisTimer); tetrisTimer = null; } else { tetrisTimer = setInterval(function () { movePiece(0, 1); drawTetris(); }, 500); tetrisCanvas.focus(); } }

  var pongCtx = hasPong ? pongCanvas.getContext('2d') : null;
  var pongBall = { x: 240, y: 160 };
  var pongVelocity = { x: 3, y: 2 };
  var pongPaddleY = 120;
  var pongPaddleDy = 0;
  var pongScore = 0;
  var pongTimer = null;
  var pongRandomSeed = 1;
  var pongSeedMultiplier = 1103515245;
  var pongSeedIncrement = 12345;
  var pongSeedModulus = 2147483648;
  var pongPaddleX = 10;
  var pongPaddleWidth = 12;
  var pongPaddleHeight = 70;
  var pongBallRadius = 8;
  var pongMaxSpeed = 12;
  var pongPaddleSpeed = 6;

  function setPongRandomSeed(seed) {
    var parsed = Number.parseInt(seed, 10);
    pongRandomSeed = Number.isNaN(parsed) ? 1 : parsed;
  }

  function nextPongRandom() {
    pongRandomSeed = ((pongRandomSeed * pongSeedMultiplier) + pongSeedIncrement) % pongSeedModulus;
    return pongRandomSeed / pongSeedModulus;
  }

  function clamp(value, minimum, maximum) {
    if (value < minimum) { return minimum; }
    if (value > maximum) { return maximum; }
    return value;
  }

  function drawPong() {
    if (!hasPong || !pongCtx) { return; }
    pongCtx.fillStyle = '#101713'; pongCtx.fillRect(0, 0, 480, 320);
    pongCtx.fillStyle = '#9cddc8';
    pongCtx.fillRect(pongPaddleX, pongPaddleY, pongPaddleWidth, pongPaddleHeight);
    pongCtx.fillStyle = '#f7af63';
    pongCtx.beginPath();
    pongCtx.arc(pongBall.x, pongBall.y, pongBallRadius, 0, Math.PI * 2, false);
    pongCtx.fill();
  }

  function setPongStateFrom(state) {
    if (!hasPong) { return; }
    if (Object.prototype.hasOwnProperty.call(state, 'ball')) { pongBall = { x: state.ball.x, y: state.ball.y }; }
    if (Object.prototype.hasOwnProperty.call(state, 'velocity')) {
      pongVelocity = { x: state.velocity.x, y: state.velocity.y };
    }
    if (Object.prototype.hasOwnProperty.call(state, 'paddleY')) { pongPaddleY = state.paddleY; }
    if (Object.prototype.hasOwnProperty.call(state, 'paddleDy')) { pongPaddleDy = state.paddleDy; }
    if (Object.prototype.hasOwnProperty.call(state, 'score')) {
      pongScore = state.score;
      document.getElementById('pong-score').value = pongScore;
    }
  }

  function setPongRunning(running) {
    if (!hasPong) { return; }
    if (running && !pongTimer) {
      pongTimer = setInterval(pongTick, 50);
      pongCanvas.focus();
    }
    if (!running && pongTimer) {
      clearInterval(pongTimer);
      pongTimer = null;
    }
  }

  function resetPong() {
    if (!hasPong) { return; }
    if (pongTimer) { clearInterval(pongTimer); pongTimer = null; }
    pongBall = { x: 240, y: 160 };
    pongVelocity = { x: 3, y: 2 };
    pongPaddleY = 120;
    pongPaddleDy = 0;
    pongScore = 0;
    document.getElementById('pong-score').value = pongScore;
    drawPong();
  }

  function setPongDirection(name) {
    if (!hasPong) { return; }
    if (name === 'up') { pongPaddleDy = -pongPaddleSpeed; }
    else if (name === 'down') { pongPaddleDy = pongPaddleSpeed; }
    else { pongPaddleDy = 0; }
  }

  function pongTick() {
    if (!hasPong) { return; }
    if (pongPaddleDy) {
      pongPaddleY += pongPaddleDy;
      pongPaddleY = clamp(pongPaddleY, 0, 320 - pongPaddleHeight);
    }

    pongBall.x += pongVelocity.x;
    pongBall.y += pongVelocity.y;
    pongVelocity.x = Number(pongVelocity.x);
    pongVelocity.y = Number(pongVelocity.y);

    if (pongBall.y - pongBallRadius <= 0 || pongBall.y + pongBallRadius >= 320) { pongVelocity.y = -pongVelocity.y; }
    if (pongBall.x + pongBallRadius >= 480) { pongVelocity.x = -pongVelocity.x; }

    if (pongVelocity.x < 0 && pongBall.x - pongBallRadius <= pongPaddleX + pongPaddleWidth) {
      if (pongBall.y + pongBallRadius >= pongPaddleY && pongBall.y - pongBallRadius <= pongPaddleY + pongPaddleHeight) {
        pongVelocity.x = Math.abs(pongVelocity.x);
        pongScore += 1;
        document.getElementById('pong-score').value = pongScore;
      } else {
        resetPong();
        return;
      }
    } else if (pongBall.x + pongBallRadius < 0) {
      resetPong();
      return;
    }

    drawPong();
  }

  var breakoutCtx = hasBreakout ? breakoutCanvas.getContext('2d') : null;
  var breakoutTimer = null;
  var breakoutBall = { x: 240, y: 160 };
  var breakoutVelocity = { x: 4, y: -4 };
  var breakoutScore = 0;
  var breakoutPaddle = {
    x: 190,
    y: 280,
    width: 100,
    height: 12,
    direction: 0
  };
  var breakoutPaddleSpeed = 10;
  var breakoutBallRadius = 8;
  var breakoutCanvasWidth = hasBreakout ? breakoutCanvas.width : 480;
  var breakoutCanvasHeight = hasBreakout ? breakoutCanvas.height : 320;
  var breakoutBrickRows = 5;
  var breakoutBrickCols = 8;
  var breakoutBrickTop = 20;
  var breakoutBrickLeft = 10;
  var breakoutBrickWidth = (breakoutCanvasWidth - breakoutBrickLeft * 2) / breakoutBrickCols;
  var breakoutBrickHeight = 14;
  var breakoutBricks = [];

  function resetBreakoutBricks() {
    breakoutBricks = Array.from({ length: breakoutBrickRows }, function () {
      return Array.from({ length: breakoutBrickCols }, function () { return 1; });
    });
  }

  function resetBreakout() {
    if (breakoutTimer) { clearInterval(breakoutTimer); breakoutTimer = null; }
    breakoutBall = { x: breakoutCanvasWidth / 2, y: breakoutCanvasHeight - 60 };
    breakoutVelocity = { x: 4, y: -4 };
    breakoutPaddle = {
      x: (breakoutCanvasWidth - breakoutPaddle.width) / 2,
      y: breakoutCanvasHeight - 26,
      width: 100,
      height: 12,
      direction: 0
    };
    breakoutScore = 0;
    resetBreakoutBricks();
    document.getElementById('breakout-score').value = breakoutScore;
    drawBreakout();
  }

  function drawBreakoutBricks() {
    if (!hasBreakout || !breakoutCtx) { return; }
    breakoutCtx.fillStyle = '#9cddc8';
    for (var row = 0; row < breakoutBrickRows; row++) {
      for (var col = 0; col < breakoutBrickCols; col++) {
        if (!breakoutBricks[row][col]) { continue; }
        var x = breakoutBrickLeft + col * breakoutBrickWidth;
        var y = breakoutBrickTop + row * breakoutBrickHeight;
        breakoutCtx.fillRect(x + 1, y + 1, breakoutBrickWidth - 2, breakoutBrickHeight - 2);
      }
    }
  }

  function drawBreakout() {
    if (!hasBreakout || !breakoutCtx) { return; }
    breakoutCtx.fillStyle = '#101713';
    breakoutCtx.fillRect(0, 0, breakoutCanvasWidth, breakoutCanvasHeight);
    drawBreakoutBricks();
    breakoutCtx.fillStyle = '#f7af63';
    breakoutCtx.fillRect(breakoutPaddle.x, breakoutPaddle.y, breakoutPaddle.width, breakoutPaddle.height);
    breakoutCtx.fillStyle = '#f4fff9';
    breakoutCtx.beginPath();
    breakoutCtx.arc(breakoutBall.x, breakoutBall.y, breakoutBallRadius, 0, Math.PI * 2, false);
    breakoutCtx.fill();
  }

  function clampBreakout(value, minimum, maximum) {
    if (value < minimum) { return minimum; }
    if (value > maximum) { return maximum; }
    return value;
  }

  function setBreakoutDirection(name) {
    if (name === 'left') { breakoutPaddle.direction = -breakoutPaddleSpeed; }
    else if (name === 'right') { breakoutPaddle.direction = breakoutPaddleSpeed; }
    else { breakoutPaddle.direction = 0; }
  }

  function breakoutBallIntersectsBrick(ballX, ballY, brickX, brickY, brickW, brickH) {
    var nearestX = clampBreakout(ballX, brickX, brickX + brickW);
    var nearestY = clampBreakout(ballY, brickY, brickY + brickH);
    var dx = ballX - nearestX;
    var dy = ballY - nearestY;
    return (dx * dx + dy * dy) <= (breakoutBallRadius * breakoutBallRadius);
  }

  function breakoutHandleBrickCollision() {
    for (var row = 0; row < breakoutBrickRows; row++) {
      for (var col = 0; col < breakoutBrickCols; col++) {
        if (!breakoutBricks[row][col]) { continue; }
        var brickX = breakoutBrickLeft + col * breakoutBrickWidth;
        var brickY = breakoutBrickTop + row * breakoutBrickHeight;
        if (breakoutBallIntersectsBrick(breakoutBall.x, breakoutBall.y, brickX, brickY, breakoutBrickWidth, breakoutBrickHeight)) {
          breakoutBricks[row][col] = 0;
          breakoutScore += 10;
          breakoutVelocity.y = -breakoutVelocity.y;
          document.getElementById('breakout-score').value = breakoutScore;
          return true;
        }
      }
    }
    return false;
  }

  function breakoutTick() {
    if (!hasBreakout) { return; }
    breakoutPaddle.x += breakoutPaddle.direction;
    breakoutPaddle.x = clampBreakout(breakoutPaddle.x, 0, breakoutCanvasWidth - breakoutPaddle.width);

    breakoutBall.x += breakoutVelocity.x;
    breakoutBall.y += breakoutVelocity.y;

    if (breakoutBall.x - breakoutBallRadius <= 0) {
      breakoutBall.x = breakoutBallRadius;
      breakoutVelocity.x = Math.abs(breakoutVelocity.x);
    }
    if (breakoutBall.x + breakoutBallRadius >= breakoutCanvasWidth) {
      breakoutBall.x = breakoutCanvasWidth - breakoutBallRadius;
      breakoutVelocity.x = -Math.abs(breakoutVelocity.x);
    }
    if (breakoutBall.y - breakoutBallRadius <= 0) {
      breakoutBall.y = breakoutBallRadius;
      breakoutVelocity.y = Math.abs(breakoutVelocity.y);
    }

    var hitsPaddle = breakoutVelocity.y > 0 &&
      breakoutBall.y + breakoutBallRadius >= breakoutPaddle.y &&
      breakoutBall.y - breakoutBallRadius <= breakoutPaddle.y + breakoutPaddle.height &&
      breakoutBall.x >= breakoutPaddle.x &&
      breakoutBall.x <= breakoutPaddle.x + breakoutPaddle.width;

    if (breakoutVelocity.y > 0 && breakoutBall.y + breakoutBallRadius >= breakoutCanvasHeight && !hitsPaddle) {
      resetBreakout();
      return;
    }

    if (hitsPaddle) {
      breakoutBall.y = breakoutPaddle.y - breakoutBallRadius;
      breakoutVelocity.y = -Math.abs(breakoutVelocity.y);
      breakoutVelocity.x += (breakoutBall.x - (breakoutPaddle.x + breakoutPaddle.width / 2)) / 16;
      if (breakoutVelocity.x > 8) { breakoutVelocity.x = 8; }
      if (breakoutVelocity.x < -8) { breakoutVelocity.x = -8; }
      if (breakoutVelocity.x >= 0) { breakoutVelocity.x = Math.max(2, breakoutVelocity.x); }
      else { breakoutVelocity.x = Math.min(-2, breakoutVelocity.x); }
    }

    breakoutHandleBrickCollision();

    drawBreakout();
  }

  function isPanelActive(game) {
    var panel = document.querySelector('[data-game-panel="' + game + '"]');
    return panel && !panel.hidden;
  }

  document.querySelectorAll('.game-choice').forEach(function (button) { button.addEventListener('click', function () {
      var game = button.dataset.game;
      document.querySelectorAll('.game-choice').forEach(function (b) {
        var active = b === button;
        b.classList.toggle('active', active);
        b.setAttribute('aria-selected', active ? 'true' : 'false');
      });
      document.querySelectorAll('[data-game-panel]').forEach(function (panel) {
        var active = panel.dataset.gamePanel === game;
        panel.classList.toggle('active', active);
        panel.hidden = !active;
      });
    }); });
  document.querySelectorAll('[data-snake-dir]').forEach(function (button) { button.addEventListener('click', function () {
      if (!isPanelActive('snake')) { return; }
      setSnakeDir(button.dataset.snakeDir);
    }); });
  document.querySelectorAll('[data-tetris-action]').forEach(function (button) { button.addEventListener('click', function () {
      if (!isPanelActive('tetris')) { return; }
      tetrisAction(button.dataset.tetrisAction);
    }); });
  document.querySelectorAll('[data-pong-dir]').forEach(function (button) { button.addEventListener('click', function () {
      if (!isPanelActive('pong')) { return; }
      setPongDirection(button.dataset.pongDir);
    }); });
  document.querySelectorAll('[data-breakout-dir]').forEach(function (button) { button.addEventListener('click', function () {
      if (!isPanelActive('breakout')) { return; }
      setBreakoutDirection(button.dataset.breakoutDir);
    }); });
  document.querySelector('[data-action="snake-toggle"]').addEventListener('click', function () {
    if (isPanelActive('snake')) { toggleSnake(); }
  });
  document.querySelector('[data-action="snake-reset"]').addEventListener('click', function () {
    if (isPanelActive('snake')) { resetSnake(); }
  });
  document.querySelector('[data-action="tetris-toggle"]').addEventListener('click', function () {
    if (isPanelActive('tetris')) { toggleTetris(); }
  });
  document.querySelector('[data-action="tetris-reset"]').addEventListener('click', function () {
    if (isPanelActive('tetris')) { resetTetris(); }
  });
  if (hasPong) {
    document.querySelector('[data-action="pong-toggle"]').addEventListener('click', function () {
      if (isPanelActive('pong')) { if (pongTimer) { clearInterval(pongTimer); pongTimer = null; } else { pongTimer = setInterval(pongTick, 50); } }
    });
    document.querySelector('[data-action="pong-reset"]').addEventListener('click', function () {
      if (isPanelActive('pong')) { resetPong(); }
    });
  }
  if (hasBreakout) {
    document.querySelector('[data-action="breakout-toggle"]').addEventListener('click', function () {
      if (!isPanelActive('breakout')) { return; }
      if (breakoutTimer) { clearInterval(breakoutTimer); breakoutTimer = null; }
      else { breakoutTimer = setInterval(breakoutTick, 33); breakoutCanvas.focus(); }
    });
    document.querySelector('[data-action="breakout-reset"]').addEventListener('click', function () {
      if (isPanelActive('breakout')) { resetBreakout(); }
    });
  }
  document.addEventListener('keydown', function (event) {
    if (isPanelActive('snake') && ['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(event.key)) {
      event.preventDefault();
      setSnakeDir(event.key.replace('Arrow', '').toLowerCase());
    } else if (isPanelActive('tetris')) {
      var map = { ArrowLeft: 'left', ArrowRight: 'right', ArrowDown: 'down', ArrowUp: 'rotate', ' ': 'drop' };
      if (map[event.key]) { event.preventDefault(); tetrisAction(map[event.key]); }
    } else if (isPanelActive('pong') && ['ArrowUp', 'ArrowDown'].includes(event.key)) {
      event.preventDefault();
      setPongDirection(event.key === 'ArrowUp' ? 'up' : 'down');
    } else if (isPanelActive('breakout') && ['ArrowLeft', 'ArrowRight'].includes(event.key)) {
      event.preventDefault();
      setBreakoutDirection(event.key === 'ArrowLeft' ? 'left' : 'right');
    }
  });

  if (window.__DADAIA_SNAKE_TEST_HOOK__ === true) {
    window.__dadaiaSnakeTest = {
      getState: function () {
        return {
          snake: snake.map(function (p) { return { x: p.x, y: p.y }; }),
          food: { x: food.x, y: food.y },
          direction: { x: snakeDir.x, y: snakeDir.y },
          nextDirection: { x: snakeNext.x, y: snakeNext.y },
          score: snakeScore,
          running: !!snakeTimer
        };
      },
      setState: function (state) {
        if (state.snake) { snake = state.snake.map(function (p) { return { x: p.x, y: p.y }; }); }
        if (state.food) { food = { x: state.food.x, y: state.food.y }; }
        if (state.direction) { snakeDir = { x: state.direction.x, y: state.direction.y }; }
        if (state.nextDirection) { snakeNext = { x: state.nextDirection.x, y: state.nextDirection.y }; }
        if (Object.prototype.hasOwnProperty.call(state, 'score')) { snakeScore = state.score; document.getElementById('snake-score').value = snakeScore; }
        if (Object.prototype.hasOwnProperty.call(state, 'running')) {
          if (state.running && !snakeTimer) { snakeTimer = setInterval(snakeTick, 115); }
          if (!state.running && snakeTimer) { clearInterval(snakeTimer); snakeTimer = null; }
        }
        drawSnake();
      },
      tick: function () { snakeTick(); },
      setDirection: function (name) { setSnakeDir(name); },
      reset: function () { resetSnake(); }
    };
  }

  if (window.__DADAIA_PONG_TEST_HOOK__ === true && hasPong) {
    window.__dadaiaPongTest = {
      getState: function () {
        return {
          ball: { x: pongBall.x, y: pongBall.y },
          velocity: { x: pongVelocity.x, y: pongVelocity.y },
          paddleY: pongPaddleY,
          paddleDy: pongPaddleDy,
          score: pongScore,
          running: !!pongTimer,
          randomSeed: pongRandomSeed
        };
      },
      setState: function (state) {
        setPongStateFrom(state);
        if (Object.prototype.hasOwnProperty.call(state, 'running')) { setPongRunning(state.running); }
        drawPong();
      },
      tick: function () { pongTick(); },
      setDirection: function (name) { setPongDirection(name); },
      keydown: function (key) { if (key === 'ArrowUp' || key === 'ArrowDown') { setPongDirection(key === 'ArrowUp' ? 'up' : 'down'); } },
      reset: function () { resetPong(); },
      setRandomSeed: setPongRandomSeed,
    };
  }

  if (window.__DADAIA_BREAKOUT_TEST_HOOK__ === true && hasBreakout) {
    window.__dadaiaBreakoutTest = {
      getState: function () {
        return {
          ball: { x: breakoutBall.x, y: breakoutBall.y },
          velocity: { x: breakoutVelocity.x, y: breakoutVelocity.y },
          score: breakoutScore,
          running: !!breakoutTimer,
          paddleX: breakoutPaddle.x,
          paddleY: breakoutPaddle.y,
          paddleWidth: breakoutPaddle.width,
          paddleHeight: breakoutPaddle.height,
          bricks: breakoutBricks.map(function (row) { return row.slice(0); }),
          rows: breakoutBrickRows,
          cols: breakoutBrickCols,
          brickTop: breakoutBrickTop,
          brickLeft: breakoutBrickLeft,
          brickWidth: breakoutBrickWidth,
          brickHeight: breakoutBrickHeight,
          canvasWidth: breakoutCanvasWidth,
          canvasHeight: breakoutCanvasHeight,
          ballRadius: breakoutBallRadius
        };
      },
      setState: function (state) {
        if (state.ball) { breakoutBall = { x: state.ball.x, y: state.ball.y }; }
        if (state.velocity) { breakoutVelocity = { x: state.velocity.x, y: state.velocity.y }; }
        if (Object.prototype.hasOwnProperty.call(state, 'score')) {
          breakoutScore = state.score;
          document.getElementById('breakout-score').value = breakoutScore;
        }
        if (Object.prototype.hasOwnProperty.call(state, 'paddleX')) { breakoutPaddle.x = state.paddleX; }
        if (Object.prototype.hasOwnProperty.call(state, 'paddleY')) { breakoutPaddle.y = state.paddleY; }
        if (Object.prototype.hasOwnProperty.call(state, 'paddleWidth')) { breakoutPaddle.width = state.paddleWidth; }
        if (Object.prototype.hasOwnProperty.call(state, 'paddleHeight')) { breakoutPaddle.height = state.paddleHeight; }
        if (Object.prototype.hasOwnProperty.call(state, 'direction')) { setBreakoutDirection(state.direction); }
        else { breakoutPaddle.direction = 0; }
        if (Object.prototype.hasOwnProperty.call(state, 'bricks')) { breakoutBricks = state.bricks.map(function (row) { return row.slice(0); }); }
        if (Object.prototype.hasOwnProperty.call(state, 'running')) {
          if (state.running && !breakoutTimer) { breakoutTimer = setInterval(breakoutTick, 33); }
          if (!state.running && breakoutTimer) { clearInterval(breakoutTimer); breakoutTimer = null; }
        }
        drawBreakout();
      },
      tick: function () { breakoutTick(); },
      setDirection: function (name) { setBreakoutDirection(name); },
      reset: function () { resetBreakout(); }
    };
  }

  resetSnake(); resetTetris();
  if (hasPong) { resetPong(); }
  if (hasBreakout) { resetBreakout(); }
})();
