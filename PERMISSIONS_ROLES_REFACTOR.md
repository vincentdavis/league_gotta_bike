# Permissions vs Roles Refactor - Implementation Status

## Overview

Successfully refactored the membership system to separate **permission levels** (authorization) from **organizational roles** (identity/function).

**Date**: 2025-10-12
**Status**: ✅ Core Implementation Complete | ⏳ Forms/Views/Templates Need Updates

---

## ✅ Completed Changes

### 1. CLAUDE.md Documentation
- ✅ Added comprehensive "Permissions vs Roles Architecture" section
- ✅ Detailed permission matrix for all permission levels
- ✅ Listed all available organizational roles
- ✅ Provided usage examples and scenarios
- ✅ Best practices guide

**Location**: `CLAUDE.md` lines 180-291

### 2. Membership Model Refactor
- ✅ Added `permission_level` field with choices: owner, admin, manager, member
- ✅ Created `MemberRole` model for organizational roles (athlete, coach, parent, etc.)
- ✅ Added helper methods: `get_roles()`, `get_primary_role()`, `has_role()`, `get_roles_display()`
- ✅ Kept old `role` field temporarily for backwards compatibility
- ✅ Full documentation in model docstrings

**Location**: `apps/membership/models.py`

**New Structure**:
```python
class Membership:
    permission_level = CharField(choices=[owner, admin, manager, member])  # NEW
    role = CharField(...)  # DEPRECATED - will be removed
    # ... relationships to MemberRole model via member_roles

class MemberRole:
    membership = ForeignKey(Membership)
    role_type = CharField(choices=[athlete, coach, parent, guardian, ...])
    is_primary = BooleanField()
    notes = TextField()
```

### 3. Database Migrations
- ✅ Migration 0002: Added `permission_level` field and `MemberRole` model
- ✅ Migration 0003: Data migration to convert old `role` → new `permission_level` + `MemberRole`

**Data Migration Mapping**:
- `OrgOwner` → `owner` permission_level
- `OrgAdmin` → `admin` permission_level
- `OrgManager` → `manager` permission_level
- `OrgCoach` → `manager` permission_level + `MemberRole(coach)`
- `OrgMember` → `member` permission_level
- `OrgParent` → `member` permission_level + `MemberRole(parent)`

**Location**: `apps/membership/migrations/`

### 4. Permission Checks Updated
- ✅ Updated `is_org_owner()` to use `permission_level == OWNER`
- ✅ Updated `is_org_admin()` to use `permission_level in [OWNER, ADMIN]`
- ✅ Updated `can_manage_members()` to use `permission_level in [OWNER, ADMIN, MANAGER]`

**Location**: `apps/organizations/permissions.py`

---

## ⏳ Remaining Work

### 1. Update Membership Forms (apps/membership/forms.py)

**Files to Update**:
- `MembershipInviteForm` - Change `role` field to `permission_level` + add optional roles multiselect
- `MembershipRoleUpdateForm` - Rename to `MembershipPermissionUpdateForm` or create separate form for roles
- Need NEW form: `MemberRoleForm` for assigning organizational roles

**Example Changes Needed**:
```python
# OLD
role = forms.ChoiceField(
    choices=[
        (Membership.ORG_MEMBER, 'Member'),
        (Membership.ORG_COACH, 'Coach'),
        # ...
    ]
)

# NEW
permission_level = forms.ChoiceField(
    choices=Membership.PERMISSION_LEVEL_CHOICES,
    label='Permission Level'
)

# NEW: Separate form for roles
roles = forms.MultipleChoiceField(
    choices=MemberRole.ROLE_TYPE_CHOICES,
    widget=forms.CheckboxSelectMultiple,
    required=False,
    label='Organizational Roles'
)
```

### 2. Update Membership Views (apps/membership/views.py)

**Changes Needed**:
- Update all views that reference `membership.role` to use `membership.permission_level`
- Update views to handle multiple `MemberRole` entries
- Update role change views to handle permission_level separately from roles

