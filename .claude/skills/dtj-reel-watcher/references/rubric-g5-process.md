# G5 Process: faster, cheaper, fewer hand steps (after every job, and weekly over all jobs)

Input: the job's timeline (progress.json stages and times), credits used (Flow), Codex pictures made and redone, retries per
gate, every command the maker ran (worker log), files the maker wrote by hand (new scripts, hand-measured boxes, hand-edited
cut lists), the watcher verdicts and the person's changes. Compare with the runbook's time table
(`.claude/skills/dtj-ugc-reel/references/remake-a-reference-edit.md`, "Time").

Find and report (each with evidence and minutes lost):
1. The slowest steps vs the time table, and why (waiting for a person, generation, CPU render, retries).
2. Repeated hand work: the same kind of code written again, measuring done by eye, clicks a script could do, a check a
   person had to ask for twice. Each one gets a proposal: a script in the repo, or a READY TOOL (see `tools-radar.md`; then
   search the HyperFrames catalog, the Apify store, npm and GitHub for "<the job in plain words>"). Example of what this gate
   exists for: effects were hand-built in OpenCV three times before HyperFrames (448 ready moves) was installed - the watcher
   must have said "install HyperFrames and search its catalog" after the first time.
3. Rounds per gate: a gate that needed 2+ rounds twice in a row = the rubric or the runbook is missing a rule: write the rule.
4. Cost: credits per finished reel, Apify results per kept reference, CPU minutes per reel on the VPS.
5. The runbook: a step that no longer matches what was done, or a lesson not yet in its lessons log.
Output (JSON as in SKILL.md, gate "g5"): issues = what slowed or cost; ideas = each with effort and gain, tools named with
what they replace and their cost/licence; and a proposed lessons-log line for the runbook.
