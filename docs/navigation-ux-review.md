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

- [x] **Fix 500s on "View Details" and "Change Role"** — `S`
      `MemberDetailView` (views.py:108) and `MembershipRoleUpdateView` (views.py:363) declare `membership/member_detail.html` and `membership/role_update.html`, **which don't exist**. The member-list dropdown links straight to both (member_list.html:149,151), so both actions raise `TemplateDoesNotExist` → 500 for every member. **Create the two missing templates** (or repoint the links at `member_roles`/`member_detail` surfaces that do exist).
- [x] **Add a top-of-page back/up affordance to _every_ org sub-page** — `M`
      The reported dead-end: no way back to the team without the browser back button or the logo→home. Establish a single always-visible top-of-page "← {Team}" (see the systemic fix in P1).
- [x] **Give the Manage cluster a back path** — `M`
      `organization_manage.html` (the hub's "Manage" gear target) and its tab partials (`_membership_tab`, `_seasons_tab`, `_profile_tab`) have **no breadcrumb and no back-to-hub link** — the main admin surface is itself a dead-end. Fixing the container covers all three tabs at once.

## 🟠 P1 — The systemic fix + consistency (highest leverage)

- [x] **Add a shared org-context header + breadcrumb in `organizations/base.html`** — `M` *(the single highest-leverage change)*
      Render "Leagues › {League} › {Team} › {Section}" (last crumb = current page) at the top of the org content block. Because nearly every org/membership template extends this base, one change gives all of them a consistent location signpost and a one-tap route back to the team hub.
- [x] **Extract one reusable `_breadcrumbs.html` partial** — `S`
      The two detail hubs (`team_detail.html:8-17`, `organization_detail.html:8-19`) hand-duplicate the trail. Extract it once and reuse it everywhere (base header + any page that needs a custom trail).
- [x] **Move member_list's "Back to team" from the bottom to the top** — `S`
      Today the only up-link is `← Back to {org}` at member_list.html:199 (of 204), below the whole roster. Put a back/breadcrumb above the header. *(Subsumed once the base-header fix lands.)*
- [ ] **Standardize where "back" points** — `M`
      Peer sub-pages currently send "back" to three different destinations. Define one rule: sub-page → team hub (`object.get_absolute_url`), consistently.
- [x] **Add breadcrumbs to all membership sub-pages** — `M`
      `member_list`, `role_management`, `request_list`, `invite`, `invite_link_list`/`create`, `sub_org_member_management` — none had breadcrumbs. *(`season_detail` excluded — unreachable, see Round 2.)*

## 🟡 P2 — Discoverability, global nav, mobile, a11y

**Hub ↔ sub-page linking**
- [x] **Link the hub's "Members" card to the full roster** — `S` — `team_detail.html:149-211` lists members inline with no link to the filterable `membership:member_list` page; the richest member surface is unreachable from the hub.
- [x] **De-duplicate the two member tables** — `M` — see Round 3; this one uncovered a live permissions bug.
- [x] **Give `invite_accept` a decline/back exit** — `S` — invited users have no way out except accept.
- [x] **Guest "already a member" state → link to member view** — `S` — done on both `team_guest` and `league_guest`.

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

## Round 2 — findings from rendering every page

The first pass was static template reading. A second pass **actually rendered all 28 org/membership
pages** through the real views (test client, seeded league → team → squad → season, transaction
rolled back). That caught four things static review missed.

### 🔴 Fixed — `Remove Member` returned a 500

`MembershipRemoveView` declared `membership/member_remove_confirm.html`, which didn't exist.
Reachable from **two** live links — `member_list.html:152` ("Remove Member" in the row dropdown) and
`member_detail.html:72`. This is the *same dropdown* whose other two actions were the original P0;
that fix caught 2 of 3.

- [x] Created `membership/member_remove_confirm.html`.

### 🔴 Fixed — the last-owner guard was dead code

More serious than the 500 that was hiding it. `MembershipRemoveView` put its *"cannot remove the only
owner"* check in `delete()`. In Django 6.0, `BaseDeleteView.post()` sits ahead of
`DeletionMixin.post()` in the MRO and routes POST straight to `form_valid()` — **`delete()` is never
called.** Simply adding the missing template would have shipped a live path to remove an
organization's only owner, orphaning it with nobody able to manage it.

- [x] Moved the guard to `form_valid()`.
- [x] Added `is_last_owner` to the context so the confirm page warns and hides the submit button,
      rather than only failing after the click.
- [x] Verified by POST: sole owner **blocked**, ordinary member **removed**, owner-with-co-owner
      **removed**, and the GET page shows the warning with no submit button.
- Audited the other four `DeleteView` subclasses — none share the pattern.

### 🔴 Fixed — `/{slug}/settings/` returned a 500

`OrganizationSettingsView` declared `organizations/organization_settings.html`, which never existed —
so the route had never worked. Linked from nowhere, and fully superseded by `OrganizationManageView`
(membership / seasons / profile tabs). It was also a *third* member-table surface, which cuts against
the P2 de-duplication item.

- [x] Removed the view and its route rather than reviving a duplicate of Manage.

### 🟠 Fixed — the shared breadcrumb silently skipped 4 pages

`_breadcrumbs.html` renders only when `organization` is in context. Views that set an explicit
`context_object_name` (`league`, `team`) don't provide it, so the breadcrumb rendered *nothing* — no
error, just a silently missing trail. The **league hub** and all three guest views were affected.

- [x] Added the `organization` alias to `LeagueMemberView`, `LeagueGuestView`, `TeamGuestView`.
- [x] Retired `team_guest.html`'s hand-rolled league-only nav (it would now be a duplicate, and it
      was wrapped in `{% if league %}` so standalone teams got nothing at all).
