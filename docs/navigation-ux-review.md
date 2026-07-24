# Navigation UI/UX Review — teams.gotta.bike (web app)

**Scope:** Navigation and wayfinding across the organization/team and membership pages of the Django web app.
**Trigger:** From `/membership/{slug}/members/` there was no discoverable way back to the team page.
**Method:** Per-page-group analysis + navigation-architecture + web-UX-heuristics passes (7 parallel reviews, 41 raw findings, consolidated below).

---

## TL;DR — the root cause

Every team lives at `/{slug}/` (the hub), but its sub-pages live under a **different** URL prefix (`/membership/{slug}/…`) and share **no org-context chrome**. `organizations/base.html` just extends the global navbar and adds nothing, so each sub-page invents its own back link — usually **buried at the bottom** or **absent**. There are no breadcrumbs anywhere.

**One fix repairs most of this:** a shared **org-context header + breadcrumb**, rendered once by `organizations/base.html` (or a `_breadcrumbs.html` partial), so *every* team page gets a consistent top-of-page "you are in {Team} › {Section}" trail with a one-tap path back to the hub.

There is also **one genuine bug** (500 errors) mixed in — fix that first regardless of the nav work.

**Priority legend:** 🔴 P0 blocker/broken · 🟠 P1 high · 🟡 P2 medium · ⚪ P3 polish · Effort: S/M/L

---

## 🔴 P0 — Broken or hard dead-ends (do first)

- [ ] **Fix 500s on "View Details" and "Change Role"** — `S`
      `MemberDetailView` (views.py:108) and `MembershipRoleUpdateView` (views.py:363) declare `membership/member_detail.html` and `membership/role_update.html`, **which don't exist**. The member-list dropdown links straight to both (member_list.html:149,151), so both actions raise `TemplateDoesNotExist` → 500 for every member. **Create the two missing templates** (or repoint the links at `member_roles`/`member_detail` surfaces that do exist).
- [ ] **Add a top-of-page back/up affordance to _every_ org sub-page** — `M`
      The reported dead-end: no way back to the team without the browser back button or the logo→home. Establish a single always-visible top-of-page "← {Team}" (see the systemic fix in P1).
- [ ] **Give the Manage cluster a back path** — `M`
      `organization_manage.html` (the hub's "Manage" gear target) and its tab partials (`_membership_tab`, `_seasons_tab`, `_profile_tab`) have **no breadcrumb and no back-to-hub link** — the main admin surface is itself a dead-end. Fixing the container covers all three tabs at once.

## 🟠 P1 — The systemic fix + consistency (highest leverage)

- [ ] **Add a shared org-context header + breadcrumb in `organizations/base.html`** — `M` *(the single highest-leverage change)*
      Render "Leagues › {League} › {Team} › {Section}" (last crumb = current page) at the top of the org content block. Because nearly every org/membership template extends this base, one change gives all of them a consistent location signpost and a one-tap route back to the team hub.
- [ ] **Extract one reusable `_breadcrumbs.html` partial** — `S`
      The two detail hubs (`team_detail.html:8-17`, `organization_detail.html:8-19`) hand-duplicate the trail. Extract it once and reuse it everywhere (base header + any page that needs a custom trail).
- [ ] **Move member_list's "Back to team" from the bottom to the top** — `S`
      Today the only up-link is `← Back to {org}` at member_list.html:199 (of 204), below the whole roster. Put a back/breadcrumb above the header. *(Subsumed once the base-header fix lands.)*
- [ ] **Standardize where "back" points** — `M`
      Peer sub-pages currently send "back" to three different destinations. Define one rule: sub-page → team hub (`object.get_absolute_url`), consistently.
- [ ] **Add breadcrumbs to all membership sub-pages** — `M`
      `member_list`, `role_management`, `request_list`, `invite`, `invite_link_list`/`create`, `season_detail`, `sub_org_member_management` — none have breadcrumbs.

## 🟡 P2 — Discoverability, global nav, mobile, a11y

**Hub ↔ sub-page linking**
- [ ] **Link the hub's "Members" card to the full roster** — `S` — `team_detail.html:149-211` lists members inline with no link to the filterable `membership:member_list` page; the richest member surface is unreachable from the hub.
- [ ] **De-duplicate the two member tables** — `M` — `_membership_tab.html` renders a read-only member table with no row actions, while `member_list.html` has view/role/remove. Pick one canonical surface; point the other at it.
- [ ] **Give `invite_accept` a decline/back exit** — `S` — invited users have no way out except accept.
- [ ] **Guest "already a member" state → link to member view** — `S`.

**Global navigation**
- [ ] **Let the global navbar return to the current team, not just Home** — `M` — deep in a team, the only global affordance is logo→home; add a breadcrumb slot in `base.html`.
- [ ] **Bridge the `/membership/{slug}/…` vs `/{slug}/` URL split** — `M` — the split makes sub-pages feel "outside" the team; the shared header hides this seam.

**Per-page back affordances (each currently bottom-only or absent)** — `S` each
- [ ] `season_list`, [ ] `season_form`, [ ] `invite`, [ ] `invite_link_list`, [ ] `invite_link_create`, [ ] `request_list`, [ ] `role_management`, [ ] `organization_edit` (Cancel buried at bottom of a long form).

**Bug in the existing breadcrumbs**
- [ ] **Guard breadcrumbs for standalone teams** — `S` — `team_detail.html:13-15`/`organization_detail.html:11-13` assume a league ancestor; for standalone teams `league` is `None`, producing an empty crumb and a live `<a href="">` that reloads the page. Wrap in `{% if league %}`.

**Mobile & accessibility**
- [ ] **Mobile nav** — `S` — top-anchor the back control; let header action rows wrap; add `flex-wrap` to the breadcrumb `<ol>` (the 4-level trail overflows on narrow phones).
- [ ] **A11y** — `S` — breadcrumbs as `<nav aria-label="Breadcrumb">` with `aria-current="page"`; label the user-menu toggle.

## ⚪ P3 — Polish

- [ ] Make the org name in list/form headers a link to the team hub — `S`.
- [ ] `league_guest`: add a top "← Browse" affordance and a location heading — `S`.
- [ ] Browse page: add an on-page `<h1>` to anchor location — `S`.

---

## Recommended order

1. **P0 bug** — create `member_detail.html` + `role_update.html` (stops live 500s).
2. **Systemic header** — `_breadcrumbs.html` partial + render it in `organizations/base.html`. This single change resolves the reported dead-end and most P1/P2 "no back" items across every page simultaneously.
3. **Standardize back target** to the team hub; drop the now-redundant buried bottom links.
4. Work down P2 (hub linking, global navbar, mobile/a11y), then P3 polish.

Doing #2 first would fix your reported issue on the members page **and** every other sub-page in one pass — so if you only do one thing, do that.
