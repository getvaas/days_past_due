---
name: sdd.implement
description: Implement a plan phase by phase, running tests after each phase. Use when the user says "implement plan", "execute plan", "run the plan", or provides a plan path to build.
---

# Spec Driven Development (SDD): Plan Implementation

A skill that executes an implementation plan phase by phase, verifying tests after each phase, and generating a resume when all phases are complete.

# When to Use This Skill

## Ideal scenarios:

- When the user needs to implement a plan that was previously created with the `sdd.plan` skill.

IMPORTANT: Perform only the actions of the **current phase**. Do NOT jump ahead to future phases.

# How to implement a plan

1. **Read and validate the project settings.** Read `.sdd.json` to resolve the dynamic paths for `docs`, `specs`,
   and `run_tests`. Use these paths throughout the rest of the steps.

   **If `.sdd.json` does not exist or is missing `paths.specs`**: stop and inform the user:
   _"No `.sdd.json` found (or missing required paths). Run `sdd init` first to initialize this project."_
   Do NOT proceed without valid paths.

   **If `paths.run_tests` is missing or the script file does not exist on disk**: warn the user:
   _"Test runner not configured (`paths.run_tests` missing or script not found). Tests will be skipped
   after each phase. Run `/sdd.util.makeruntest` to generate test scripts."_
   Continue with implementation but skip step 5 (test execution) for each phase.

2. **Identify the source plan.** If the user provided the path to the plan, read it. If the user did NOT provide the
   path, ask the user which plan to implement using AskUserQuestion. Do NOT proceed until you have a valid plan to
   execute.

   Example question:
   - "Which plan should I implement? Please provide the path to the plan file (e.g., `{paths.specs}/<folder>/plan.md`)."

3. Run `~/.sdd/scripts/sdd-check-phase.sh {plan_path}` to identify the **current phase**. If it returns "done",
   all phases are complete — skip to step 8.

3b. **Offer to create a feature branch (first phase only).** Before executing the first phase, check the current
branch by running `git branch --show-current`. Compare it with `baseBranch` from `.sdd.json` (default: `develop`).

- **If on baseBranch**: ask the user: _"You are on `{baseBranch}`. Create a feature branch for this implementation?"_
  Do NOT skip this question. Do NOT create a branch without asking.
  - If **yes**: run `~/.sdd/scripts/sdd-branch-name.sh {spec_folder}` to get a suggested name.
    Let the user confirm or type a different name.
    Then run: `~/.sdd/scripts/sdd-branch.sh "<branch-name>"`
  - If **no**: continue on current branch.
- **If already on a feature branch** (not baseBranch): skip this step silently.

This step runs **only once** before the first phase. Do NOT repeat it for subsequent phases.

4. **Execute the current phase.** Implement all the actions listed in the current phase's to-do list.

4b. **Visual reference (optional — Figma MCP).** If the current phase references Figma nodes and
Figma MCP tools are available, use them for visual verification before and after implementing
UI tasks. Follow the detailed procedure in **`references/figma-verification.md`**.
If Figma MCP tools are not available, skip this step.

5. **Run tests.** After completing all actions of the current phase, run `{paths.run_tests}` (from settings.json) to verify tests pass.
   - If tests **pass**: proceed to step 5a.
   - If tests **fail**: **STOP** and fix the issues before continuing.

   When tests fail:
   1. Analyze the failure: read the test output to understand what broke.
   2. Fix the issue: modify the code to make tests pass.
   3. Re-run tests: execute `{paths.run_tests}` again.
   4. Repeat until all tests pass. Only then proceed to step 5a.

5a. **E2E browser verification (optional — Playwright CLI).** Only run this step if **all three**
conditions are met:

1.  `.sdd.json` contains a `playwright` config section
2.  `playwright-cli` is available (installed via `@playwright/cli`)
3.  The current phase has action items that affect **UI, routes, or visible components**
    (e.g., pages, layouts, forms, navigation). Skip silently for phases that only touch
    backend logic, tests, refactoring, config, or documentation.

- If verification **fails**: fix the code **and** update the tests, then re-run step 5 before continuing.
- If any condition above is not met: skip silently.

6. **Update the plan file.** After tests pass:
   - Check the checkboxes (`- [x]`) of the completed actions in the current phase.
   - Update the **Next Step** section to point to the next phase to be completed.

7. **Check if all phases are complete.** If there are remaining phases, inform the user that the current phase is done
   and which phase is next. Wait for the user to continue.

8. **When all phases are complete**, perform the following finalization steps:

   a. **Generate the resume.** Load the `template.md` file in the current folder and fill it with the information
   from the plan execution. Save it as `resume.md` in the **same `{paths.specs}` folder** as the plan.

   b. **Update the plan file.** Run `~/.sdd/scripts/sdd-update-status.sh {plan_path} "Status" "Done"`. Update the
   **Next Step** section to: "All phases completed. See resume.md for the summary."

   c. **Update the source story.** Read the story file linked in the plan's "Based on story" field and run:
   - `~/.sdd/scripts/sdd-update-status.sh {story_path} "Status" "Done"`
   - `~/.sdd/scripts/sdd-update-status.sh {story_path} "Plan implemented" "@{plan_path}"`

# Important Notes

- **One phase at a time.** NEVER implement actions from a future phase. Complete current phase → tests → update plan → then proceed.
- **Tests are mandatory gates.** Do NOT mark a phase as complete if tests fail. Fix first, re-run, then mark.
- **Resume goes in the same folder as the plan.** Never create a new directory for the resume.
- **Do NOT modify the plan's contracts or phases** during implementation. If something needs to change,
  inform the user and let them decide.

# Language

Write in the **same language the user used**. If the user wrote in Spanish, write the resume in Spanish.
If they wrote in English, write in English. Template field names (Status, Created at, etc.) stay in English.

# Additional Resources

### Reference Files

- **`references/figma-verification.md`** — Detailed procedure for Figma visual verification during UI implementation
- **`references/playwright-verification.md`** — Detailed procedure for E2E browser verification using Playwright CLI

### Examples

- **`examples/example-resume.md`** — Resume for a 3-phase implementation
- **`examples/example-resume-large.md`** — Resume for a 4-phase implementation with integrations
