# JARVIS automation safety policy (approval-first)

- Any mutating/external action (apply/submit/send/upload/delete/purchase/post) requires explicit user approval.
- JARVIS/OpenJarvis may draft, search, rank, prepare documents, and open pages; it must stop before final submission.
- Store credentials in OS/browser profile or approved secret store; never hardcode secrets.
- Log action proposals, approvals, and results.
- For job applying: prefer "prepare application packet + open form + wait for approval".
