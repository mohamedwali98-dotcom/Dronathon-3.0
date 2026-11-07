// PreToolUse (Bash): block git commit/push commands that would credit Claude in this repo.
// Owner rule: commits are authored by mohamedwali98-dotcom only, never Claude.
let raw = '';
process.stdin.on('data', d => (raw += d)).on('end', () => {
  const cmd = JSON.parse(raw || '{}').tool_input?.command || '';
  if (!/\bgit\b[^|;&]*\b(commit|merge|tag|rebase|cherry-pick)\b/.test(cmd)) return;
  if (!/co-authored-by|generated with \[?claude|noreply@anthropic\.com|--author[= ]["']?claude/i.test(cmd)) return;
  console.log(JSON.stringify({
    hookSpecificOutput: {
      hookEventName: 'PreToolUse',
      permissionDecision: 'deny',
      permissionDecisionReason:
        'Repo rule: no Claude attribution. Remove Co-Authored-By / "Generated with Claude" / Claude author ' +
        'from the git command; commits must be authored only by mohamedwali98-dotcom.',
    },
  }));
});
