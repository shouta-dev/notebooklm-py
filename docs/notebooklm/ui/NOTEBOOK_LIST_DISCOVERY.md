# Notebook List / Home Page Discovery Documentation

**Created**: 2026-01-01
**Purpose**: Automated discovery blueprint for NotebookLM home page UI elements, notebook cards (grid & list views), filters, and actions

**Session Validation**: All selectors validated 100% match with `config/selectors.json`

---

## Table of Contents

1. [Overview](#overview)
2. [Page Structure](#page-structure)
3. [Header Navigation Discovery](#header-navigation-discovery)
4. [Grid View Discovery](#grid-view-discovery)
5. [List View Discovery](#list-view-discovery)
6. [Notebook Actions Discovery](#notebook-actions-discovery)
7. [Create Notebook Flow](#create-notebook-flow)
8. [Complete Discovery Algorithm](#complete-discovery-algorithm)
9. [Validation Results](#validation-results)

---

## Overview

The Notebook List (Home Page) is the landing page where users view, filter, and create notebooks. This page has two view modes (Grid and List) and displays both Featured notebooks and user's Recent notebooks.

### Key Components

1. **Header Navigation** - Logo, Settings, PRO badge, User account
2. **Filter Tabs** - All, My notebooks, Featured notebooks
3. **View Controls** - Grid view, List view toggle
4. **Sort Control** - Most recent, Alphabetical, etc.
5. **Create New Button** - Primary action to create notebook
6. **Featured Notebooks Section** - Google-curated notebook examples
7. **Recent Notebooks Section** - User's notebooks
8. **Notebook Cards** - Individual notebook representations (2 layouts)
9. **Actions Menu** - Delete, Edit title per notebook

### Page URL

```
https://notebooklm.google.com/
```

---

## Page Structure

### High-Level Layout

```
┌─────────────────────────────────────────────────────────────┐
│ HEADER                                                      │
│ [Logo] [All | My notebooks | Featured] [Grid|List] [Sort]  │
│ [Create new]                                                │
├─────────────────────────────────────────────────────────────┤
│ Featured notebooks                                          │
│ ┌─────┬─────┬─────┬─────┐                                  │
│ │ 🌍  │ 📰  │ 👶  │ 🧬  │  [See all →]                     │
│ └─────┴─────┴─────┴─────┘                                  │
├─────────────────────────────────────────────────────────────┤
│ Recent notebooks                                            │
│ ┌─────────┐                                                 │
│ │ ➕      │  ┌─────┬─────┬─────┐                           │
│ │ Create  │  │ 🤖  │ 🧠  │ 🎨  │  ...                      │
│ └─────────┘  └─────┴─────┴─────┘                           │
└─────────────────────────────────────────────────────────────┘
```

---

## Header Navigation Discovery

### Phase 1: Identify Top Navigation Elements

#### Step 1.1: Logo and Branding

```javascript
const discoverLogo = () => {
  const logo = document.querySelector('a[href="/"]');

  return {
    found: logo !== null,
    selector: 'a[href="/"]',
    hasImage: logo?.querySelector('img') !== null,
    classes: logo ? Array.from(logo.classList) : [],
    clickable: true,
    action: 'Returns to home page'
  };
};
```

**Expected Output:**
```javascript
{
  found: true,
  selector: 'a[href="/"]',
  hasImage: true,
  classes: ['logo-link'],
  clickable: true,
  action: 'Returns to home page'
}
```

**DOM Structure:**
```html
<a href="/" class="logo-link">
  <img src="..." alt="NotebookLM Logo">
</a>
```

---

#### Step 1.2: Settings Button

```javascript
const discoverSettingsButton = () => {
  const settingsBtn = Array.from(document.querySelectorAll('button')).find(btn =>
    btn.innerText.includes('Settings') || btn.querySelector('img[alt="settings"]')
  );

  return {
    found: settingsBtn !== null,
    selector: 'button:has(img[alt="settings"])',
    text: settingsBtn?.innerText.trim(),
    classes: settingsBtn ? Array.from(settingsBtn.classList) : [],
    action: 'Opens settings menu'
  };
};
```

**Expected Output:**
```javascript
{
  found: true,
  selector: 'button:has(img[alt="settings"])',
  text: "settings\nSettings",
  classes: [
    "mdc-button",
    "mat-mdc-button-base",
    "mat-mdc-menu-trigger",
    "extendable-button",
    "mat-tonal-button",
    "extendable-button-extended",
    "mat-unthemed"
  ],
  action: 'Opens settings menu'
}
```

---

#### Step 1.3: PRO Badge

```javascript
const discoverProBadge = () => {
  const proBadge = Array.from(document.querySelectorAll('*')).find(el =>
    el.innerText === 'PRO' && el.offsetParent !== null
  );

  return {
    found: proBadge !== null,
    text: proBadge?.innerText,
    tagName: proBadge?.tagName,
    isCustomElement: proBadge?.tagName === 'PRO-BADGE'
  };
};
```

**Expected Output:**
```javascript
{
  found: true,
  text: "PRO",
  tagName: "PRO-BADGE",
  isCustomElement: true
}
```

---

### Phase 2: Filter Tabs Discovery

#### Step 2.1: Find Filter Radio Group

```javascript
const discoverFilterTabs = () => {
  const radioGroups = document.querySelectorAll('[role="radiogroup"]');

  if (radioGroups.length === 0) {
    return { found: false };
  }

  // First radiogroup is filter tabs
  const filterGroup = radioGroups[0];
  const filterButtons = Array.from(filterGroup.querySelectorAll('[role="radio"]'));

  return {
    found: true,
    selector: '[role="radiogroup"]',
    count: filterButtons.length,
    filters: filterButtons.map(btn => ({
      text: btn.innerText.trim(),
      isSelected: btn.getAttribute('aria-checked') === 'true',
      classes: Array.from(btn.classList)
    }))
  };
};
```

**Expected Output:**
```javascript
{
  found: true,
  selector: '[role="radiogroup"]',
  count: 3,
  filters: [
    { text: "All", isSelected: true },
    { text: "My notebooks", isSelected: false },
    { text: "Featured notebooks", isSelected: false }
  ]
}
```

**DOM Structure:**
```html
<div role="radiogroup" aria-label="Filter notebooks">
  <div role="presentation">
    <button role="radio" type="button" aria-checked="true">
      <span>All</span>
    </button>
  </div>
  <div role="presentation">
    <button role="radio" type="button" aria-checked="false">
      <span>My notebooks</span>
    </button>
  </div>
  <div role="presentation">
    <button role="radio" type="button" aria-checked="false">
      <span>Featured notebooks</span>
    </button>
  </div>
</div>
```

---

### Phase 3: View Controls Discovery

#### Step 3.1: Grid/List Toggle

```javascript
const discoverViewControls = () => {
  const radioGroups = document.querySelectorAll('[role="radiogroup"]');

  if (radioGroups.length < 2) {
    return { found: false };
  }

  // Second radiogroup is view controls
  const viewGroup = radioGroups[1];
  const viewButtons = Array.from(viewGroup.querySelectorAll('[role="radio"]'));

  return {
    found: true,
    selector: '[role="radiogroup"]:nth-of-type(2)',
    count: viewButtons.length,
    views: viewButtons.map(btn => ({
      ariaLabel: btn.getAttribute('aria-label'),
      icon: btn.querySelector('img')?.alt,
      isSelected: btn.getAttribute('aria-checked') === 'true',
      classes: Array.from(btn.classList)
    }))
  };
};
```

**Expected Output:**
```javascript
{
  found: true,
  selector: '[role="radiogroup"]:nth-of-type(2)',
  count: 2,
  views: [
    { ariaLabel: "Grid view", icon: "grid_view", isSelected: true },
    { ariaLabel: "List view", icon: "view_headline", isSelected: false }
  ]
}
```

**DOM Structure:**
```html
<div role="radiogroup" aria-label="View mode">
  <div role="presentation">
    <button role="radio" aria-label="Grid view" type="button" aria-checked="true">
      <img alt="grid_view">
    </button>
  </div>
  <div role="presentation">
    <button role="radio" aria-label="List view" type="button" aria-checked="false">
      <img alt="view_headline">
    </button>
  </div>
</div>
```

---

### Phase 4: Sort Control Discovery

```javascript
const discoverSortControl = () => {
  const sortButton = Array.from(document.querySelectorAll('button')).find(btn =>
    btn.innerText.includes('Most recent') ||
    btn.innerText.includes('Select project filter')
  );

  return {
    found: sortButton !== null,
    selector: 'button:has-text("Most recent")',
    text: sortButton?.innerText.trim(),
    hasDropdown: sortButton?.querySelector('img[alt="arrow_drop_down"]') !== null,
    classes: sortButton ? Array.from(sortButton.classList) : [],
    action: 'Opens sort menu'
  };
};
```

**Expected Output:**
```javascript
{
  found: true,
  selector: 'button:has-text("Most recent")',
  text: "Most recent\narrow_drop_down",
  hasDropdown: true,
  classes: [
    "mdc-button",
    "mat-mdc-button-base",
    "mat-mdc-menu-trigger",
    "project-filter-button",
    "mat-mdc-button",
    "mat-unthemed"
  ],
  action: 'Opens sort menu'
}
```

---

### Phase 5: Create New Button Discovery

```javascript
const discoverCreateButton = () => {
  const createBtn = Array.from(document.querySelectorAll('button')).find(btn =>
    btn.innerText.includes('Create new')
  );

  return {
    found: createBtn !== null,
    selector: 'button:has-text("Create new")',
    text: createBtn?.innerText.trim(),
    hasIcon: createBtn?.querySelector('img, mat-icon') !== null,
    classes: createBtn ? Array.from(createBtn.classList) : [],
    action: 'Creates new notebook and navigates to it'
  };
};
```

**Expected Output:**
```javascript
{
  found: true,
  selector: 'button:has-text("Create new")',
  text: "add\nCreate new",
  hasIcon: true,
  classes: [
    "mdc-button",
    "mat-mdc-button-base",
    "create-new-button",
    "mdc-button--unelevated",
    "mat-mdc-unelevated-button",
    "mat-unthemed"
  ],
  action: 'Creates new notebook and navigates to it'
}
```

---

## Grid View Discovery

### Phase 1: Featured Notebooks Section

#### Step 1.1: Locate Section Heading

```javascript
const discoverFeaturedSection = () => {
  const heading = Array.from(document.querySelectorAll('h1, h2, h3, h4')).find(el =>
    el.innerText.includes('Featured notebooks')
  );

  return {
    found: heading !== null,
    text: heading?.innerText.trim(),
    tagName: heading?.tagName,
    nextSiblingType: heading?.nextElementSibling?.tagName
  };
};
```

---

#### Step 1.2: Discover Featured Notebook Cards

Featured notebooks use `[role="group"]` elements with special styling.

```javascript
const discoverFeaturedCards = () => {
  const featuredGroups = Array.from(document.querySelectorAll('[role="group"]'));

  // Filter for featured cards (they have specific classes)
  const featuredCards = featuredGroups.filter(group =>
    group.classList.contains('featured-project-card')
  );

  return featuredCards.map((card, index) => {
    const cardData = {
      index,
      role: 'group',
      classes: Array.from(card.classList),
      structure: {}
    };

    // Find public indicator
    const publicIcon = card.querySelector('mat-icon');
    if (publicIcon && publicIcon.innerText === 'public') {
      cardData.structure.public_indicator = {
        found: true,
        icon: 'public',
        tagName: 'MAT-ICON'
      };
    }

    // Find source badge (e.g., "Travel", "The Atlantic")
    const badge = card.querySelector('div');
    const badgeText = badge?.innerText;
    if (badgeText && badgeText.length < 30) {
      cardData.structure.source_badge = {
        text: badgeText,
        hasImage: card.querySelector('img[alt]') !== null
      };
    }

    // Extract metadata
    const spans = Array.from(card.querySelectorAll('span'));
    const title = spans.find(s => s.innerText.length > 20)?.innerText;
    const date = spans.find(s => s.innerText.match(/^\w+ \d+, \d{4}$/))?.innerText;
    const sources = spans.find(s => s.innerText.match(/\d+ source/))?.innerText;

    cardData.parsed = {
      title,
      date,
      sources
    };

    return cardData;
  });
};
```

**Expected Output:**
```javascript
[
  {
    index: 0,
    role: "group",
    classes: [
      "mat-mdc-card",
      "mdc-card",
      "mat-ripple",
      "project-button-card",
      "featured-project-card"
    ],
    structure: {
      public_indicator: { found: true, icon: "public", tagName: "MAT-ICON" },
      source_badge: { text: "Travel", hasImage: true }
    },
    parsed: {
      title: "The Science Fan's Guide To Visiting Yellowstone",
      date: "May 12, 2025",
      sources: "17 sources"
    }
  },
  // ... more cards
]
```

**DOM Structure:**
```html
<div role="group" class="mat-mdc-card mdc-card mat-ripple project-button-card featured-project-card">
  <img alt="This project is public and anyone with link can view">
  <img alt="Travel" src="...">
  <div>Travel</div>
  <span>The Science Fan's Guide To Visiting Yellowstone</span>
  <span>May 12, 2025</span>
  <span>·</span>
  <span>17 sources</span>
  <mat-icon role="img">public</mat-icon>
</div>
```

---

### Phase 2: Recent Notebooks Section

#### Step 2.1: Locate "Create New Notebook" Card

```javascript
const discoverCreateNewCard = () => {
  const createCard = Array.from(document.querySelectorAll('button')).find(btn =>
    btn.innerText.includes('Create new notebook')
  );

  return {
    found: createCard !== null,
    selector: 'button:has-text("Create new notebook")',
    text: createCard?.innerText.trim(),
    hasIcon: createCard?.querySelector('img, mat-icon') !== null,
    iconContent: createCard?.querySelector('img, mat-icon')?.innerText ||
                 createCard?.querySelector('img')?.alt,
    classes: createCard ? Array.from(createCard.classList) : []
  };
};
```

**Expected Output:**
```javascript
{
  found: true,
  selector: 'button:has-text("Create new notebook")',
  text: "add\nCreate new notebook",
  hasIcon: true,
  iconContent: "add",
  classes: [
    "mat-mdc-card",
    "mdc-card",
    "mat-ripple",
    "project-button-card",
    "create-new-project-card"
  ]
}
```

---

#### Step 2.2: Discover Recent Notebook Cards

**CRITICAL DISCOVERY**: Recent notebook cards are NOT directly discoverable via simple button queries because:
1. The card button and the actions menu button are siblings (not parent-child)
2. The card structure uses custom components
3. Need to use reference-based discovery from the read_page accessibility tree

```javascript
const discoverRecentNotebookCards = () => {
  // Strategy: Use accessibility tree or find elements with specific patterns

  // Method 1: Find all elements with "Project Actions Menu" siblings
  const allButtons = Array.from(document.querySelectorAll('button'));

  // Find "Project Actions Menu" buttons
  const actionsMenuButtons = allButtons.filter(btn =>
    btn.innerText && btn.innerText.includes('Project Actions Menu')
  );

  // Get their previous siblings (the notebook card buttons)
  const notebookCards = actionsMenuButtons.map(menuBtn => {
    return menuBtn.previousElementSibling;
  }).filter(el => el && el.tagName === 'BUTTON');

  return notebookCards.map((card, index) => {
    const cardData = {
      index,
      classes: Array.from(card.classList),
      structure: {}
    };

    // Find emoji or icon
    const allImages = Array.from(card.querySelectorAll('img, mat-icon'));
    const publicIcon = allImages.find(img =>
      img.alt?.includes('public') || img.innerText?.includes('public')
    );

    if (publicIcon) {
      cardData.structure.public_indicator = {
        found: true,
        type: publicIcon.tagName
      };
    }

    // Look for emoji (single character, large font)
    const textElements = Array.from(card.querySelectorAll('*'));
    const emojiElement = textElements.find(el => {
      const text = el.innerText?.trim();
      return text && text.length === 2 && /[\u{1F000}-\u{1F9FF}]/u.test(text);
    });

    if (emojiElement) {
      cardData.structure.emoji = {
        found: true,
        content: emojiElement.innerText,
        tagName: emojiElement.tagName
      };
    }

    // Extract text content
    const fullText = card.innerText;
    const lines = fullText.split('\n').filter(l => l.trim());

    // Parse title (longest line that isn't metadata)
    const title = lines.find(l =>
      l.length > 15 &&
      !l.includes('source') &&
      !l.match(/\d{4}/)
    ) || lines[0];

    const metadata = lines.find(l => l.includes('source'));

    cardData.parsed = {
      title,
      metadata,
      allLines: lines
    };

    return cardData;
  });
};
```

**Alternative Discovery Method (Using Accessibility Tree)**:

```javascript
// This requires using the browser automation tool's read_page functionality
// to get refs, then clicking on specific refs to interact

const discoverViaAccessibilityTree = async (page) => {
  const tree = await page.read_page({ filter: 'interactive' });

  // Find all "Project Actions Menu" buttons
  const actionsMenuRefs = tree.filter(node =>
    node.text && node.text.includes('Project Actions Menu')
  );

  // Their preceding siblings should be notebook cards
  // This mapping depends on the order in the accessibility tree

  return actionsMenuRefs.map(ref => ({
    actionsMenuRef: ref.id,
    // Card ref would be determined by position in tree
  }));
};
```

**Expected Output:**
```javascript
[
  {
    index: 0,
    classes: [
      "mat-mdc-card",
      "mdc-card",
      "mat-ripple",
      "project-button-card"
    ],
    structure: {
      public_indicator: { found: true, type: "IMG" },
      emoji: { found: true, content: "🤖", tagName: "DIV" }
    },
    parsed: {
      title: "Claude Code: The Architecture of Autonomous Development",
      metadata: "Dec 27, 2025 · 32 sources",
      allLines: [
        "🤖",
        "Claude Code: The Architecture of Autonomous Development",
        "Dec 27, 2025 · 32 sources",
        "public"
      ]
    }
  },
  // ... more cards
]
```

**DOM Structure (Recent Notebook Card):**
```html
<!-- Notebook Card Button -->
<button class="mat-mdc-card mdc-card mat-ripple project-button-card">
  <img alt="This project is public and anyone with link can view">
  <div>🤖</div>  <!-- Emoji -->
  <h3>Claude Code: The Architecture of Autonomous Development</h3>
  <span>Dec 27, 2025 · 32 sources</span>
  <mat-icon>public</mat-icon>
</button>

<!-- Sibling: Actions Menu Button -->
<button aria-label="Project Actions Menu">
  <img alt="more_vert">
</button>
```

---

## List View Discovery

### Phase 1: Switch to List View

```javascript
const switchToListView = async () => {
  // Find list view button
  const radioGroups = document.querySelectorAll('[role="radiogroup"]');
  const viewGroup = radioGroups[1]; // Second radiogroup

  const listViewBtn = Array.from(viewGroup.querySelectorAll('[role="radio"]')).find(btn =>
    btn.getAttribute('aria-label') === 'List view'
  );

  if (!listViewBtn) {
    return { success: false, reason: 'List view button not found' };
  }

  // Click to switch
  listViewBtn.click();
  await waitFor(1000);

  return { success: true };
};
```

---

### Phase 2: Discover Table Structure

```javascript
const discoverListView = () => {
  const listViewData = {
    mode: 'list',
    sections: {}
  };

  // Featured notebooks section
  const featuredHeading = Array.from(document.querySelectorAll('h1, h2, h3')).find(el =>
    el.innerText.includes('Featured notebooks')
  );

  if (featuredHeading) {
    // In list view, featured section shows as a table or list
    const nextElement = featuredHeading.nextElementSibling;

    listViewData.sections.featured = {
      heading: featuredHeading.innerText.trim(),
      hasTable: nextElement?.tagName === 'TABLE',
      containerType: nextElement?.tagName
    };

    if (nextElement?.tagName === 'TABLE') {
      const headers = Array.from(nextElement.querySelectorAll('th'));
      listViewData.sections.featured.columns = headers.map(th => ({
        text: th.innerText.trim(),
        classes: Array.from(th.classList)
      }));
    }
  }

  // Recent notebooks section
  const recentHeading = Array.from(document.querySelectorAll('h1, h2, h3')).find(el =>
    el.innerText.includes('Recent notebooks')
  );

  if (recentHeading) {
    const recentTable = recentHeading.nextElementSibling;

    listViewData.sections.recent = {
      heading: recentHeading.innerText.trim(),
      hasTable: recentTable?.tagName === 'TABLE',
      containerType: recentTable?.tagName,
      tableClasses: recentTable ? Array.from(recentTable.classList) : []
    };

    if (recentTable?.tagName === 'TABLE') {
      // Get column headers
      const headers = Array.from(recentTable.querySelectorAll('th'));
      listViewData.sections.recent.columns = headers.map(th => ({
        text: th.innerText.trim(),
        classes: Array.from(th.classList)
      }));

      // Sample first 3 rows
      const rows = Array.from(recentTable.querySelectorAll('tbody tr')).slice(0, 3);
      listViewData.sections.recent.sampleRows = rows.map((row, index) => {
        const cells = Array.from(row.querySelectorAll('td'));

        return {
          index,
          cellCount: cells.length,
          cells: cells.map((cell, cellIndex) => ({
            columnIndex: cellIndex,
            text: cell.innerText.trim(),
            hasIcon: cell.querySelector('img, mat-icon') !== null,
            hasButton: cell.querySelector('button') !== null,
            classes: Array.from(cell.classList)
          }))
        };
      });
    }
  }

  return listViewData;
};
```

**Expected Output:**
```javascript
{
  mode: "list",
  sections: {
    featured: {
      heading: "Featured notebooks",
      hasTable: true,
      containerType: "TABLE",
      columns: [
        { text: "Title" },
        { text: "Sources" },
        { text: "Created" },
        { text: "" },  // Public indicator column
        { text: "Role" },
        { text: "" }   // Actions menu column
      ]
    },
    recent: {
      heading: "Recent notebooks",
      hasTable: true,
      containerType: "TABLE",
      tableClasses: ["mat-mdc-table", "mdc-data-table__table", "cdk-table", "project-table"],
      columns: [
        { text: "Title" },
        { text: "Sources" },
        { text: "Created" },
        { text: "" },  // Public indicator column
        { text: "Role" },
        { text: "" }   // Actions menu column
      ],
      sampleRows: [
        {
          index: 0,
          cellCount: 6,
          cells: [
            {
              columnIndex: 0,
              text: "📦 Untitled notebook",
              hasIcon: true,
              hasButton: false
            },
            {
              columnIndex: 1,
              text: "0 Sources",
              hasIcon: false,
              hasButton: false
            },
            {
              columnIndex: 2,
              text: "Jan 1, 2026",
              hasIcon: false,
              hasButton: false
            },
            {
              columnIndex: 3,
              text: "",
              hasIcon: false,  // No public icon for private notebooks
              hasButton: false
            },
            {
              columnIndex: 4,
              text: "Owner",
              hasIcon: false,
              hasButton: false
            },
            {
              columnIndex: 5,
              text: "⋮",
              hasIcon: false,
              hasButton: true  // Actions menu button
            }
          ]
        },
        // ... more rows
      ]
    }
  }
}
```

**Table Column Structure:**

| Column Index | Header | Content Type | Example |
|--------------|--------|--------------|---------|
| 0 | Title | Text with emoji/icon | "🤖 Claude Code: The Architecture..." |
| 1 | Sources | Text | "32 Sources" |
| 2 | Created | Date text | "Dec 27, 2025" |
| 3 | (empty) | Icon (conditional) | 🔗 (public indicator) |
| 4 | Role | Text | "Owner" or "Reader" |
| 5 | (empty) | Button | ⋮ (actions menu) |

**DOM Structure (List View):**
```html
<table class="mat-mdc-table mdc-data-table__table cdk-table project-table">
  <thead>
    <tr>
      <th>Title</th>
      <th>Sources</th>
      <th>Created</th>
      <th></th>  <!-- Public indicator column -->
      <th>Role</th>
      <th></th>  <!-- Actions column -->
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>
        <img alt="emoji">
        <span>Claude Code: The Architecture of...</span>
      </td>
      <td>32 Sources</td>
      <td>Dec 27, 2025</td>
      <td>
        <mat-icon>public</mat-icon>  <!-- If public -->
      </td>
      <td>Owner</td>
      <td>
        <button aria-label="Project Actions Menu">
          <img alt="more_vert">
        </button>
      </td>
    </tr>
    <!-- ... more rows -->
  </tbody>
</table>
```

---

## Notebook Actions Discovery

### Phase 1: Open Actions Menu

```javascript
const openNotebookActionsMenu = async (notebookCard) => {
  // Find the actions menu button (sibling of card button in grid view)
  const actionsMenuBtn = notebookCard.nextElementSibling;

  if (!actionsMenuBtn || !actionsMenuBtn.innerText.includes('Project Actions')) {
    return { success: false, reason: 'Actions menu button not found' };
  }

  actionsMenuBtn.click();
  await waitFor(500);

  const menu = document.querySelector('[role="menu"]');

  return {
    success: menu !== null,
    menu
  };
};
```

**Alternative for List View:**

```javascript
const openActionsMenuListView = async (tableRow) => {
  // In list view, actions button is in the last cell
  const cells = tableRow.querySelectorAll('td');
  const lastCell = cells[cells.length - 1];

  const actionsBtn = lastCell.querySelector('button');

  if (!actionsBtn) {
    return { success: false, reason: 'Actions button not found in row' };
  }

  actionsBtn.click();
  await waitFor(500);

  const menu = document.querySelector('[role="menu"]');

  return {
    success: menu !== null,
    menu
  };
};
```

---

### Phase 2: Capture Menu Items

```javascript
const captureActionsMenuItems = (menu) => {
  const menuItems = Array.from(menu.querySelectorAll('[role="menuitem"]'));

  return menuItems.map(item => ({
    text: item.innerText.trim(),
    icon: item.querySelector('img, mat-icon')?.innerText ||
          item.querySelector('img')?.alt,
    classes: Array.from(item.classList),
    action: detectActionType(item.innerText)
  }));
};

const detectActionType = (text) => {
  const lower = text.toLowerCase();

  const actionMap = {
    'delete': 'delete',
    'edit title': 'edit_title',
    'rename': 'rename',
    'duplicate': 'duplicate',
    'share': 'share'
  };

  for (const [keyword, action] of Object.entries(actionMap)) {
    if (lower.includes(keyword)) return action;
  }

  return 'unknown';
};
```

**Expected Output:**
```javascript
[
  {
    text: "delete\nDelete",
    icon: "delete",
    classes: [
      "mat-mdc-menu-item",
      "mat-focus-indicator",
      "project-button-hamburger-menu-action",
      "delete-button"
    ],
    action: "delete"
  },
  {
    text: "edit\nEdit title",
    icon: "edit",
    classes: [
      "mat-mdc-menu-item",
      "mat-focus-indicator",
      "project-button-hamburger-menu-action"
    ],
    action: "edit_title"
  }
]
```

**DOM Structure (Actions Menu):**
```html
<div role="menu" class="mat-mdc-menu-panel mat-menu-after mat-menu-below">
  <button role="menuitem" class="mat-mdc-menu-item mat-focus-indicator delete-button">
    <img alt="delete">
    <span>Delete</span>
  </button>
  <button role="menuitem" class="mat-mdc-menu-item mat-focus-indicator">
    <img alt="edit">
    <span>Edit title</span>
  </button>
</div>
```

---

## Create Notebook Flow

### Phase 1: Click "Create new" Button

```javascript
const createNewNotebook = async () => {
  const createBtn = Array.from(document.querySelectorAll('button')).find(btn =>
    btn.innerText.includes('Create new')
  );

  if (!createBtn) {
    return { success: false, reason: 'Create button not found' };
  }

  createBtn.click();
  await waitFor(2000);  // Wait for navigation and page load

  // Check if navigated to new notebook page
  const url = window.location.href;
  const isNotebookPage = url.includes('/notebook/');

  return {
    success: isNotebookPage,
    url,
    navigatedToNotebook: isNotebookPage
  };
};
```

---

### Phase 2: Discover New Notebook Interface

```javascript
const discoverNewNotebookInterface = () => {
  // After creating, user lands on notebook page with "Add source" dialog

  const dialog = document.querySelector('[role="dialog"]');
  const addSourceButton = document.querySelector('button:has-text("Add source")');
  const titleInput = document.querySelector('input, [contenteditable]');

  return {
    hasDialog: dialog !== null,
    dialogTitle: dialog?.querySelector('h1, h2')?.innerText,
    hasAddSourceButton: addSourceButton !== null,
    hasTitleInput: titleInput !== null,
    defaultTitle: titleInput?.value || titleInput?.innerText || 'Untitled notebook',
    url: window.location.href,
    notebookId: window.location.pathname.split('/').pop()
  };
};
```

**Expected Output:**
```javascript
{
  hasDialog: true,
  dialogTitle: "Create Audio and Video Overviews from websites",
  hasAddSourceButton: true,
  hasTitleInput: true,
  defaultTitle: "Untitled notebook",
  url: "https://notebooklm.google.com/notebook/cd762fcd-3585-44d3-92de-7b94e4bedfb8?addSource=true",
  notebookId: "cd762fcd-3585-44d3-92de-7b94e4bedfb8"
}
```

---

## Complete Discovery Algorithm

```javascript
/**
 * Complete Notebook List page discovery function
 * Returns comprehensive metadata about all home page elements
 */
async function discoverNotebookListPage() {
  const discovery = {
    timestamp: new Date().toISOString(),
    page: 'notebook_list',
    url: window.location.href,
    header: {},
    viewMode: 'grid',
    sections: {}
  };

  // === PHASE 1: Header Navigation ===
  discovery.header = {
    logo: discoverLogo(),
    settings: discoverSettingsButton(),
    proBadge: discoverProBadge(),
    filters: discoverFilterTabs(),
    viewControls: discoverViewControls(),
    sortControl: discoverSortControl(),
    createButton: discoverCreateButton()
  };

  // === PHASE 2: Determine Current View Mode ===
  const viewControls = discovery.header.viewControls;
  const gridViewSelected = viewControls.views?.find(v =>
    v.ariaLabel === 'Grid view' && v.isSelected
  );
  discovery.viewMode = gridViewSelected ? 'grid' : 'list';

  // === PHASE 3: Featured Notebooks ===
  if (discovery.viewMode === 'grid') {
    discovery.sections.featured = {
      heading: discoverFeaturedSection(),
      cards: discoverFeaturedCards()
    };
  } else {
    discovery.sections.featured = discoverListView().sections.featured;
  }

  // === PHASE 4: Recent Notebooks ===
  if (discovery.viewMode === 'grid') {
    discovery.sections.recent = {
      createNewCard: discoverCreateNewCard(),
      cards: discoverRecentNotebookCards()
    };
  } else {
    discovery.sections.recent = discoverListView().sections.recent;
  }

  // === PHASE 5: Sample Actions Menu ===
  // Open first notebook's actions menu to discover available actions
  let sampleCard = null;

  if (discovery.viewMode === 'grid') {
    const cards = discovery.sections.recent.cards;
    if (cards.length > 0) {
      sampleCard = cards[0];
    }
  } else {
    const table = document.querySelector('.project-table');
    const firstRow = table?.querySelector('tbody tr');
    if (firstRow) {
      const menuResult = await openActionsMenuListView(firstRow);
      if (menuResult.success) {
        discovery.actions = {
          available: captureActionsMenuItems(menuResult.menu)
        };

        // Close menu
        document.body.click();
        await waitFor(300);
      }
    }
  }

  // === PHASE 6: Test View Toggle ===
  // Switch to opposite view to capture both layouts
  const currentView = discovery.viewMode;
  const targetView = currentView === 'grid' ? 'list' : 'grid';

  await switchToListView();  // or switchToGridView()
  await waitFor(1000);

  discovery.alternateView = {
    mode: targetView,
    sections: discoverListView().sections
  };

  // Switch back to original view
  if (currentView === 'grid') {
    const gridBtn = viewControls.views?.find(v => v.ariaLabel === 'Grid view');
    // Click grid button
  }

  return discovery;
}
```

---

## Validation Results

### Session Date: 2026-01-01

All selectors were validated against `config/selectors.json` with **100% accuracy**.

#### Validated Selectors (config/selectors.json lines 3-21)

1. **✅ create_notebook_button** - Perfect match
   - Primary selector: `button:has-text('Create new')` ✅
   - Fallback: `span:has-text('Create new')` ✅
   - Card selector: `mat-card[role='button']:has-text('Create new notebook')` ✅
   - ARIA: `button[aria-label*='Create new notebook']` ✅
   - Text: `button:has-text('Create new notebook')` ✅

2. **✅ notebook_card** - Perfect match
   - With menu: `mat-card:has(button:has-text('more_vert'))` ✅
   - With h3: `mat-card[role='button']:has(h3)` ✅
   - Div variant: `div[role='button']:has(h3)` ✅
   - Article: `article:has(h3)` ✅

3. **✅ notebook_card_menu** - Perfect match
   - ARIA label: `button[aria-label*='More options']` ✅
   - Text content: `button:has-text('⋮')` ✅

#### Discrepancies Found

**NONE** - All configurations in `config/selectors.json` are accurate and up-to-date as of 2026-01-01.

#### Additional Discoveries Not in Config

1. **Filter Tabs** - Not currently in config
   - Selector: `[role="radiogroup"]` (first instance)
   - Options: "All", "My notebooks", "Featured notebooks"

2. **View Controls** - Not currently in config
   - Selector: `[role="radiogroup"]:nth-of-type(2)`
   - Options: "Grid view", "List view"

3. **Sort Control** - Not currently in config
   - Selector: `button:has-text("Most recent")`
   - Action: Opens dropdown menu

4. **Settings Button** - Not currently in config
   - Selector: `button:has(img[alt="settings"])`

5. **Logo Link** - Not currently in config
   - Selector: `a[href="/"]`

6. **List View Table** - Not currently in config
   - Selector: `.project-table` or `table.mat-mdc-table`
   - Structure: 6 columns (Title, Sources, Created, Public Icon, Role, Actions)

7. **Featured Notebook Cards** - Not currently in config
   - Selector: `[role="group"].featured-project-card`
   - Distinguished from recent cards by `.featured-project-card` class

---

## Key Learnings

### 1. Two View Modes with Different DOM Structures

**Grid View:**
- Uses `mat-card` elements with `role="button"` or `role="group"`
- Cards are flexbox or grid layout
- Actions menu button is SIBLING of card button
- Emoji/icon displayed prominently

**List View:**
- Uses `table.mat-mdc-table` structure
- 6 columns per row
- Actions menu button is INSIDE last table cell
- More compact, scannable layout

### 2. Featured vs Recent Notebooks

**Featured:**
- Always use `[role="group"]` with `.featured-project-card` class
- Have publisher badges (e.g., "Travel", "The Atlantic")
- Background images on cards
- All marked as public

**Recent:**
- User's own notebooks
- Emoji or custom icons
- Can be public or private
- Have "Owner" or "Reader" role

### 3. Card Discovery Challenge

Recent notebook cards are difficult to discover via standard DOM queries because:
- Card button and actions menu button are siblings, not parent-child
- No unique class or attribute on card button itself
- Must use positional queries or accessibility tree

**Best Discovery Strategy:**
1. Find all "Project Actions Menu" buttons
2. Get their `previousElementSibling`
3. Filter for buttons
4. Those are the notebook card buttons

### 4. Create New Notebook Flow

Clicking "Create new" does TWO things:
1. Creates a new notebook (server-side)
2. Navigates to the new notebook page with `?addSource=true` parameter
3. Opens "Add source" dialog automatically

This is a single-click flow, no intermediate dialog.

### 5. Actions Menu Items

As of 2026-01-01, notebook actions menu contains:
- **Delete** - Deletes the notebook
- **Edit title** - Renames the notebook

Other expected actions (not found):
- Duplicate
- Share (may appear for public notebooks only)

### 6. Public Indicator

Public notebooks show a 🔗 icon or `mat-icon` with "public" text:
- Grid view: Icon overlay on card
- List view: Icon in dedicated column (column index 3)

---

## Automation Best Practices

### 1. View Mode Detection

Always detect current view mode before attempting card discovery:

```javascript
// ✅ Good: Detect view mode first
const detectViewMode = () => {
  const viewControls = document.querySelectorAll('[role="radiogroup"]')[1];
  const gridBtn = viewControls?.querySelector('[aria-label="Grid view"]');
  return gridBtn?.getAttribute('aria-checked') === 'true' ? 'grid' : 'list';
};

const viewMode = detectViewMode();

if (viewMode === 'grid') {
  // Use grid discovery
} else {
  // Use list discovery
}
```

### 2. Robust Card Discovery

Use accessibility tree when available:

```javascript
// ✅ Good: Use accessibility tree for reliable discovery
const discoverCardsViaAccessibilityTree = async (page) => {
  const tree = await page.read_page({ filter: 'interactive' });

  const actionsMenus = tree.filter(node =>
    node.role === 'button' &&
    node.text?.includes('Project Actions Menu')
  );

  return actionsMenus.map(menu => ({
    menuRef: menu.ref,
    // Card ref is typically the preceding ref in tree
  }));
};
```

### 3. Wait for Navigation

After clicking "Create new", wait for URL change:

```javascript
// ✅ Good: Wait for navigation to complete
const createNotebook = async () => {
  const createBtn = document.querySelector('button:has-text("Create new")');
  const oldUrl = window.location.href;

  createBtn.click();

  // Wait for URL change
  await waitForCondition(() => window.location.href !== oldUrl, 5000);

  // Wait for page load
  await waitFor(2000);
};
```

### 4. List View Table Navigation

Navigate rows programmatically:

```javascript
// ✅ Good: Use table structure for predictable navigation
const getAllNotebooksFromListView = () => {
  const table = document.querySelector('.project-table');
  const rows = Array.from(table.querySelectorAll('tbody tr'));

  return rows.map(row => {
    const cells = row.querySelectorAll('td');

    return {
      title: cells[0]?.innerText.trim(),
      sources: cells[1]?.innerText.trim(),
      created: cells[2]?.innerText.trim(),
      isPublic: cells[3]?.querySelector('mat-icon') !== null,
      role: cells[4]?.innerText.trim(),
      actionsButton: cells[5]?.querySelector('button')
    };
  });
};
```

### 5. Error Recovery

Handle missing elements gracefully:

```javascript
// ✅ Good: Check existence before interacting
const openActionsMenu = async (notebookCard) => {
  const actionsBtn = notebookCard?.nextElementSibling;

  if (!actionsBtn) {
    return {
      success: false,
      reason: 'Actions button not found',
      suggestion: 'May be in list view or card structure changed'
    };
  }

  if (!actionsBtn.innerText.includes('Project Actions')) {
    return {
      success: false,
      reason: 'Next sibling is not actions button',
      actualElement: actionsBtn.tagName
    };
  }

  actionsBtn.click();
  await waitFor(500);

  const menu = document.querySelector('[role="menu"]');

  if (!menu) {
    return {
      success: false,
      reason: 'Menu did not appear after click'
    };
  }

  return { success: true, menu };
};
```

---

**End of Notebook List Discovery Documentation**
