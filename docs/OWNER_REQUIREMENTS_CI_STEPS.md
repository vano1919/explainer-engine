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

## If a step does not match
- If **Settings > Branches** says branch protection needs a paid plan for a private repository, tell Claude; there is then no GitHub-side
  lock on this plan, and the other three layers (hooks, `require_layers`, the send gate) stay the machine enforcement. Do not upgrade
  anything because of this file alone.
- If you prefer **Rules > Rulesets > New ruleset > New branch ruleset**: target the same branches and add the rule **Require status checks to
  pass** with `owner-requirements`; tick no bypass list.
