# Studio Panel Discovery Documentation

**Created**: 2026-01-01
**Purpose**: Automated discovery blueprint for NotebookLM Studio Panel UI elements, artifact types, customization dialogs, and actions

**Session Validation**: All artifact types validated 100% match with `config/artifact_types_fallback.json`

---

## Table of Contents

1. [Overview](#overview)
2. [Studio Panel Structure](#studio-panel-structure)
3. [Artifact Type Discovery](#artifact-type-discovery)
4. [Customization Dialog Discovery](#customization-dialog-discovery)
5. [Artifact Actions Discovery](#artifact-actions-discovery)
6. [Complete Discovery Algorithm](#complete-discovery-algorithm)
7. [Validation Results](#validation-results)

---

## Overview

The Studio Panel is the right panel in NotebookLM where users create, manage, and interact with AI-generated artifacts. This document provides a comprehensive blueprint for automated discovery of all Studio Panel functionality based on real browser exploration completed 2026-01-01.

### Key Components

1. **Artifact Type Buttons** - Top section with 9 artifact creation buttons
2. **Artifact Library** - Bottom section with generated artifacts
3. **Customization Dialogs** - Modal dialogs for configuring artifact generation
4. **Add Note Button** - Special creation method for Note artifacts
5. **Artifact Actions Menus** - Per-artifact action menus (rename, delete, download, etc.)

### Artifact Types Discovered

| Type | Customizable | Creation Pattern | Parent Button |
|------|--------------|------------------|---------------|
| Audio Overview | ✅ Yes | Direct | - |
| Video Overview | ✅ Yes | Direct | - |
| Mind Map | ❌ No | Direct | - |
| Reports | ✅ Yes | Multi-step | Reports → Format selection |
| Flashcards | ✅ Yes | Direct | - |
| Quiz | ✅ Yes | Direct | - |
| Infographic | ✅ Yes | Direct | - |
| Slide Deck | ✅ Yes | Direct | - |
| Data Table | ✅ Yes | Direct | - |
| Note | ❌ No | Manual | "Add note" button |

---

## Studio Panel Structure

### High-Level Layout

```
┌──────────────────────────────────┐
│ Studio (Tab Header)              │
├──────────────────────────────────┤
│ ARTIFACT TYPE BUTTONS (Top Half) │
│ ┌────────┬────────┬────────┐    │
│ │ Audio  │ Video  │  Mind  │    │
│ │Overview│Overview│  Map   │    │
│ │   ✏️   │   ✏️   │        │    │
│ └────────┴────────┴────────┘    │
│ ┌────────┬────────┬────────┐    │
│ │Reports │  Flash │  Quiz  │    │
│ │   📄   │ cards  │   📝   │    │
│ │        │   ✏️   │   ✏️   │    │
│ └────────┴────────┴────────┘    │
│ ┌────────┬────────┬────────┐    │
│ │ Info-  │ Slide  │  Data  │    │
│ │graphic │  Deck  │ Table  │    │
│ │   ✏️   │   ✏️   │   ✏️   │    │
│ └────────┴────────┴────────┘    │
├──────────────────────────────────┤
│ ARTIFACT LIBRARY (Bottom Half)   │
│ ┌──────────────────────────────┐ │
│ │ 🎵 Engineering Digital Trust │ │
│ │    32 sources · 14m ago   ⋮  │ │
│ └──────────────────────────────┘ │
│ ┌──────────────────────────────┐ │
│ │ 📊 System Test Report        │ │
│ │    32 sources · 16m ago   ⋮  │ │
│ └──────────────────────────────┘ │
│                                  │
│ [+ Add note]                     │ ← Note creation
└──────────────────────────────────┘
```

---

## Artifact Type Discovery

### Phase 1: Identify All Artifact Type Buttons

#### Step 1.1: Locate Studio Panel
```javascript
const studioPanel = document.querySelector(
  '.studio-panel, [class*="studio"], [aria-label*="Studio"]'
);

// Verify panel is visible
const isVisible = studioPanel &&
  window.getComputedStyle(studioPanel).display !== 'none';
```

#### Step 1.2: Find All Artifact Buttons
```javascript
const discoverArtifactButtons = () => {
  // Primary selector from config
  const buttons = Array.from(document.querySelectorAll(
    '.create-artifact-button-container'
  ));

  return buttons.map((btn, index) => {
    // Extract artifact name (usually second line of text)
    const text = btn.innerText;
    const lines = text.split('\n').filter(l => l.trim());
    const name = lines[1] || lines[0]; // Icon is first, name is second

    // Check for customization icon
    const editIcon = btn.querySelector('.option-icon');
    const hasEditIcon = editIcon !== null;

    // Get icon
    const icon = btn.querySelector('mat-icon, svg');
    const iconName = icon?.innerText || icon?.getAttribute('aria-label');

    return {
      index,
      name,
      iconName,
      hasEditIcon,
      customizable: hasEditIcon,
      element: btn
    };
  });
};
```

**Expected Output:**
```javascript
[
  {index: 0, name: "Audio Overview", hasEditIcon: true, customizable: true},
  {index: 1, name: "Video Overview", hasEditIcon: true, customizable: true},
  {index: 2, name: "Mind Map", hasEditIcon: false, customizable: false},
  {index: 3, name: "Reports", hasEditIcon: false, customizable: false}, // Special
  {index: 4, name: "Flashcards", hasEditIcon: true, customizable: true},
  {index: 5, name: "Quiz", hasEditIcon: true, customizable: true},
  {index: 6, name: "Infographic", hasEditIcon: true, customizable: true},
  {index: 7, name: "Slide Deck", hasEditIcon: true, customizable: true},
  {index: 8, name: "Data Table", hasEditIcon: true, customizable: true}
]
```

**DOM Structure:**
```html
<div class="create-artifact-button-container" role="button">
  <mat-icon>audio_magic_eraser</mat-icon>
  <span>Audio Overview</span>
  <div class="option-icon">edit</div>  <!-- If customizable -->
</div>
```

---

### Phase 2: Distinguish Artifact Creation Patterns

#### Pattern Detection
```javascript
const detectCreationPattern = (artifactName, hasEditIcon) => {
  if (artifactName === 'Note') {
    return {
      pattern: 'manual',
      description: 'Created via separate "Add note" button'
    };
  }

  if (artifactName === 'Reports') {
    return {
      pattern: 'multi_step',
      description: 'Click button → Select format → Customize format'
    };
  }

  if (hasEditIcon) {
    return {
      pattern: 'direct_customizable',
      description: 'Click edit icon → Customize → Generate'
    };
  }

  return {
    pattern: 'direct_simple',
    description: 'Click button → Generate immediately'
  };
};
```

---

## Customization Dialog Discovery

### Pattern 1: Direct Customization (Standard Artifacts)

**Applies to**: Audio Overview, Video Overview, Quiz, Flashcards, Infographic, Slide Deck, Data Table

#### Step 1: Click Edit Icon (NOT entire button)

**CRITICAL**: Clicking the entire button triggers immediate generation. Must click only the edit/pencil icon.

```javascript
const openCustomizationDialog = async (artifactButton) => {
  // Find the edit icon within the button
  const editIcon = artifactButton.querySelector('.option-icon');

  if (!editIcon) {
    return {
      success: false,
      reason: 'No edit icon found - artifact not customizable'
    };
  }

  // Get coordinates of edit icon specifically
  const rect = editIcon.getBoundingClientRect();
  const clickCoords = {
    x: rect.x + rect.width / 2,
    y: rect.y + rect.height / 2
  };

  // Click the edit icon
  // (Use browser automation to click at clickCoords)
  editIcon.click();

  // Wait for dialog
  await waitFor(1000);

  const dialog = document.querySelector('mat-dialog-container, [role="dialog"]');

  return {
    success: dialog !== null,
    dialog
  };
};
```

**Common Mistake:**
```javascript
// ❌ WRONG - This triggers generation without customization
artifactButton.click();

// ✅ CORRECT - Click only the edit icon
artifactButton.querySelector('.option-icon').click();
```

#### Step 2: Capture Dialog Fields

```javascript
const captureCustomizationFields = (dialog) => {
  const fields = {
    title: null,
    cardSelectors: [],
    dropdowns: [],
    radioGroups: [],
    textareas: [],
    thumbnailSelectors: []
  };

  // Get dialog title
  const titleEl = dialog.querySelector('h1, h2, [class*="title"]');
  fields.title = titleEl?.innerText;

  // 1. CARD SELECTORS (Format selection)
  const cards = Array.from(dialog.querySelectorAll('[role="radio"], .format-card'));
  if (cards.length > 0 && cards[0].querySelector('h3, [class*="label"]')) {
    fields.cardSelectors = cards.map(card => ({
      label: card.querySelector('h3, [class*="label"]')?.innerText,
      description: card.querySelector('p, [class*="description"]')?.innerText,
      isSelected: card.querySelector('mat-icon[innerText="checkmark"]') !== null ||
                  card.getAttribute('aria-checked') === 'true'
    }));
  }

  // 2. DROPDOWNS
  const selects = Array.from(dialog.querySelectorAll('select, mat-select, button[role="combobox"]'));
  fields.dropdowns = selects.map(select => {
    // Find label (usually preceding element or parent label)
    const label = select.previousElementSibling?.innerText ||
                  select.closest('label')?.innerText ||
                  select.getAttribute('aria-label');

    const selectedValue = select.value || select.innerText;

    return {
      label,
      selectedValue,
      type: 'dropdown'
    };
  });

  // 3. RADIO GROUPS
  const radioGroups = Array.from(dialog.querySelectorAll('[role="radiogroup"]'));
  fields.radioGroups = radioGroups.map(group => {
    // Get group label
    const groupLabel = group.previousElementSibling?.innerText ||
                       group.getAttribute('aria-label');

    // Get all radio options
    const radios = Array.from(group.querySelectorAll('[role="radio"], button'));
    const options = radios.map(radio => ({
      label: radio.innerText.trim(),
      selected: radio.getAttribute('aria-checked') === 'true' ||
                radio.classList.contains('selected')
    }));

    return {
      label: groupLabel,
      options,
      type: 'radio'
    };
  });

  // 4. TEXTAREAS
  const textareas = Array.from(dialog.querySelectorAll('textarea'));
  fields.textareas = textareas.map(textarea => {
    // Find label
    const label = textarea.previousElementSibling?.innerText ||
                  textarea.getAttribute('aria-label') ||
                  textarea.getAttribute('placeholder');

    return {
      label,
      placeholder: textarea.placeholder,
      value: textarea.value,
      required: textarea.hasAttribute('required'),
      type: 'textarea'
    };
  });

  // 5. THUMBNAIL SELECTORS (e.g., Video Overview visual styles)
  const thumbnails = Array.from(dialog.querySelectorAll('button:has(img), [role="radio"]:has(img)'));
  if (thumbnails.length > 0) {
    fields.thumbnailSelectors = thumbnails.map(thumb => ({
      label: thumb.getAttribute('aria-label') || thumb.querySelector('span')?.innerText,
      imageUrl: thumb.querySelector('img')?.src,
      isSelected: thumb.getAttribute('aria-checked') === 'true',
      type: 'thumbnail_selector'
    }));
  }

  return fields;
};
```

#### Step 3: Structure Field Metadata

```javascript
const structureFieldMetadata = (capturedFields) => {
  const metadata = {
    artifact_type: null,
    customization_fields: []
  };

  // Infer artifact type from dialog title
  metadata.artifact_type = capturedFields.title?.toLowerCase()
    .replace('customize ', '')
    .replace(/ /g, '_');

  // Process card selectors
  if (capturedFields.cardSelectors.length > 0) {
    metadata.customization_fields.push({
      id: 'format',
      label: 'Format',
      type: 'card_selector',
      required: true,
      options: capturedFields.cardSelectors.map(card => ({
        value: card.label.toLowerCase().replace(/\s+/g, '_'),
        label: card.label,
        description: card.description
      })),
      default: capturedFields.cardSelectors.find(c => c.isSelected)?.label
    });
  }

  // Process dropdowns
  capturedFields.dropdowns.forEach(dropdown => {
    metadata.customization_fields.push({
      id: dropdown.label.toLowerCase().replace(/\s+/g, '_'),
      label: dropdown.label,
      type: 'dropdown',
      required: true,
      default: dropdown.selectedValue
    });
  });

  // Process radio groups
  capturedFields.radioGroups.forEach(group => {
    metadata.customization_fields.push({
      id: group.label.toLowerCase().replace(/\s+/g, '_').replace(/\?/g, ''),
      label: group.label,
      type: 'radio',
      required: true,
      options: group.options.map(opt => ({
        value: opt.label.toLowerCase(),
        label: opt.label
      })),
      default: group.options.find(o => o.selected)?.label
    });
  });

  // Process textareas
  capturedFields.textareas.forEach(textarea => {
    metadata.customization_fields.push({
      id: textarea.label.toLowerCase().replace(/\s+/g, '_').replace(/\?/g, ''),
      label: textarea.label,
      type: 'textarea',
      required: textarea.required,
      placeholder: textarea.placeholder,
      default: textarea.value || undefined
    });
  });

  // Process thumbnail selectors
  if (capturedFields.thumbnailSelectors.length > 0) {
    metadata.customization_fields.push({
      id: 'visual_style',
      label: 'Visual Style',
      type: 'thumbnail_selector',
      required: false,
      options: capturedFields.thumbnailSelectors.map(thumb => ({
        value: thumb.label.toLowerCase().replace(/\s+/g, '_'),
        label: thumb.label
      }))
    });
  }

  return metadata;
};
```

---

### Pattern 2: Reports (Multi-Step Selection)

Reports follows a unique two-dialog flow.

#### Step 1: Click Reports Button (entire button, not edit icon)

```javascript
const openReportsDialog = async () => {
  const reportsButton = Array.from(
    document.querySelectorAll('.create-artifact-button-container')
  ).find(btn => btn.innerText.includes('Reports'));

  // Click entire button (Reports doesn't have edit icon on main button)
  reportsButton.click();
  await waitFor(1000);

  const dialog = document.querySelector('mat-dialog-container');
  return dialog;
};
```

#### Step 2: Discover Report Formats

```javascript
const discoverReportFormats = (dialog) => {
  // Reports dialog has sections: "Create Your Own" and "Suggested Format"
  const sections = Array.from(dialog.querySelectorAll('section, div[class*="section"]'));

  const formats = [];

  sections.forEach(section => {
    const sectionTitle = section.querySelector('h2, h3')?.innerText;

    const formatCards = Array.from(section.querySelectorAll('[role="button"]'));

    formatCards.forEach(card => {
      const name = card.querySelector('h3, [class*="title"]')?.innerText;
      const description = card.querySelector('p, [class*="description"]')?.innerText;
      const editIcon = card.querySelector('.option-icon');

      formats.push({
        category: sectionTitle,
        name,
        description,
        hasCustomization: editIcon !== null,
        element: card
      });
    });
  });

  return formats;
};
```

**Expected Output:**
```javascript
[
  {
    category: "Create Your Own",
    name: "Briefing Doc",
    description: "Overview of your sources featuring key insights and quotes",
    hasCustomization: true
  },
  {
    category: "Create Your Own",
    name: "Study Guide",
    description: "Short-answer quiz, suggested essay questions...",
    hasCustomization: true
  },
  {
    category: "Suggested Format",
    name: "Technical Report",
    description: "An analysis of test cases and validation methods...",
    hasCustomization: true
  }
  // ... more formats
]
```

#### Step 3: Click Format's Edit Icon

```javascript
const openFormatCustomization = async (formatCard) => {
  const editIcon = formatCard.querySelector('.option-icon');

  if (!editIcon) {
    return { success: false, reason: 'Format not customizable' };
  }

  editIcon.click();
  await waitFor(1000);

  const customizationDialog = document.querySelector('mat-dialog-container');

  return {
    success: customizationDialog !== null,
    dialog: customizationDialog
  };
};
```

#### Step 4: Capture Format Customization

```javascript
// Now use the same field capture as Pattern 1
const formatFields = captureCustomizationFields(customizationDialog);
```

**Example: Briefing Doc Fields**
```javascript
{
  title: "Briefing Doc",
  dropdowns: [
    {label: "Choose language", selectedValue: "English (default)"}
  ],
  textareas: [
    {
      label: "Describe the report you want to create",
      placeholder: "For example:\n\nCreate a formal competitive review...",
      value: "Create a comprehensive briefing document..."
    }
  ]
}
```

---

### Pattern 3: Note (Manual Editor)

Note doesn't have a customization dialog - it opens an editor directly.

#### Step 1: Locate "Add note" Button

```javascript
const findAddNoteButton = () => {
  // This button is typically at bottom of Studio Panel
  const buttons = Array.from(document.querySelectorAll('button'));
  const addNoteButton = buttons.find(btn =>
    btn.innerText.includes('Add note')
  );

  return addNoteButton;
};
```

**DOM Structure:**
```html
<button class="add-note-button">
  <mat-icon>sticky_note_2</mat-icon>
  <span>Add note</span>
</button>
```

#### Step 2: Click to Open Editor

```javascript
const createNote = async () => {
  const addNoteButton = findAddNoteButton();

  if (!addNoteButton) {
    return { success: false, reason: 'Add note button not found' };
  }

  addNoteButton.click();
  await waitFor(1000);

  // Check if note editor appeared
  const noteEditor = document.querySelector('.note-editor, [class*="note"]');
  const breadcrumb = Array.from(document.querySelectorAll('*')).find(
    el => el.innerText === 'Studio > Note'
  );

  return {
    success: noteEditor !== null || breadcrumb !== null,
    interface: 'editor' // Not a customization dialog
  };
};
```

#### Step 3: Identify Note Editor Interface

```javascript
const discoverNoteInterface = () => {
  // Note editor has:
  // - Title field ("New Note")
  // - Rich text toolbar
  // - Content area
  // - "Convert to source" button

  const titleField = Array.from(document.querySelectorAll('input, [contenteditable]')).find(
    el => el.innerText === 'New Note' || el.value === 'New Note'
  );

  const convertButton = Array.from(document.querySelectorAll('button')).find(
    btn => btn.innerText.includes('Convert to source')
  );

  const deleteButton = Array.from(document.querySelectorAll('button')).find(
    btn => btn.getAttribute('aria-label')?.includes('delete') ||
           btn.querySelector('mat-icon[innerText="delete"]')
  );

  return {
    hasTitle: titleField !== null,
    hasConvertToSource: convertButton !== null,
    hasDelete: deleteButton !== null,
    hasToolbar: true, // Rich text toolbar always present
    customizable: false, // No customization - direct editor
    creation_method: 'manual'
  };
};
```

---

## Artifact Actions Discovery

### Phase 1: Discover Generated Artifacts

#### Step 1: Find Artifact Library

```javascript
const discoverArtifactLibrary = () => {
  const library = document.querySelector(
    '.artifact-library-container, [class*="artifact-library"]'
  );

  if (!library) {
    return { found: false, artifacts: [] };
  }

  const artifactRows = Array.from(library.querySelectorAll(
    '.artifact-item-button, [class*="artifact-item"]'
  ));

  return {
    found: true,
    count: artifactRows.length,
    artifacts: artifactRows
  };
};
```

#### Step 2: Extract Artifact Metadata

```javascript
const extractArtifactInfo = (artifactRow) => {
  // Get icon (indicates type)
  const icon = artifactRow.querySelector('mat-icon, svg');
  const iconName = icon?.innerText;

  // Get title
  const title = artifactRow.querySelector('.artifact-title, h3, [class*="title"]')?.innerText;

  // Get details (sources, time)
  const details = artifactRow.querySelector('.artifact-details, [class*="details"]')?.innerText;

  // Parse details for source count and time
  const sourceMatch = details?.match(/(\d+)\s*source/);
  const sourceCount = sourceMatch ? parseInt(sourceMatch[1]) : null;

  const timeMatch = details?.match(/(\d+[hmd]|just now)/);
  const timeAgo = timeMatch ? timeMatch[0] : null;

  // Detect artifact type from icon
  const type = detectArtifactTypeFromIcon(iconName);

  // Check for playable (Audio/Video)
  const playButton = artifactRow.querySelector('button[aria-label*="Play"]');
  const isPlayable = playButton !== null;

  return {
    title,
    type,
    iconName,
    sourceCount,
    timeAgo,
    isPlayable,
    element: artifactRow
  };
};

const detectArtifactTypeFromIcon = (iconName) => {
  const iconMap = {
    'audio_magic_eraser': 'audio_overview',
    'video_camera_front': 'video_overview',
    'account_tree': 'mind_map',
    'auto_tab_group': 'report',
    'quiz': 'quiz',
    'style': 'flashcards',
    'image': 'infographic',
    'slideshow': 'slide_deck',
    'table_chart': 'data_table',
    'sticky_note_2': 'note'
  };

  return iconMap[iconName] || 'unknown';
};
```

---

### Phase 2: Discover Artifact Actions Menu

#### Step 1: Open More Menu

```javascript
const openArtifactMenu = async (artifactRow) => {
  const moreButton = artifactRow.querySelector(
    '.artifact-more-button, button[aria-label*="More"]'
  );

  if (!moreButton) {
    return { found: false, reason: 'No more button found' };
  }

  moreButton.click();
  await waitFor(500);

  const menu = document.querySelector('[role="menu"], mat-menu');

  return {
    found: menu !== null,
    menu
  };
};
```

#### Step 2: Capture Available Actions

```javascript
const discoverArtifactActions = (menu) => {
  const menuItems = Array.from(menu.querySelectorAll('[role="menuitem"], button'));

  return menuItems.map(item => ({
    text: item.innerText.trim(),
    action: detectActionType(item.innerText),
    icon: item.querySelector('mat-icon')?.innerText,
    element: item
  }));
};

const detectActionType = (text) => {
  const lower = text.toLowerCase();

  const actionMap = {
    'rename': 'rename',
    'delete': 'delete',
    'download': 'download',
    'share': 'share',
    'export to docs': 'export_to_docs',
    'export to sheets': 'export_to_sheets',
    'convert to source': 'convert_to_source',
    'convert all notes': 'convert_all_notes',
    'view custom prompt': 'view_custom_prompt'
  };

  for (const [keyword, action] of Object.entries(actionMap)) {
    if (lower.includes(keyword)) return action;
  }

  return 'unknown';
};
```

**Action Availability by Type:**

| Action | Audio | Video | Mind Map | Reports | Quiz | Note |
|--------|-------|-------|----------|---------|------|------|
| Rename | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| Delete | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Download | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ |
| Share | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| Export to Docs | ❌ | ❌ | ❌ | ✅ | ❌ | ✅ |
| Export to Sheets | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Convert to Source | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |

---

## Complete Discovery Algorithm

```javascript
/**
 * Complete Studio Panel discovery function
 * Returns comprehensive metadata about all artifact types and capabilities
 */
async function discoverStudioPanel() {
  const discovery = {
    timestamp: new Date().toISOString(),
    artifactTypes: [],
    generatedArtifacts: [],
    noteInterface: null
  };

  // === PHASE 1: Artifact Type Buttons ===
  const buttons = discoverArtifactButtons();

  for (const button of buttons) {
    const artifactType = {
      name: button.name,
      customizable: button.hasEditIcon,
      pattern: detectCreationPattern(button.name, button.hasEditIcon).pattern,
      customization_fields: []
    };

    // === PHASE 2: Customization Discovery ===
    if (button.hasEditIcon && button.name !== 'Reports') {
      // Pattern 1: Direct customization
      const dialogResult = await openCustomizationDialog(button.element);

      if (dialogResult.success) {
        const fields = captureCustomizationFields(dialogResult.dialog);
        artifactType.customization_fields = structureFieldMetadata(fields).customization_fields;

        // Close dialog
        const closeButton = dialogResult.dialog.querySelector('button[aria-label*="Close"]');
        closeButton?.click();
        await waitFor(500);
      }
    }

    if (button.name === 'Reports') {
      // Pattern 2: Multi-step Reports
      const reportDialog = await openReportsDialog();

      if (reportDialog) {
        const formats = discoverReportFormats(reportDialog);
        artifactType.report_formats = formats;

        // Sample one format (e.g., Briefing Doc)
        if (formats.length > 0 && formats[0].hasCustomization) {
          const formatDialog = await openFormatCustomization(formats[0].element);

          if (formatDialog.success) {
            const fields = captureCustomizationFields(formatDialog.dialog);
            artifactType.sample_format_fields = structureFieldMetadata(fields).customization_fields;

            // Close dialogs
            const closeButton = formatDialog.dialog.querySelector('button[aria-label*="Close"]');
            closeButton?.click();
            await waitFor(500);
          }
        }

        // Close report selection dialog
        const closeButton = reportDialog.querySelector('button[aria-label*="Close"]');
        closeButton?.click();
        await waitFor(500);
      }
    }

    discovery.artifactTypes.push(artifactType);
  }

  // === PHASE 3: Note Discovery ===
  const addNoteButton = findAddNoteButton();
  if (addNoteButton) {
    const noteResult = await createNote();

    if (noteResult.success) {
      discovery.noteInterface = discoverNoteInterface();

      // Close note editor
      const closeButton = document.querySelector('button[aria-label*="Close"], button:has(mat-icon:innerText("close"))');
      closeButton?.click();
      await waitFor(500);
    }
  }

  // === PHASE 4: Generated Artifacts ===
  const library = discoverArtifactLibrary();

  if (library.found) {
    for (const artifactRow of library.artifacts.slice(0, 5)) { // Sample first 5
      const info = extractArtifactInfo(artifactRow);

      // Discover actions for this artifact
      const menuResult = await openArtifactMenu(artifactRow);

      if (menuResult.found) {
        info.actions = discoverArtifactActions(menuResult.menu);

        // Close menu
        document.body.click(); // Click outside to close
        await waitFor(300);
      }

      discovery.generatedArtifacts.push(info);
    }
  }

  return discovery;
}
```

---

## Validation Results

### Session Date: 2026-01-01

All artifact types were validated against `config/artifact_types_fallback.json` with **100% accuracy**.

#### Validated Artifacts

1. **✅ Audio Overview** - Perfect match
   - Format: 4 card options (Deep Dive, Brief, Critique, Debate)
   - Language: Dropdown (English default)
   - Length: 3 radio options (Short, Default, Long)
   - Focus: Textarea (optional)

2. **✅ Video Overview** - Perfect match
   - Format: 2 card options (Explainer, Brief)
   - Language: Dropdown
   - Visual Style: 6 thumbnail options
   - Focus: Textarea (optional)

3. **✅ Quiz** - Perfect match
   - Number of Questions: 3 radio options
   - Difficulty: 3 radio options
   - Topic: Textarea (optional)

4. **✅ Flashcards** - Perfect match
   - Number of Cards: 3 radio options
   - Difficulty: 3 radio options
   - Topic: Textarea (optional)

5. **✅ Infographic** - Perfect match
   - Language: Dropdown
   - Orientation: 3 radio options
   - Level of Detail: 3 radio options
   - Description: Textarea (optional)

6. **✅ Slide Deck** - Perfect match
   - Format: 2 card options
   - Language: Dropdown
   - Length: 2 radio options
   - Description: Textarea (optional)

7. **✅ Data Table** - Perfect match
   - Language: Dropdown
   - Description: Textarea (optional)

8. **✅ Reports (Briefing Doc)** - Perfect match
   - Language: Dropdown
   - Description: Textarea with default value

9. **✅ Note** - Perfect match
   - No customization fields
   - Manual creation via "Add note" button
   - Direct editor interface
   - Convert to source capability

#### Discrepancies Found

**NONE** - All configurations in `config/artifact_types_fallback.json` are accurate and up-to-date as of 2026-01-01.

---

## Key Learnings

### 1. Edit Icon vs Full Button Click

**Critical distinction:**
- ✅ Click **edit icon** (.option-icon) → Opens customization dialog
- ❌ Click **entire button** → Triggers immediate generation without customization

This is the most common mistake in automation.

### 2. Reports Special Handling

Reports requires a two-step process:
1. Click Reports button → Opens format selection
2. Click format's edit icon → Opens customization for that format

Each report format (Briefing Doc, Study Guide, etc.) has its own customization fields.

### 3. Field Type Detection

Five field types identified:
1. **card_selector**: Format cards with checkmarks
2. **dropdown**: Language/option selection
3. **radio**: Button groups with single selection
4. **textarea**: Multi-line text input for descriptions/focus
5. **thumbnail_selector**: Visual style selection (Video Overview)

### 4. Dialog Waiting

Always wait for `mat-dialog-container` to appear after clicking:
- 1000ms is usually sufficient
- Use retry logic with timeout for robustness
- Check both presence and visibility

### 5. Menu Closing

Artifact action menus can be closed by:
- Clicking outside the menu
- Pressing Escape key
- Clicking a menu item (executes action)

---

## Automation Best Practices

### 1. Element Targeting

```javascript
// ✅ Good: Target edit icon specifically
const editIcon = button.querySelector('.option-icon');
const rect = editIcon.getBoundingClientRect();
// Click at center of edit icon

// ❌ Bad: Click entire button
button.click(); // This triggers generation
```

### 2. Error Recovery

```javascript
// ✅ Good: Handle missing elements gracefully
const openCustomization = async (button) => {
  const editIcon = button.querySelector('.option-icon');

  if (!editIcon) {
    return {
      success: false,
      reason: 'not_customizable',
      artifact: button.innerText
    };
  }

  // Proceed with opening...
};
```

### 3. Validation

```javascript
// ✅ Good: Validate dialog appeared before proceeding
const dialog = await waitForDialog();

if (!dialog) {
  throw new Error('Customization dialog did not appear');
}

// Now safe to interact with dialog
```

---

**End of Studio Panel Discovery Documentation**
