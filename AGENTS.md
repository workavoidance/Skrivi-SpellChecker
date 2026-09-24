# Source of truth and continuity

- Work from this Git checkout and workavoidance/Skrivi-SpellChecker. Do not use hidden ChatGPT project folders as working source.
- Read README.md and STATUS.md first. Application: sandbox/. Launcher: sandbox/Start-Skrivi.cmd.
- Commit completed changes and push to a task branch or explicitly authorised branch. Use PRs for subsequent behavioural changes. Verify remote commits before claiming work is saved on GitHub.
- Update STATUS.md with experiment revision, settings, results location and next action. Distinguish historical results from newly reproduced measurements.
- Keep pupil writing, benchmark corpora, model files and logs out of Git and cloud inference. Inspect staged content before publication; .gitignore is not a privacy validator.
- The complete recovered original is under ignored data/local/recovered-original/. Check that and docs/RECOVERY-MANIFEST.json before asking the user to find source files.
- Reuse the persistent cache; no implicit downloads during launch. No large models or paid services without authorisation.
- Preserve authorship. Keep experimental changes separate from defaults until measured improvements justify promotion.
