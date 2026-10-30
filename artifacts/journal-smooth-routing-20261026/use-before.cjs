const fs = require('node:fs');
const oldSource = require('node:child_process').execFileSync('git', ['show', 'HEAD:site/js/journal.js'], {encoding: 'utf8'});
const originalRead = fs.readFileSync;
fs.readFileSync = function (file, ...args) {
  if (String(file).replaceAll('\\', '/').endsWith('site/js/journal.js')) return oldSource;
  return originalRead.call(this, file, ...args);
};
