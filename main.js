const { app, BrowserWindow } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const fs = require('fs');

let mainWindow;
let pyProcess;

function findPython() {
  const possiblePaths = [
    '/usr/local/bin/python3',
    '/usr/local/opt/python@3.14/bin/python3.14',
    '/opt/homebrew/bin/python3',
    '/usr/bin/python3'
  ];
  for (const p of possiblePaths) {
    if (fs.existsSync(p)) {
      return p;
    }
  }
  return 'python3';
}

function startBackend() {
  let pyScript = path.join(__dirname, 'app.py');
  let cwd = __dirname;

  if (!fs.existsSync(pyScript)) {
    let parentScript = path.join(__dirname, '..', 'app.py');
    if (fs.existsSync(parentScript)) {
      pyScript = parentScript;
      cwd = path.join(__dirname, '..');
    }
  }

  const pythonExec = findPython();
  console.log("Using Python executable:", pythonExec, "Script:", pyScript);

  const env = Object.assign({}, process.env, {
    PATH: '/usr/local/bin:/usr/local/opt/python@3.14/bin:/opt/homebrew/bin:/usr/bin:/bin:' + (process.env.PATH || '')
  });

  pyProcess = spawn(pythonExec, [pyScript], { cwd: cwd, env: env });

  pyProcess.stdout.on('data', (data) => {
    console.log(`[Python Backend]: ${data}`);
  });

  pyProcess.stderr.on('data', (data) => {
    console.error(`[Python Backend Error]: ${data}`);
  });
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

  function loadAppWithRetry(retries = 20) {
    mainWindow.loadURL('http://127.0.0.1:5050').catch(err => {
      if (retries > 0) {
        setTimeout(() => loadAppWithRetry(retries - 1), 500);
      }
    });
  }

  loadAppWithRetry();

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

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
