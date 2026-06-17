---
name: sdd.develop
description: Full SDD pipeline — story → plan → implement in one session. Use when the user says "develop this feature", "build this", "full pipeline", or wants end-to-end development from description to code.
---

# SDD: Full Development Pipeline

Runs story → plan → implement in a single session, auto-detecting where to start.

IMPORTANT: Perform only the actions of the **current step**. Do NOT jump ahead.

## Output Protocol — MANDATORY

**Show ONLY:**
- Progress line per step: `[N/total] Step description...    done`
- Questions requiring user input (contracts, clarifications, approvals)
- Phase results: `PASS` or `BLOCK: [1-line reason]`
- Final artifact paths

**Do NOT output:** full file contents, internal reasoning, verbose explanations.

**Example:**
```
[1/6] Reading project context...                  done
[2/6] Writing story...                            done → specs/.../story.md
[3/6] Defining contracts and phases...
  Proposed contracts: [contract list]
  Phases: [phase list]
  → Do you approve?
[4/6] Writing plan...                             done → specs/.../plan.md
[5/6] Implementing...
  Phase 1/3...  PASS    Phase 2/3...  PASS    Phase 3/3 (final)...  PASS
[6/6] Finalizing...                               done → specs/.../resume.md
```

---

## Phase 0: Initialize and detect state

1. **Read and validate settings.** Read `.sdd.json` — resolve `docs`, `specs`, and `run_tests`.

   **If `.sdd.json` does not exist or is missing `paths.docs` / `paths.specs`**: stop and inform the user:
   *"No `.sdd.json` found (or missing required paths). Run `sdd init` first to initialize this project."*

   **If `paths.run_tests` is missing or the script does not exist on disk**: warn the user:
   *"Test runner not configured. Tests will be skipped after each phase. Run `/sdd.util.makeruntest` to generate test scripts."*
   Continue but skip test execution in Phase 3.

2. **Detect starting point.**
   - **Plan path** → check for current phase → go to **Phase 3**
   - **Story path** → note spec folder → go to **Phase 2**
   - **Spec folder** → Glob: has `plan.md` → Phase 3; has `story.md` only → Phase 2; neither → Phase 1
   - **Feature description, Jira key, and/or Figma URL** → go to **Phase 1**
   - **Unclear** → ask: "Start a new feature", "Continue from a story", "Continue from a plan"

   Note: a feature description may include a Figma URL (e.g., `https://figma.com/design/...?node-id=...`).
   This is still a Phase 1 start — the Figma URL will be processed during story creation.

---

## Phase 1: Story

3. **Read project docs.** Read the following for context:
   - `{docs}/code/`
   - `{docs}/architecture/`
   - `{docs}/business/`

4. **Check for external context (optional — Jira and/or Figma).**
   If the user provided a Jira ticket key/URL or a Figma URL, extract context from these sources before
   writing the story. Follow the detailed procedures in **`.claude/skills/sdd.story/references/mcp-integrations.md`**.

   Summary:
   - **Jira ticket**: detect MCP tools → fetch issue + comments → summarize → ask for additions → skip step 5.
   - **Figma URL**: detect MCP tools → fetch design context, screenshot, variables → summarize → populate Visual Spec.
   - Both can be provided in the same request — process both.
   - If MCP tools are unavailable, inform with install instructions and ask for manual input.

5. **If no ticket and no Figma URL:** Ask the user to describe the feature.

6. **Clarify if needed.** Evaluate whether the description is clear enough. If ambiguities exist, ask
   **up to 3 targeted questions** per round (max 2 rounds). Only ask when the answer materially changes the story.

7. **Create spec folder:** Run `~/.sdd/scripts/sdd-spec.sh {specs} "{feature_slug}"`.
   Capture the output path for subsequent steps.

8. **Confirm before writing.** Present a brief summary of what the story will cover (title, key AC, scope) and ask the
   user to confirm or adjust before writing the file.

9. **Write the story.** Read `.claude/skills/sdd.story/template.md`, fill it with gathered information. Save as
   `story.md` in the spec folder. Also save `original_request.md` with the raw user input.

→ Transition to Phase 2.

---

## Phase 2: Plan

10. **Read project docs (if entering directly).** If starting from Phase 2 (story path provided, no Phase 1), read:
   - `{docs}/code/`
   - `{docs}/architecture/`
   - `{docs}/testing/`
   - Evaluate the story and read contextual docs as needed (database, business logic, API collections, config).

11. **Read the story.** If entering from Phase 1, you already have it. Otherwise, read the story file.
    Check for existing `plan.md` — run `~/.sdd/scripts/sdd-plan-name.sh {spec_folder}` to get the correct filename
    (`plan.md` or `{timestamp}_plan.md`).

