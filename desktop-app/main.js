const { app, BrowserWindow } = require('electron');
const path = require('path');
const { spawn, execSync, spawnSync } = require('child_process');
const fs = require('fs');

let mainWindow;
let pyProcess;

function killPort5050() {
  try {
    execSync("lsof -ti:5050 | xargs kill -9 2>/dev/null || true");
    console.log("Port 5050 cleared successfully.");
  } catch (e) {
    // Ignore
  }
}

function findPython() {
  const possiblePaths = [
    '/usr/local/bin/python3',
    '/usr/local/opt/python@3.14/bin/python3',
    '/usr/local/opt/python@3.14/libexec/bin/python',
    '/usr/local/Cellar/python@3.14/3.14.6/bin/python3',
    '/opt/homebrew/bin/python3',
    '/Library/Frameworks/Python.framework/Versions/Current/bin/python3',
    '/usr/bin/python3',
    'python3'
  ];

  for (const p of possiblePaths) {
    try {
      if (fs.existsSync(p) || p === 'python3') {
        const test = spawnSync(p, ['-c', 'import flask; print("OK")'], { encoding: 'utf8', timeout: 3000 });
        if (test.status === 0 && test.stdout.includes('OK')) {
          console.log("Found verified Python with Flask:", p);
          return p;
        }
      }
    } catch (err) {
      // Continue searching
    }
  }

  // Fallback
  return '/usr/local/bin/python3';
}

function startBackend() {
  killPort5050();

  let baseDir = __dirname;
  if (baseDir.includes('app.asar')) {
    baseDir = baseDir.replace('app.asar', 'app.asar.unpacked');
  }

  let pyScript = path.join(baseDir, 'app.py');
  let cwd = baseDir;

  if (!fs.existsSync(pyScript)) {
    let parentScript = path.join(baseDir, '..', 'app.py');
    if (fs.existsSync(parentScript)) {
      pyScript = parentScript;
      cwd = path.join(baseDir, '..');
    }
  }

  const pythonExec = findPython();
  console.log("Using Python executable:", pythonExec, "Script:", pyScript);

  const env = Object.assign({}, process.env, {
    PYTHONUNBUFFERED: "1",
    PORT: "5050",
    PATH: '/usr/local/bin:/usr/local/opt/python@3.14/bin:/opt/homebrew/bin:/usr/bin:/bin:' + (process.env.PATH || '')
  });

  try {
    pyProcess = spawn(pythonExec, [pyScript], { cwd: cwd, env: env });

    pyProcess.stdout.on('data', (data) => {
      console.log(`[Python Backend]: ${data}`);
    });

    pyProcess.stderr.on('data', (data) => {
      console.error(`[Python Backend Error]: ${data}`);
    });

    pyProcess.on('exit', (code) => {
      console.log(`Python Backend exited with code ${code}`);
    });
  } catch (e) {
    console.error("Failed to start Python backend:", e);
  }
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1300,
    height: 860,
    minWidth: 1000,
    minHeight: 700,
    title: "SINYLON Badge Studio Pro",
    backgroundColor: "#0b0f19",
    show: false,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true
    }
  });

  let loaded = false;

  function tryLoadURL(retries = 40) {
    if (!mainWindow || mainWindow.isDestroyed()) return;

    mainWindow.loadURL('http://127.0.0.1:5050').then(() => {
      loaded = true;
      if (mainWindow && !mainWindow.isVisible()) {
        mainWindow.show();
      }
    }).catch(err => {
      if (retries > 0 && mainWindow && !mainWindow.isDestroyed()) {
        setTimeout(() => tryLoadURL(retries - 1), 500);
      } else {
        console.error("Failed to load backend URL after retries:", err);
        if (mainWindow && !mainWindow.isVisible()) {
          mainWindow.show();
        }
      }
    });
  }

  mainWindow.webContents.on('did-fail-load', () => {
    if (!loaded && mainWindow && !mainWindow.isDestroyed()) {
      setTimeout(() => tryLoadURL(20), 1000);
    }
  });

  if (mainWindow.webContents && mainWindow.webContents.session) {
    mainWindow.webContents.session.clearCache();
  }

  // Allow backend 300ms to bind, then start retrying
  setTimeout(() => tryLoadURL(), 300);

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

process.on('uncaughtException', (error) => {
  console.error('Uncaught Exception:', error);
});

app.whenReady().then(() => {
  startBackend();
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (pyProcess) {
    try {
      pyProcess.kill();
    } catch (e) {}
  }
  killPort5050();
  if (process.platform !== 'darwin') {
    app.quit();
  }
});
