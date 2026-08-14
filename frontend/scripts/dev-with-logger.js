const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

// Ensure logs directory exists
const logDir = path.join(__dirname, '..', 'logs');
if (!fs.existsSync(logDir)) {
  fs.mkdirSync(logDir, { recursive: true });
}

const logFile = path.join(logDir, 'frontend.log');
const logStream = fs.createWriteStream(logFile, { flags: 'a' });

// Log startup timestamp
const timestamp = new Date().toISOString();
const startHeader = `\n=== Frontend Dev Server Started [${timestamp}] ===\n`;
process.stdout.write(startHeader);
logStream.write(startHeader);

// Spawn Next.js dev server
const isWin = process.platform === 'win32';
const nextCmd = isWin ? 'npx.cmd' : 'npx';
const child = spawn(nextCmd, ['next', 'dev'], {
  cwd: path.join(__dirname, '..'),
  env: process.env,
  shell: true,
});

child.stdout.on('data', (data) => {
  process.stdout.write(data);
  logStream.write(data);
});

child.stderr.on('data', (data) => {
  process.stderr.write(data);
  logStream.write(data);
});

child.on('close', (code) => {
  const endFooter = `\n=== Frontend Dev Server Stopped [Code: ${code}] ===\n`;
  process.stdout.write(endFooter);
  logStream.write(endFooter);
  logStream.end();
  process.exit(code || 0);
});

// Handle termination signals cleanly
process.on('SIGINT', () => {
  child.kill('SIGINT');
});

process.on('SIGTERM', () => {
  child.kill('SIGTERM');
});
