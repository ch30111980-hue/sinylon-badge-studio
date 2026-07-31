const { app, BrowserWindow } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const fs = require('fs');

let mainWindow;
let pyProcess;

function findPython() {
  const possiblePaths = [
    '/usr/local/bin/python3',
    '/opt/homebrew/bin/python3',
    '/usr/bin/python3',
    '/Library/Frameworks/Python.framework/Versions/Current/bin/python3'
  ];
  for (const p of possiblePaths) {
    if (fs.existsSync(p)) {
      return p;
    }
  }
  return 'python3';
}

function startBackend() {
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
    PATH: '/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:' + (process.env.PATH || '')
  });

  try {
    pyProcess = spawn(pythonExec, [pyScript], { cwd: cwd, env: env });

    pyProcess.stdout.on('data', (data) => {
      console.log(`[Python Backend]: ${data}`);
    });

    pyProcess.stderr.on('data', (data) => {
      console.error(`[Python Backend Error]: ${data}`);
    });
  } catch (e) {
    console.error("Failed to start Python backend:", e);
  }
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 840,
    minWidth: 1000,
    minHeight: 700,
    title: "SINYLON Badge Studio Pro",
    show: true,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true
    }
  });

  function loadAppWithRetry(retries = 40) {
    if (!mainWindow || mainWindow.isDestroyed()) return;
    mainWindow.loadURL('http://127.0.0.1:5050').catch(err => {
      if (retries > 0 && mainWindow && !mainWindow.isDestroyed()) {
        setTimeout(() => loadAppWithRetry(retries - 1), 500);
      } else {
        console.error("Failed to load backend URL after 20 seconds:", err);
      }
    });
  }

  if (mainWindow.webContents && mainWindow.webContents.session) {
    mainWindow.webContents.session.clearCache();
  }

  loadAppWithRetry();

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
    pyProcess.kill();
  }
  if (process.platform !== 'darwin') {
    app.quit();
  }
});