**Specific Views to Update**:
- `MembershipInviteView` - Create membership with permission_level + roles
- `MembershipRoleUpdateView` - Split into two views or handle both
- `MembershipRequestDecisionView` - Assign permission_level + default role

**Example Pattern**:
```python
# OLD
membership = Membership.objects.create(
    user=user,
    organization=organization,
    role=Membership.ORG_MEMBER  # OLD
)

# NEW
membership = Membership.objects.create(
    user=user,
    organization=organization,
    permission_level=Membership.MEMBER  # NEW
)

# Add roles separately
MemberRole.objects.create(
    membership=membership,
    role_type=MemberRole.ATHLETE,
    is_primary=True
)
```

### 3. Update Organization Views (apps/organizations/views.py)

**Changes Needed**:
- Update views that create memberships to use `permission_level=OWNER` instead of `role=ORG_OWNER`
- Update context data that passes role information to templates

**Specific Views**:
- `LeagueCreateView.form_valid()` - Use `permission_level=OWNER`
- `TeamCreateView.form_valid()` - Use `permission_level=OWNER`
- `SquadCreateView.form_valid()` - Use `permission_level=OWNER`
- `ClubCreateView.form_valid()` - Use `permission_level=OWNER`

### 4. Update Templates

**Templates to Update**:
- `member_list.html` - Display permission_level badge + roles list
- `member_detail.html` - Show permission level + all roles with badges
- `request_decision.html` - Separate permission level from role selection
- `invite.html` - Update form to show permission level + role checkboxes
- `role_update.html` - Consider renaming to `permission_update.html` or split functionality

**Example Template Changes**:
```django
{# OLD #}
<span class="badge">{{ membership.get_role_display }}</span>

{# NEW #}
<div class="flex gap-2">
    <span class="badge badge-primary">{{ membership.get_permission_level_display }}</span>
    {% for role in membership.get_roles %}
        <span class="badge badge-ghost">{{ role.get_role_type_display }}</span>
    {% endfor %}
</div>
```

### 5. Update Admin Interface (apps/membership/admin.py)

**Changes Needed**:
- Add `MemberRoleInline` to `MembershipAdmin`
- Update list_display to show `permission_level` instead of `role`
- Add filter for `permission_level`
- Consider adding `MemberRoleAdmin` for standalone role management

**Example**:
```python
class MemberRoleInline(admin.TabularInline):
    model = MemberRole
    extra = 1

@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ['user', 'organization', 'permission_level', 'get_roles_display', 'status']
    list_filter = ['permission_level', 'status']
    inlines = [MemberRoleInline]
```

### 6. Test and Verify

**Testing Checklist**:
- [ ] Run migrations: `python manage.py migrate`
- [ ] Verify data migration worked correctly
- [ ] Test permission checks work with new permission_level
- [ ] Test creating new memberships with permission_level
- [ ] Test adding multiple roles to a membership
- [ ] Test UI displays permission level + roles correctly
- [ ] Test filtering/searching by permission level
- [ ] Test filtering/searching by role
- [ ] Verify backwards compatibility during transition

### 7. Cleanup (Final Step)

**After Everything Works**:
- [ ] Remove old `role` field from Membership model
- [ ] Remove old `role` references from forms
- [ ] Remove DEPRECATED constants (ORG_OWNER, ORG_ADMIN, etc.)
- [ ] Create final migration to drop `role` column
- [ ] Update any remaining documentation

---

## Migration Strategy

### Phase 1: Add New Fields (✅ COMPLETE)
- Add `permission_level` field
- Create `MemberRole` model
- Keep old `role` field

### Phase 2: Data Migration (✅ COMPLETE)
- Convert existing `role` data to `permission_level`
- Create `MemberRole` entries for coaches and parents

### Phase 3: Update Code (⏳ IN PROGRESS)
- Update permission checks (✅ DONE)
- Update forms (⏳ TODO)
- Update views (⏳ TODO)
- Update templates (⏳ TODO)
- Update admin (⏳ TODO)

### Phase 4: Test & Verify (⏳ PENDING)
- Test all functionality
- Verify UI looks correct
- Check permission enforcement