12. **Propose contracts and phases.** Based on the story and project context, propose:
    - Public contracts (services, events, tests, DB schema, UI copies)
    - If the story has a **Visual Spec** section: include **UI/Design** contracts (components with Figma node refs, design token mappings, assets)
    - Implementation phases (with Figma node references in action items when Visual Spec is present)

    Present the proposal to the user.

13. **Clarify if needed.** Max 3 questions, max 2 rounds.

14. **User approval required.** Do NOT proceed until the user agrees on contracts and phases.

15. **Write the plan.** Read `.claude/skills/sdd.plan/template.md`, fill with approved contracts and phases. Save using
    the filename from `~/.sdd/scripts/sdd-plan-name.sh` in the spec folder.

16. **Update story status.** Run `~/.sdd/scripts/sdd-update-status.sh {story_path} "Status" "In Progress"` (only if current Status is `Draft`).

→ Transition to Phase 3.

---

## Phase 3: Implement

17. **Read the plan and identify current phase.** Run `~/.sdd/scripts/sdd-check-phase.sh {plan_path}` to find the current
    phase. If it returns "done", all phases are complete — go to step 22.

17b. **Offer to create a feature branch (first phase only).** Before executing the first phase, run
    `git branch --show-current` and compare with `baseBranch` from `.sdd.json` (default: `develop`).

    - **If on baseBranch**: ask the user: *"You are on `{baseBranch}`. Create a feature branch?"*
      Do NOT skip this question. Do NOT create a branch without asking.
      - If **yes**: run `~/.sdd/scripts/sdd-branch-name.sh {spec_folder}` to get a suggested name.
        Let the user confirm or type a different name.
        Then run: `~/.sdd/scripts/sdd-branch.sh "<branch-name>"`
      - If **no**: continue on current branch.
    - **If already on a feature branch**: skip silently.

    Only runs before the first phase. Do NOT repeat for subsequent phases.

18. **Execute the current phase.** Implement all action items listed in the current phase's to-do list.

18b. **Visual reference (optional).** If the phase references Figma nodes and Figma MCP tools are available,
    use them for visual verification. Follow **`.claude/skills/sdd.implement/references/figma-verification.md`**.
    Skip if Figma MCP is not available.

19. **Run tests.** After completing the phase, run `{run_tests}`.
    - If tests **pass**: proceed to step 19a.
    - If tests **fail**: analyze the failure, fix the issue, re-run tests. Repeat until all tests pass.

19a. **E2E browser verification (optional — Playwright CLI).** Only run this step if **all three**
    conditions are met:
    1. `.sdd.json` contains a `playwright` config section
    2. `playwright-cli` is available (installed via `@playwright/cli`)
    3. The current phase has action items that affect **UI, routes, or visible components**
       (e.g., pages, layouts, forms, navigation). Skip silently for phases that only touch
       backend logic, tests, refactoring, config, or documentation.

    **Open the browser with:** `playwright-cli open --headed {playwright.baseUrl}`
    The `--headed` flag is **mandatory** — without it the user cannot see the browser.
    NEVER run `playwright-cli open` without `--headed`.

    Then follow the detailed procedure in **`.claude/skills/sdd.implement/references/playwright-verification.md`**
    to authenticate (if configured), execute the user flow from the **source story**, and verify the results.

    - If verification **fails**: fix the code **and** update the tests, then re-run step 19 before continuing.
    - If any condition above is not met: skip silently.

20. **Update the plan.** Check the completed action items (`- [x]`). Update the **Next Step** section.

21. **More phases?** Show progress line, return to step 18 for the next phase.

22. **Finalize (all phases done).**
    a. **Write resume.** Read `.claude/skills/sdd.implement/template.md`, fill it. Save as `resume.md` in the spec folder.
    b. **Update plan:** Run `~/.sdd/scripts/sdd-update-status.sh {plan_path} "Status" "Done"` and update Next Step to
       "All phases completed. See resume.md."
    c. **Update story:** Run `~/.sdd/scripts/sdd-update-status.sh {story_path} "Status" "Done"` and
       `~/.sdd/scripts/sdd-update-status.sh {story_path} "Plan implemented" "@{plan_path}"`.

---

## Error Handling

If an irrecoverable error occurs at any point during the pipeline (e.g., missing files, tool failures, unresolvable test failures),
stop and report the error to the user with the current phase and a brief description.
This is **best-effort** — if the error prevents running the script, skip it.

---

# Important Notes

- **One step at a time.** NEVER jump ahead to a future phase or step. Complete current → validate → move on.
- **User approval is mandatory in Phase 2.** Do NOT write the plan until the user agrees on contracts and phases.
- **Output Protocol is mandatory.** Follow the progress line format strictly. No verbose output.
- **Sub-skill resources are authoritative.** When this skill references files from `sdd.story`, `sdd.plan`,
  or `sdd.implement`, those files are the source of truth for the detailed procedures.

# Language

Write all artifacts in the **same language the user used**. Template field names (Status, Created at, etc.)
stay in English.
