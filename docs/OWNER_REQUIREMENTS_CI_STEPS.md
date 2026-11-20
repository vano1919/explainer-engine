# Owner steps: make the `owner-requirements` check mandatory on GitHub

For the owner, in Georgian (the names of the buttons stay in English, exactly as GitHub shows them). Why: the workflow
`.github/workflows/owner-requirements.yml` runs the job `owner-requirements` on every pull request. It fails if the registry of your
requirements is missing, has an entry without a check, lost an entry or changed your words, or if a test it names fails. GitHub
stops a merge only if you mark the job as **required**; that is a setting in your account, which Claude cannot and must not change. Spec:
[LAYER_GATE.md](LAYER_GATE.md), section "The owner's requirements registry".

## Before the first click
1. Open a pull request of this repository once (any draft) so the job runs once. GitHub lists a check in the search box below only after
   it has run in the last 7 days.
2. You need the **Owner** rights of the repository `vano1919/explainer-engine`.

## The clicks (classic branch protection)
1. Open `https://github.com/vano1919/explainer-engine` and click **Settings** (the gear tab at the top right of the repository).
2. In the left menu click **Branches** (under "Code and automation").
3. Click **Add branch protection rule** (green button; if GitHub shows **Add classic branch protection rule**, click that).
4. In the field **Branch name pattern** type `main` and press Enter.
5. Tick **Require a pull request before merging**.
6. Tick **Require status checks to pass before merging**. Under it appears **Require branches to be up to date before merging**: tick it too.
7. In the search box that appears under "Status checks that are required." type `owner-requirements`. Click the entry `owner-requirements`
   when it appears (if nothing appears: the job has not run in the last 7 days, do the step "Before the first click" again and wait one minute).
8. Scroll down and tick **Do not allow bypassing the above settings** (without it the repository owner can still merge past a red check).
9. Click **Create** at the bottom (it may ask for your password).
10. Repeat steps 3 to 9 for the integration branch the team merges into: in step 4 type `claude/skills-rebuild-2026-11-20`
    (and any other base branch Claude names to you at that time).

## What you should see afterwards
- On a pull request, the box "Merging is blocked" lists `owner-requirements` as **Required**. A red `owner-requirements` means: do not merge.
- To check the setting: **Settings > Branches**; both rules are listed and each says `owner-requirements` under "Require status checks".

## What applies to this repository (checked 2026-11-20 via the GitHub search API)
`vano1919/explainer-engine` is a **public** repository on a personal account (`visibility: public`). On GitHub Free, public repositories
have branch protection and required status checks, so steps 1 to 10 work as written and need no paid plan. If the repository is ever made
private, GitHub Free no longer offers required status checks: the paid-plan alternative is below, and until then the other three layers
(hooks, `require_layers`, the send gate) are the machine enforcement and the red `owner-requirements` check is only advice.

## If a step does not match
- If **Settings > Branches** says branch protection needs a paid plan for a private repository, tell Claude; there is then no GitHub-side
  lock on this plan, and the other three layers (hooks, `require_layers`, the send gate) stay the machine enforcement. Do not upgrade
  anything because of this file alone.
- If you prefer **Rules > Rulesets > New ruleset > New branch ruleset**: target the same branches and add the rule **Require status checks to
  pass** with `owner-requirements`; tick no bypass list.

## Added by the tester (2026-11-20, STEP 1 and 2; evidence in `ENFORCEMENT_METHODS_2026-11-20.md` on HF)

What the tests showed about how a thread gets round a rule, and which of those holes only GitHub can close. Items marked **UNVERIFIED** I could
not check from the cloud container (it cannot read or change repository settings).

### Extra clicks for the same rule on `main` and on `claude/skills-rebuild-2026-11-20` (classic branch protection, same screen as steps 3 to 9)
1. Under **Require status checks to pass before merging** add a second required check, `quality` (the older workflow `quality.yml`: tests, docs lint,
   palette). Today only `owner-requirements` is named; `quality` can be red and the merge still goes.
2. Leave **Allow force pushes** and **Allow deletions** unticked (they are off by default). A force push is how a thread rewrites a branch past the check.
3. Keep **Do not allow bypassing the above settings** ticked (step 8). Without it the repository owner's own token walks past a red check, and
   every thread pushes with that token (below).
4. Do not set a path filter or a "skip if" condition on the workflow: GitHub counts a skipped required check as passed. The tests
   `test_the_workflow_has_no_way_to_skip_or_swallow_the_check` keep the file honest.
5. After clicking, test it once: open a draft pull request that deletes one line of `explainer_engine/governance/owner_requirements.json` (any entry's
   `words`). `owner-requirements` must turn red and **Merge** must be greyed. If Merge is clickable, step 8 or the check name is wrong.

### What GitHub cannot do on this plan (say it to the owner as it is)
- **Threads push as the owner.** A pull request created from a thread shows the owner as author, and asking the owner for a review of it fails with
  "Review cannot be requested from pull request author". GitHub therefore cannot tell a thread's merge or push from the owner's, and a
  "required review by the owner" rule cannot separate them either. What stops a red merge is only the required check plus no bypass. The only fix is a
  second GitHub identity for threads (a machine user or the Claude GitHub App with its own token); whether this platform lets threads use one is **UNVERIFIED**.
- **Restrict file paths** (the rule that would stop any commit touching `.claude/settings.json`, `explainer_engine/governance/**`, `docs/layers/**`,
  `config/spend_caps.json`, `.github/workflows/**`) belongs to GitHub's *push rulesets*, and the GitHub documentation I read says push
  rulesets are for private or internal repositories. This repository is public, so assume **it is not offered here**; do not buy a plan for it. UNVERIFIED on the live Settings screen.
  The replacement is a step inside the `owner-requirements` job that fails when the diff touches those paths and no owner word (a `jobs/creator_ok.jsonl` line with a `cmsg_` id and a quote) is added in the same
  diff. That makes the change visible to the owner in the pull request; it does not prove the word is his (the file is written by the same hands, see `test_W1`, `test_W2`).
- **Managed settings** (the one Claude Code settings tier a project file cannot switch off, `disableAllHooks`): whether the owner's Claude plan offers it is **UNKNOWN**; nothing here assumes it.
  Until it exists, `.claude/settings.json` is protected only by being listed in the paths above (CI step) and by review.