### Phase 5: Cleanup (⏳ PENDING)
- Remove old `role` field
- Final migration

---

## Permission Matrix Reference

| Action | Owner | Admin | Manager | Member |
|--------|:-----:|:-----:|:-------:|:------:|
| View organization | ✅ | ✅ | ✅ | ✅ |
| Edit organization | ✅ | ✅ | ❌ | ❌ |
| Delete organization | ✅ | ❌ | ❌ | ❌ |
| Manage members | ✅ | ✅ | ✅ | ❌ |
| Assign permissions | ✅ | ✅ | ❌ | ❌ |
| Create/edit events | ✅ | ✅ | ✅ | ❌ |
| View finances | ✅ | ✅ | ✅ | ❌ |
| Manage finances | ✅ | ✅ | ❌ | ❌ |

---

## Organizational Roles Reference

Available role types (descriptive only, no permissions):
- **Athlete/Cyclist** - Active participant
- **Coach** - Provides training and guidance
- **Parent** - Parent of a youth athlete
- **Guardian** - Legal guardian of an athlete
- **Team Captain** - Leadership among athletes
- **Medical Staff** - Medical support
- **Mechanic** - Bike maintenance
- **Volunteer** - General volunteer
- **Official** - Race/event official
- **Spectator** - Observer/supporter

---

## Example Usage

### Creating a Member with Roles
```python
# Create membership with permission level
membership = Membership.objects.create(
    user=user,
    organization=team,
    permission_level=Membership.MANAGER,  # Can manage members and events
    status=Membership.ACTIVE
)

# Add multiple organizational roles
MemberRole.objects.create(
    membership=membership,
    role_type=MemberRole.COACH,
    is_primary=True
)
MemberRole.objects.create(
    membership=membership,
    role_type=MemberRole.PARENT
)

# Display
print(f"Permission: {membership.get_permission_level_display()}")
# Output: "Permission: Manager"

print(f"Roles: {membership.get_roles_display()}")
# Output: "Roles: Coach, Parent"
```

### Checking Permissions
```python
# Check if user can edit organization
if is_org_admin(user, organization):
    # User has owner or admin permission level
    pass

# Check if user has a specific role
if membership.has_role(MemberRole.COACH):
    # Display coach-specific features
    pass
```

---

## Benefits of This Refactor

✅ **Clear Separation**: Permission vs Role is no longer confusing
✅ **Multiple Roles**: Users can be Coach AND Parent simultaneously
✅ **Flexible Permissions**: Easy to adjust what each permission level can do
✅ **Better UX**: Clear display of "what you can do" vs "what you are"
✅ **Extensible**: Add new roles without changing permission logic
✅ **Backwards Compatible**: Migration preserves existing data
✅ **Well Documented**: Comprehensive docs in CLAUDE.md

---

## Next Steps

1. **Update Forms** - Change role field to permission_level, add roles multiselect
2. **Update Views** - Use permission_level when creating memberships
3. **Update Templates** - Display permission level + roles separately
4. **Test Thoroughly** - Verify all functionality works
5. **Cleanup** - Remove old role field after verification

---

## Files Changed

### Models
- ✅ `apps/membership/models.py` - Added permission_level, created MemberRole

### Migrations
- ✅ `apps/membership/migrations/0002_add_permission_level_and_member_roles.py`
- ✅ `apps/membership/migrations/0003_migrate_role_data_to_permission_level.py`

### Permissions
- ✅ `apps/organizations/permissions.py` - Updated to use permission_level

### Documentation
- ✅ `CLAUDE.md` - Added Permissions vs Roles section
- ✅ `PERMISSIONS_ROLES_REFACTOR.md` - This document

### To Be Updated
- ⏳ `apps/membership/forms.py`
- ⏳ `apps/membership/views.py`
- ⏳ `apps/membership/admin.py`
- ⏳ `apps/organizations/views.py` (organization creation views)
- ⏳ Templates in `apps/membership/templates/`
- ⏳ Templates in `apps/organizations/templates/`

---

Generated: 2025-10-12