- Re-ran the audit: **all 25 org-context pages now render exactly one breadcrumb.** The three
  without one — `/browse/`, `/create/`, `/create/squad/` — have no org to anchor to. Correct as-is.

### 📋 Not a bug — season registration is unimplemented

Worth a decision, not a fix. `SeasonDetailView` exists but **has no URL route**, so
`membership/season_detail.html` is unreachable and `_season_card.html` is included nowhere.

This can't be fixed by adding a route: both templates link to `membership:season_register` and
`membership:join_and_register_season`, and **neither has a view or a URL**. The season *registration*
UI was written ahead of its backend.

Today `season_list.html` is admin-only (Edit / Delete). It shows a registered-count but there is no
way to see who registered, and **members cannot register for a season at all**. Either build the
registration backend or remove the three templates — but it's a feature call, not cleanup.

---

## Round 3 — de-duplicating the member tables uncovered a permissions bug

The P2 de-dup item required reading both member tables closely. That read found
`member_list.html` gating **every** admin control on `user_membership.role` — but `Membership` has
no `role` field. Authorization lives on `permission_level`; roles are descriptive and live on
`MemberRole`.

Django's `{% if %}` resolves the missing attribute to `None`, and its `in` operator swallows the
resulting error and returns `False`. So the gate was **always false for everyone, owners included**:

| Broken by `.role` | Effect |
|---|---|
| `{% if user_membership.role in 'OrgOwner,OrgAdmin,OrgManager' %}` | Invite Member, Pending Requests, the whole **Actions column**, View Details, Change Role, Remove Member — invisible to *every* user including owners |
| `{{ membership.get_role_display }}` | Role badge column rendered **blank** for every member |
| Filter form `name="role"` with `OrgOwner`-style values | Submitted `?role=OrgOwner`, which the view never reads (it reads `permission_level`) — **the filter did nothing** |

This reframes the earlier P0 work: the dropdown whose three actions were 500ing had itself never
rendered. The 500s were real (the URLs are directly reachable, and `member_detail.html` links to
`member_remove`), but the dropdown was invisible the whole time.

- [x] Replaced the string-matching gates with `can_manage` / `can_admin` booleans computed in the
      view from `permission_level`, matching the permission matrix in CLAUDE.md
      (manage members → owner/admin/manager; assign permissions → owner/admin).
- [x] Fixed the Permission column to use `get_permission_level_display`.
- [x] Rebuilt the filter form against what the view actually reads, and added server-side role
      filtering and name/email search to close the gap with the tab's client-side version.
- [x] Pagination now preserves every filter via `{% querystring %}` (it previously dropped all but
      two params).

**Canonical surface: `member_list.html`.** It is member-accessible (the Manage tab is admin-only),
paginated, and has row actions. It absorbed the tab's Email and Roles columns so nothing was lost.

- [x] `_membership_tab.html` keeps what is genuinely admin-only — membership requirements, stats,
      quick actions, CSV export — and its duplicated table, duplicated filters, and 40-line
      client-side filter script were replaced by a link to the roster.

Verified by rendering: 24 checks covering owner-vs-member visibility, all four filters, the invite
exit across all three branches, and the absence of the duplicate table.

---

## Recommended order

1. **P0 bug** — create `member_detail.html` + `role_update.html` (stops live 500s).
2. **Systemic header** — `_breadcrumbs.html` partial + render it in `organizations/base.html`. This single change resolves the reported dead-end and most P1/P2 "no back" items across every page simultaneously.
3. **Standardize back target** to the team hub; drop the now-redundant buried bottom links.
4. Work down P2 (hub linking, global navbar, mobile/a11y), then P3 polish.

Doing #2 first would fix your reported issue on the members page **and** every other sub-page in one pass — so if you only do one thing, do that.
