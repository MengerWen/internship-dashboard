const path = require('node:path');

// 临时验收结果集中存放；需要长期保存的证据再选入 artifacts/。
function artifactDirectory(task, env = process.env) {
  if (!/^[a-z0-9][a-z0-9_-]*$/i.test(task)) {
    throw new Error('验收任务名称只能包含字母、数字、下划线和短横线');
  }
  return env.JOURNAL_ARTIFACT_DIR
    ? path.resolve(env.JOURNAL_ARTIFACT_DIR)
    : path.resolve(__dirname, '..', '.local', 'runs', task);
}

module.exports = {artifactDirectory};
