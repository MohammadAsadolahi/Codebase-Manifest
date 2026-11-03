# Inspect contract — task-scoped, read only

Use this for `inspect <task or topic>`. Reply in chat; do not create or update `.architectureY/` documents.

## Discovery

1. Restate the specific behavior or code question. Start with relevant existing manifest entries if present; otherwise search current source. Existing documentation is a navigation hint, **not** evidence of behavior.
2. Locate the concrete entry point and follow direct calls only far enough to explain the requested change or question. Include relevant tests and direct data or cross-feature dependencies.
3. Check every reported path and symbol in current source. Keep references repository-relative. Cite line numbers only when verified by the tool's source view; never guess.
4. Rank locations by usefulness to the task: entry point, behavior owner, direct dependencies, then tests. Prefer 3–5 verified locations; include fewer if that is all the evidence supports, or more only when necessary.
5. Stop once the relevant flow is established. Mark uncertain relationships as unverified rather than inferring them from filenames, comments, or generated docs.

## Response

Use a compact answer with these sections:

- **Task:** one-sentence interpretation of the requested behavior.
- **Start here:** ranked paths and verified symbols, with a brief reason for each. Do not list a symbol unless it was found in source.
- **Verified flow:** a short sequence from the actual trigger to the behavior relevant to the task; omit if not established.
- **Dependencies and tests:** only directly relevant, source-confirmed files or checks.
- **Unknowns:** unresolved questions that matter to the requested task; omit when none remain.
- **Next step:** one concrete investigation or edit location for the developer, without making the edit.

If the source cannot be accessed or no relevant entry point is verified, say so explicitly; do not substitute plausible-sounding paths. Never claim to have executed tests or verified runtime behavior unless that actually occurred.
