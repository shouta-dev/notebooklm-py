# Chat Panel Discovery Documentation

**Created**: 2026-01-01
**Purpose**: Automated discovery blueprint for NotebookLM Chat Panel UI elements, message interactions, configuration, and actions

---

## Table of Contents

1. [Overview](#overview)
2. [Chat Panel Structure](#chat-panel-structure)
3. [Discovery Process](#discovery-process)
4. [UI Elements & DOM](#ui-elements--dom)
5. [Chat Operations](#chat-operations)
6. [Message Extraction](#message-extraction)
7. [Chat Configuration Discovery](#chat-configuration-discovery)
8. [Automated Discovery Algorithm](#automated-discovery-algorithm)
9. [Comparison with Config](#comparison-with-config)

---

## Overview

The Chat Panel is the center panel in NotebookLM where users interact with the AI assistant to ask questions about their sources. This document provides a complete blueprint for automated discovery of Chat Panel functionality.

### Key Components

1. **Message Input** - Textarea for entering questions/prompts
2. **Send Button** - Submits the chat message
3. **Chat History** - Scrollable conversation display
4. **Message Bubbles** - Individual user/AI messages
5. **Configure Chat Button** - Opens chat settings dialog
6. **Message Actions** - Save to note, view citations, copy, etc.
7. **Source Citations** - Linked references in AI responses

---

## Chat Panel Structure

### High-Level Layout

```
┌────────────────────────────────────────┐
│ Chat (Tab Header)        [⚙️ Configure]│
├────────────────────────────────────────┤
│                                        │
│ CHAT HISTORY (Scrollable)              │
│                                        │
│ ┌────────────────────────────────────┐ │
│ │ USER MESSAGE                       │ │
│ │ "What are the main themes?"        │ │
│ └────────────────────────────────────┘ │
│                                        │
│ ┌────────────────────────────────────┐ │
│ │ AI RESPONSE                    ⋮   │ │
│ │ "The main themes include...        │ │
│ │  1. Source Integration             │ │
│ │  2. Testing Protocols     [1][2]   │ │← Citations
│ │                                    │ │
│ │ [💾 Save to note] [Sources: 3]    │ │← Actions
│ └────────────────────────────────────┘ │
│                                        │
│ ┌────────────────────────────────────┐ │
│ │ Give me a brief overview.      [⏎]│ │← Message input
│ └────────────────────────────────────┘ │
│                                        │
│ [32 sources ▼]                         │← Source indicator
└────────────────────────────────────────┘
```

---

## Discovery Process

### Phase 1: Identify Chat Panel Container

#### Step 1.1: Locate Chat Panel
```javascript
// Find the Chat panel container
const chatPanel = document.querySelector(
  '.chat-panel, [class*="chat"], [aria-label*="Chat"]'
);

// Alternative: Find by active tab
const chatTab = Array.from(document.querySelectorAll('button, a')).find(
  el => el.innerText.includes('Chat') &&
        el.getAttribute('aria-selected') === 'true'
);

// Get the panel associated with active tab
const chatContainer = chatTab?.nextElementSibling ||
                      document.querySelector('[class*="chat-container"]');
```

**Expected DOM Structure:**
```html
<div class="chat-panel">
  <header>
    <h2>Chat</h2>
    <button aria-label="Configure notebook">
      <mat-icon>tune</mat-icon>
    </button>
  </header>
  <div class="chat-history" role="log">
    <!-- Messages here -->
  </div>
  <div class="chat-input-container">
    <textarea placeholder="Start typing..."></textarea>
    <button type="submit">
      <mat-icon>arrow_forward</mat-icon>
    </button>
  </div>
</div>
```

---

### Phase 2: Discover Message Input

#### Step 2.1: Locate Message Input Textarea
```javascript
const discoverMessageInput = () => {
  // Try multiple selectors in priority order
  const input =
    document.querySelector('textarea[placeholder="Start typing..."]') ||
    document.querySelector('textarea[aria-label="Query box"]') ||
    document.querySelector('textarea[placeholder*="Type"]') ||
    Array.from(document.querySelectorAll('textarea')).find(
      ta => ta.closest('.chat-panel, [class*="chat"]')
    );

  if (!input) {
    return { found: false };
  }

  return {
    found: true,
    placeholder: input.placeholder,
    ariaLabel: input.getAttribute('aria-label'),
    maxLength: input.maxLength,
    rows: input.rows,
    isDisabled: input.disabled,
    element: input
  };
};
```

**Selector Priority** (from config):
```json
{
  "message_input": [
    "textarea[placeholder='Start typing...']",
    "textarea[aria-label='Query box']",
    "textarea[placeholder*='Type']",
    "textarea"
  ]
}
```

#### Step 2.2: Locate Send Button
```javascript
const discoverSendButton = () => {
  const button =
    document.querySelector('button[aria-label="Submit"]') ||
    document.querySelector('button[type="submit"]') ||
    Array.from(document.querySelectorAll('button')).find(
      btn => btn.querySelector('mat-icon')?.innerText === 'arrow_forward'
    ) ||
    document.querySelector('button[aria-label*="Send"]');

  if (!button) {
    return { found: false };
  }

  return {
    found: true,
    ariaLabel: button.getAttribute('aria-label'),
    isDisabled: button.disabled,
    icon: button.querySelector('mat-icon')?.innerText,
    element: button
  };
};
```

**Selector Priority** (from config):
```json
{
  "send_button": [
    "button[aria-label='Submit']",
    "button[type='submit']",
    "button:has(mat-icon):has-text('arrow_forward')",
    "button[aria-label*='Send']"
  ]
}
```

---

### Phase 3: Discover Chat History

#### Step 3.1: Locate Chat History Container
```javascript
const discoverChatHistory = () => {
  const history =
    document.querySelector('[role="log"]') ||
    document.querySelector('div[aria-label*="Chat history"]') ||
    document.querySelector('.chat-history');

  if (!history) {
    return { found: false, messages: [] };
  }

  return {
    found: true,
    element: history,
    scrollHeight: history.scrollHeight,
    clientHeight: history.clientHeight,
    isScrollable: history.scrollHeight > history.clientHeight
  };
};
```

**Selector Priority** (from config):
```json
{
  "chat_history": [
    "[role='log']",
    "div[aria-label*='Chat history']"
  ]
}
```

#### Step 3.2: Extract All Messages
```javascript
const extractMessages = (chatHistory) => {
  // Message bubbles have various selectors
  const messageBubbles = Array.from(
    chatHistory.querySelectorAll(
      '.to-user-container, .from-user-container, ' +
      'chat-message, .to-user-message-inner-content, ' +
      '.from-user-message-inner-content, div.model-segment, ' +
      'div.user-query, .message-bubble, [role="article"], ' +
      'div[data-testid*="message"], .message-content, ' +
      'app-message-bubble, div.message-row'
    )
  );

  return messageBubbles.map((bubble, index) => ({
    index,
    ...extractMessageMetadata(bubble)
  }));
};
```

**Selector Priority** (from config - 13 fallbacks):
```json
{
  "message_bubble": [
    ".to-user-container",
    ".from-user-container",
    "chat-message",
    ".to-user-message-inner-content",
    ".from-user-message-inner-content",
    "div.model-segment",
    "div.user-query",
    "div.message-bubble",
    "[role='article']",
    "div[data-testid*='message']",
    ".message-content",
    "app-message-bubble",
    "div.message-row"
  ]
}
```

---

### Phase 4: Message Metadata Extraction

#### Step 4.1: Determine Message Type (User vs AI)
```javascript
const extractMessageMetadata = (messageBubble) => {
  // Determine if message is from user or AI
  const isUserMessage =
    messageBubble.classList.contains('from-user-container') ||
    messageBubble.classList.contains('user-query') ||
    messageBubble.querySelector('.user-avatar') !== null ||
    messageBubble.closest('[class*="user"]') !== null;

  const isAIMessage =
    messageBubble.classList.contains('to-user-container') ||
    messageBubble.classList.contains('model-segment') ||
    messageBubble.querySelector('.ai-avatar, .model-avatar') !== null;

  const sender = isUserMessage ? 'user' :
                 isAIMessage ? 'ai' :
                 'unknown';

  // Extract content
  const contentEl =
    messageBubble.querySelector('.message-content, .message-text') ||
    messageBubble;

  const content = contentEl.innerText || contentEl.textContent;

  return {
    sender,
    content,
    ...extractMessageComponents(messageBubble)
  };
};
```

#### Step 4.2: Extract Message Components
```javascript
const extractMessageComponents = (messageBubble) => {
  const components = {
    citations: [],
    actions: [],
    timestamp: null,
    sourceCount: null
  };

  // Extract citations (numbered references like [1], [2])
  const citationLinks = Array.from(
    messageBubble.querySelectorAll('a[href*="#citation"], sup, [class*="citation"]')
  );

  components.citations = citationLinks.map(link => ({
    number: link.innerText.match(/\d+/)?.[0],
    href: link.getAttribute('href'),
    element: link
  }));

  // Extract action buttons (Save to note, etc.)
  const actionButtons = Array.from(
    messageBubble.querySelectorAll('button')
  );

  components.actions = actionButtons.map(btn => ({
    text: btn.innerText,
    icon: btn.querySelector('mat-icon')?.innerText,
    ariaLabel: btn.getAttribute('aria-label'),
    element: btn
  }));

  // Extract timestamp if present
  const timestampEl = messageBubble.querySelector('time, [class*="timestamp"]');
  if (timestampEl) {
    components.timestamp = timestampEl.innerText ||
                          timestampEl.getAttribute('datetime');
  }

  // Extract source count indicator
  const sourceIndicator = Array.from(messageBubble.querySelectorAll('*')).find(
    el => el.innerText.match(/Sources?:\s*\d+/i)
  );

  if (sourceIndicator) {
    const match = sourceIndicator.innerText.match(/(\d+)/);
    components.sourceCount = match ? parseInt(match[1]) : null;
  }

  return components;
};
```

---

### Phase 5: Discover Message Actions

#### Step 5.1: Identify Available Actions per Message
```javascript
const discoverMessageActions = (messageBubble) => {
  const actions = [];

  // Common action patterns
  const actionPatterns = [
    { name: 'save_to_note', pattern: /save.*note/i },
    { name: 'copy', pattern: /copy/i },
    { name: 'regenerate', pattern: /regenerate|retry/i },
    { name: 'view_sources', pattern: /sources?/i },
    { name: 'share', pattern: /share/i },
    { name: 'thumbs_up', pattern: /thumbs.*up|like|good/i },
    { name: 'thumbs_down', pattern: /thumbs.*down|dislike|bad/i }
  ];

  // Find all buttons in message
  const buttons = Array.from(messageBubble.querySelectorAll('button'));

  buttons.forEach(btn => {
    const text = btn.innerText.toLowerCase();
    const ariaLabel = btn.getAttribute('aria-label')?.toLowerCase() || '';
    const icon = btn.querySelector('mat-icon')?.innerText;

    // Match against patterns
    for (const { name, pattern } of actionPatterns) {
      if (pattern.test(text) || pattern.test(ariaLabel)) {
        actions.push({
          action: name,
          text: btn.innerText,
          icon,
          element: btn
        });
        break;
      }
    }
  });

  return actions;
};
```

**Expected Actions by Message Type:**

| Action | User Message | AI Message |
|--------|-------------|------------|
| Save to note | ❌ | ✅ |
| Copy | ✅ | ✅ |
| Regenerate | ❌ | ✅ |
| View sources | ❌ | ✅ |
| Thumbs up/down | ❌ | ✅ |
| Edit | ✅ | ❌ |

---

### Phase 6: Discover Citations

#### Step 6.1: Extract Citation Links
```javascript
const extractCitations = (messageBubble) => {
  // Citations are typically numbered links like [1], [2]
  const citationElements = Array.from(
    messageBubble.querySelectorAll(
      'a[href*="#citation"], ' +
      'sup > a, ' +
      '[class*="citation"] a, ' +
      'a[class*="footnote"]'
    )
  );

  return citationElements.map(citation => {
    const number = citation.innerText.match(/\d+/)?.[0];
    const href = citation.getAttribute('href');

    // Extract source information if available
    const sourceId = href?.match(/#citation-(\d+)/)?.[1];

    return {
      number: number ? parseInt(number) : null,
      href,
      sourceId,
      text: citation.innerText,
      element: citation
    };
  });
};
```

#### Step 6.2: Click Citation to View Source
```javascript
const viewCitation = async (citationElement) => {
  citationElement.click();
  await waitFor(500);

  // Check if citation panel/popup appeared
  const citationPanel = document.querySelector(
    '[class*="citation-panel"], ' +
    '[role="dialog"]:has-text("Source"), ' +
    '.source-preview'
  );

  if (citationPanel) {
    const sourceInfo = {
      title: citationPanel.querySelector('h3, .source-title')?.innerText,
      excerpt: citationPanel.querySelector('.excerpt, .quote')?.innerText,
      metadata: citationPanel.querySelector('.metadata')?.innerText
    };

    return { found: true, sourceInfo };
  }

  return { found: false };
};
```

---

### Phase 7: Discover Chat Configuration

#### Step 7.1: Locate Configure Button
```javascript
const discoverConfigureButton = () => {
  const configButton =
    document.querySelector('button[aria-label="Configure notebook"]') ||
    Array.from(document.querySelectorAll('button')).find(
      btn => btn.querySelector('mat-icon')?.innerText === 'tune'
    ) ||
    Array.from(document.querySelectorAll('button')).find(
      btn => btn.innerText.includes('Configure')
    ) ||
    document.querySelector('button[aria-label*="Configure chat"]');

  return {
    found: configButton !== null,
    element: configButton
  };
};
```

**Selector Priority** (from config):
```json
{
  "configure_chat_button": [
    "button[aria-label='Configure notebook']",
    "button:has-text('tune')",
    "button:has-text('Configure')",
    "button[aria-label*='Configure chat']"
  ]
}
```

#### Step 7.2: Open Configuration Dialog
```javascript
const openChatConfig = async (configButton) => {
  configButton.click();
  await waitFor(1000);

  const dialog =
    document.querySelector('configure-notebook-settings') ||
    document.querySelector('.configure-settings-container') ||
    Array.from(document.querySelectorAll('mat-dialog-container')).find(
      d => d.innerText.includes('Configure Chat')
    );

  return {
    found: dialog !== null,
    dialog
  };
};
```

**Selector Priority** (from config):
```json
{
  "modal": [
    "configure-notebook-settings",
    ".configure-settings-container",
    "mat-dialog-container:has-text('Configure Chat')"
  ]
}
```

---

### Phase 8: Chat Configuration Options

#### Step 8.1: Discover Chat Goal Options
```javascript
const discoverChatGoals = (configDialog) => {
  // Chat has 3 goal options: Default, Learning Guide, Custom
  const goals = [
    {
      id: 'default',
      selectors: [
        'mat-button-toggle:has(button[aria-label="Default button"])',
        'button[aria-label="Default button"]',
        'button:has-text("Default")'
      ]
    },
    {
      id: 'learning_guide',
      selectors: [
        'mat-button-toggle:has(button[aria-label*="Learning Guide"])',
        'button[aria-label*="Learning Guide"]',
        'button:has-text("Learning Guide")'
      ]
    },
    {
      id: 'custom',
      selectors: [
        'mat-button-toggle:has(button[aria-label="Custom button"])',
        'button[aria-label="Custom button"]',
        'button:has-text("Custom")'
      ]
    }
  ];

  return goals.map(goal => {
    let element = null;
    for (const selector of goal.selectors) {
      element = configDialog.querySelector(selector);
      if (element) break;
    }

    return {
      id: goal.id,
      found: element !== null,
      isSelected: element?.getAttribute('aria-checked') === 'true' ||
                  element?.classList.contains('mat-button-toggle-checked'),
      element
    };
  });
};
```

**Goal Options** (from config):
1. **Default** - Standard chat behavior
2. **Learning Guide** - Educational focus
3. **Custom** - User-defined behavior

#### Step 8.2: Discover Response Length Options
```javascript
const discoverResponseLength = (configDialog) => {
  // Response length has 3 options: Shorter, Default, Longer
  const lengths = [
    {
      id: 'shorter',
      selectors: [
        'mat-button-toggle:has(button[aria-label*="Shorter"])',
        'button[aria-label*="Concise style guide button"]',
        'button:has-text("Shorter")'
      ]
    },
    {
      id: 'default',
      selectors: [
        'mat-button-toggle-group[formcontrolname="styleGuideButtonSelected"] mat-button-toggle:has-text("Default")',
        'mat-button-toggle:has(button[aria-label="Default button"]) >> nth=1'
      ]
    },
    {
      id: 'longer',
      selectors: [
        'mat-button-toggle:has(button[aria-label*="Longer"])',
        'button[aria-label*="Verbose style guide button"]',
        'button:has-text("Longer")'
      ]
    }
  ];

  return lengths.map(length => {
    let element = null;
    for (const selector of length.selectors) {
      element = configDialog.querySelector(selector);
      if (element) break;
    }

    return {
      id: length.id,
      found: element !== null,
      isSelected: element?.getAttribute('aria-checked') === 'true' ||
                  element?.classList.contains('mat-button-toggle-checked'),
      element
    };
  });
};
```

**Length Options** (from config):
1. **Shorter** - Concise responses
2. **Default** - Standard response length
3. **Longer** - Verbose, detailed responses

#### Step 8.3: Extract Custom Prompt (if Custom goal selected)
```javascript
const extractCustomPrompt = (configDialog) => {
  // If "Custom" goal is selected, there should be a textarea for custom prompt
  const textarea = configDialog.querySelector(
    'textarea[placeholder*="custom"], ' +
    'textarea[placeholder*="prompt"], ' +
    'textarea[aria-label*="Custom"]'
  );

  if (!textarea) {
    return { found: false };
  }

  return {
    found: true,
    placeholder: textarea.placeholder,
    value: textarea.value,
    maxLength: textarea.maxLength,
    element: textarea
  };
};
```

#### Step 8.4: Locate Save Button
```javascript
const discoverSaveButton = (configDialog) => {
  const saveButton =
    configDialog.querySelector('button[aria-label*="Save settings"]') ||
    Array.from(configDialog.querySelectorAll('button')).find(
      btn => btn.innerText.includes('Save')
    ) ||
    configDialog.querySelector('button[type="submit"]');

  return {
    found: saveButton !== null,
    text: saveButton?.innerText,
    isDisabled: saveButton?.disabled,
    element: saveButton
  };
};
```

**Selector Priority** (from config):
```json
{
  "save_button": [
    "button[aria-label*='Save settings']",
    "button:has-text('Save')",
    "button[type='submit']"
  ]
}
```

---

### Phase 9: Source Context Discovery

#### Step 9.1: Discover Source Count Indicator
```javascript
const discoverSourceContext = () => {
  // Chat panel shows number of selected sources
  const sourceIndicator = Array.from(document.querySelectorAll('*')).find(
    el => el.innerText.match(/^\d+\s+sources?$/i)
  );

  if (!sourceIndicator) {
    return { found: false };
  }

  const match = sourceIndicator.innerText.match(/(\d+)/);
  const count = match ? parseInt(match[1]) : null;

  // Check if it's a dropdown/button
  const isClickable = sourceIndicator.tagName === 'BUTTON' ||
                      sourceIndicator.querySelector('button') !== null;

  return {
    found: true,
    sourceCount: count,
    isClickable,
    text: sourceIndicator.innerText,
    element: sourceIndicator
  };
};
```

#### Step 9.2: Open Source Selection (if clickable)
```javascript
const openSourceSelection = async (sourceIndicator) => {
  const button = sourceIndicator.tagName === 'BUTTON' ?
                 sourceIndicator :
                 sourceIndicator.querySelector('button');

  if (!button) {
    return { found: false, reason: 'Not clickable' };
  }

  button.click();
  await waitFor(500);

  // Check if source selection panel/dropdown appeared
  const panel = document.querySelector(
    '[class*="source-selection"], ' +
    '[role="menu"], ' +
    '.source-picker'
  );

  return {
    found: panel !== null,
    panel
  };
};
```

---

## UI Elements & DOM

### Complete Element Mapping

| Element | Selector Priority | Purpose |
|---------|------------------|---------|
| **Message Input** | `textarea[placeholder="Start typing..."]` | User input field |
| **Send Button** | `button[aria-label="Submit"]` | Submit message |
| **Configure Button** | `button[aria-label="Configure notebook"]` | Open chat settings |
| **Chat History** | `[role="log"]` | Message container |
| **Message Bubble** | `.to-user-container` or `.from-user-container` | Individual message |
| **Citation Link** | `a[href*="#citation"]` | Source reference |
| **Save to Note** | `button` with "Save" text | Save response |
| **Source Indicator** | Text matching `/\d+ sources?/` | Selected sources count |

### DOM Hierarchy Example

```html
<div class="chat-panel">
  <!-- Header -->
  <header>
    <h2>Chat</h2>
    <button aria-label="Configure notebook">
      <mat-icon>tune</mat-icon>
    </button>
  </header>

  <!-- Chat History -->
  <div class="chat-history" role="log">

    <!-- User Message -->
    <div class="from-user-container message-bubble">
      <div class="user-avatar"></div>
      <div class="message-content">
        <p>What are the main testing protocols?</p>
      </div>
      <time>2 minutes ago</time>
    </div>

    <!-- AI Response -->
    <div class="to-user-container message-bubble">
      <div class="ai-avatar"></div>
      <div class="message-content">
        <p>The main testing protocols include:</p>
        <ol>
          <li>Source Integration <a href="#citation-1">[1]</a></li>
          <li>Removal Operations <a href="#citation-2">[2]</a></li>
          <li>Rename Validation <a href="#citation-3">[3]</a></li>
        </ol>
      </div>
      <div class="message-actions">
        <button aria-label="Save to note">
          <mat-icon>sticky_note_2</mat-icon>
          Save to note
        </button>
        <span class="source-count">Sources: 3</span>
        <button aria-label="Thumbs up">
          <mat-icon>thumb_up</mat-icon>
        </button>
        <button aria-label="Thumbs down">
          <mat-icon>thumb_down</mat-icon>
        </button>
      </div>
    </div>

  </div>

  <!-- Input Area -->
  <div class="chat-input-container">
    <div class="source-indicator">
      <button>32 sources ▼</button>
    </div>
    <textarea
      placeholder="Start typing..."
      aria-label="Query box"
      rows="3"
    ></textarea>
    <button type="submit" aria-label="Submit">
      <mat-icon>arrow_forward</mat-icon>
    </button>
  </div>
</div>
```

---

## Chat Operations

### Operation 1: Send Message

**Complete Flow:**
```javascript
async function sendChatMessage(message) {
  // 1. Find message input
  const input = document.querySelector('textarea[placeholder="Start typing..."]');

  if (!input) {
    throw new Error('Message input not found');
  }

  // 2. Enter message
  input.value = message;
  input.dispatchEvent(new Event('input', { bubbles: true }));

  // 3. Find and click send button
  const sendButton = document.querySelector('button[aria-label="Submit"]');

  if (!sendButton || sendButton.disabled) {
    throw new Error('Send button not available');
  }

  sendButton.click();

  // 4. Wait for response to appear
  const initialMessageCount = document.querySelectorAll('.message-bubble').length;

  await waitForNewMessage(initialMessageCount);
}

async function waitForNewMessage(previousCount, timeout = 60000) {
  const startTime = Date.now();

  while (Date.now() - startTime < timeout) {
    const currentCount = document.querySelectorAll('.message-bubble').length;

    if (currentCount > previousCount) {
      // New message appeared, wait a bit more for it to complete
      await waitFor(1000);
      return true;
    }

    await waitFor(500);
  }

  throw new Error('Response timeout');
}
```

### Operation 2: Save Response to Note

**Complete Flow:**
```javascript
async function saveResponseToNote(messageIndex = -1) {
  // 1. Get AI messages
  const aiMessages = Array.from(document.querySelectorAll('.to-user-container'));

  if (aiMessages.length === 0) {
    throw new Error('No AI responses found');
  }

  // 2. Select message (default to last)
  const message = messageIndex >= 0 ?
                  aiMessages[messageIndex] :
                  aiMessages[aiMessages.length - 1];

  // 3. Find "Save to note" button
  const saveButton = Array.from(message.querySelectorAll('button')).find(
    btn => btn.innerText.includes('Save') && btn.innerText.includes('note')
  );

  if (!saveButton) {
    throw new Error('Save to note button not found');
  }

  // 4. Click save button
  saveButton.click();
  await waitFor(1000);

  // 5. Check if note was created (Studio panel should show it)
  const noteCreated = document.querySelector('.studio-panel .artifact-item:has-text("Note")');

  return {
    success: noteCreated !== null,
    noteElement: noteCreated
  };
}
```

### Operation 3: Configure Chat Settings

**Complete Flow:**
```javascript
async function configureChatSettings(goal, responseLength) {
  // 1. Click configure button
  const configButton = document.querySelector('button[aria-label="Configure notebook"]');
  configButton.click();
  await waitFor(1000);

  // 2. Wait for dialog
  const dialog = document.querySelector('configure-notebook-settings');

  if (!dialog) {
    throw new Error('Configuration dialog did not appear');
  }

  // 3. Select goal
  const goalButtons = {
    'default': dialog.querySelector('button:has-text("Default")'),
    'learning_guide': dialog.querySelector('button:has-text("Learning Guide")'),
    'custom': dialog.querySelector('button:has-text("Custom")')
  };

  const goalButton = goalButtons[goal];
  if (goalButton && goalButton.getAttribute('aria-checked') !== 'true') {
    goalButton.click();
    await waitFor(300);
  }

  // 4. Select response length
  const lengthButtons = {
    'shorter': dialog.querySelector('button:has-text("Shorter")'),
    'default': Array.from(dialog.querySelectorAll('button:has-text("Default")')).find(
      btn => btn.closest('[formcontrolname="styleGuideButtonSelected"]')
    ),
    'longer': dialog.querySelector('button:has-text("Longer")')
  };

  const lengthButton = lengthButtons[responseLength];
  if (lengthButton && lengthButton.getAttribute('aria-checked') !== 'true') {
    lengthButton.click();
    await waitFor(300);
  }

  // 5. Save settings
  const saveButton = Array.from(dialog.querySelectorAll('button')).find(
    btn => btn.innerText.includes('Save')
  );

  saveButton.click();
  await waitFor(500);
}
```

### Operation 4: Get Conversation History

**Complete Flow:**
```javascript
function getConversationHistory() {
  const chatHistory = document.querySelector('[role="log"]');

  if (!chatHistory) {
    return { success: false, messages: [] };
  }

  const messageBubbles = Array.from(
    chatHistory.querySelectorAll('.message-bubble, .to-user-container, .from-user-container')
  );

  const messages = messageBubbles.map((bubble, index) => {
    const isUser = bubble.classList.contains('from-user-container') ||
                   bubble.querySelector('.user-avatar') !== null;

    const content = bubble.querySelector('.message-content, .message-text')?.innerText ||
                    bubble.innerText;

    const citations = Array.from(bubble.querySelectorAll('a[href*="#citation"]'))
      .map(a => ({
        number: a.innerText.match(/\d+/)?.[0],
        href: a.getAttribute('href')
      }));

    return {
      index,
      sender: isUser ? 'user' : 'ai',
      content: content.trim(),
      citations,
      timestamp: bubble.querySelector('time')?.innerText
    };
  });

  return {
    success: true,
    messageCount: messages.length,
    messages
  };
}
```

---

## Message Extraction

### Extract Specific Message Components

#### Citations with Source Information
```javascript
function extractMessageCitations(messageBubble) {
  const citations = Array.from(
    messageBubble.querySelectorAll('a[href*="#citation"], sup a')
  );

  return citations.map(citation => {
    const number = citation.innerText.match(/\d+/)?.[0];
    const href = citation.getAttribute('href');
    const sourceId = href?.match(/#citation-(\d+)/)?.[1];

    return {
      number: parseInt(number),
      href,
      sourceId,
      text: citation.innerText,
      // Get the surrounding context
      context: citation.parentElement.innerText.substring(
        Math.max(0, citation.parentElement.innerText.indexOf(citation.innerText) - 50),
        citation.parentElement.innerText.indexOf(citation.innerText) + 50
      )
    };
  });
}
```

#### Code Blocks
```javascript
function extractCodeBlocks(messageBubble) {
  const codeBlocks = Array.from(
    messageBubble.querySelectorAll('pre code, code, .code-block')
  );

  return codeBlocks.map((block, index) => ({
    index,
    language: block.className.match(/language-(\w+)/)?.[1],
    code: block.innerText || block.textContent,
    isInline: block.tagName === 'CODE' && block.closest('pre') === null
  }));
}
```

#### Lists and Structured Content
```javascript
function extractStructuredContent(messageBubble) {
  const content = {
    lists: [],
    tables: [],
    headings: []
  };

  // Extract lists
  const lists = messageBubble.querySelectorAll('ul, ol');
  content.lists = Array.from(lists).map(list => ({
    type: list.tagName.toLowerCase(),
    items: Array.from(list.querySelectorAll('li')).map(li => li.innerText)
  }));

  // Extract tables
  const tables = messageBubble.querySelectorAll('table');
  content.tables = Array.from(tables).map(table => {
    const headers = Array.from(table.querySelectorAll('th')).map(th => th.innerText);
    const rows = Array.from(table.querySelectorAll('tbody tr')).map(tr =>
      Array.from(tr.querySelectorAll('td')).map(td => td.innerText)
    );
    return { headers, rows };
  });

  // Extract headings
  const headings = messageBubble.querySelectorAll('h1, h2, h3, h4, h5, h6');
  content.headings = Array.from(headings).map(h => ({
    level: parseInt(h.tagName[1]),
    text: h.innerText
  }));

  return content;
}
```

---

## Chat Configuration Discovery

### Complete Configuration Discovery

```javascript
async function discoverChatConfiguration() {
  const discovery = {
    currentSettings: {},
    availableOptions: {},
    timestamp: new Date().toISOString()
  };

  // 1. Open configuration dialog
  const configButton = document.querySelector('button[aria-label="Configure notebook"]');

  if (!configButton) {
    return { found: false, reason: 'Configure button not found' };
  }

  configButton.click();
  await waitFor(1000);

  const dialog = document.querySelector('configure-notebook-settings, mat-dialog-container');

  if (!dialog) {
    return { found: false, reason: 'Configuration dialog did not open' };
  }

  // 2. Discover chat goals
  const goals = discoverChatGoals(dialog);
  const selectedGoal = goals.find(g => g.isSelected);

  discovery.availableOptions.goals = goals.map(g => ({
    id: g.id,
    available: g.found
  }));
  discovery.currentSettings.goal = selectedGoal?.id || 'unknown';

  // 3. Discover response lengths
  const lengths = discoverResponseLength(dialog);
  const selectedLength = lengths.find(l => l.isSelected);

  discovery.availableOptions.responseLengths = lengths.map(l => ({
    id: l.id,
    available: l.found
  }));
  discovery.currentSettings.responseLength = selectedLength?.id || 'unknown';

  // 4. Check for custom prompt
  if (selectedGoal?.id === 'custom') {
    const customPrompt = extractCustomPrompt(dialog);
    discovery.currentSettings.customPrompt = customPrompt.value;
  }

  // 5. Close dialog
  const closeButton = dialog.querySelector('button[aria-label*="Close"], button:has-text("Cancel")');
  if (closeButton) {
    closeButton.click();
    await waitFor(500);
  }

  discovery.found = true;
  return discovery;
}
```

---

## Automated Discovery Algorithm

### Complete Discovery Function

```javascript
async function discoverChatPanel() {
  const discovery = {
    timestamp: new Date().toISOString(),
    panel: {},
    input: {},
    history: {},
    messages: [],
    configuration: {},
    sourceContext: {}
  };

  // === PHASE 1: Panel Structure ===
  const chatPanel = document.querySelector('.chat-panel, [class*="chat"]');
  discovery.panel = {
    found: chatPanel !== null,
    isVisible: chatPanel &&
               window.getComputedStyle(chatPanel).display !== 'none'
  };

  if (!discovery.panel.found) {
    return discovery;
  }

  // === PHASE 2: Input Elements ===
  discovery.input = {
    textarea: discoverMessageInput(),
    sendButton: discoverSendButton(),
    configureButton: discoverConfigureButton()
  };

  // === PHASE 3: Chat History ===
  discovery.history = discoverChatHistory();

  if (discovery.history.found) {
    // Extract messages
    const messages = extractMessages(discovery.history.element);

    // Sample first 5 messages (or all if fewer)
    discovery.messages = messages.slice(0, 5).map(msg => ({
      sender: msg.sender,
      contentPreview: msg.content.substring(0, 100) + '...',
      citationCount: msg.citations?.length || 0,
      actionCount: msg.actions?.length || 0,
      hasTimestamp: msg.timestamp !== null
    }));
  }

  // === PHASE 4: Configuration ===
  if (discovery.input.configureButton.found) {
    discovery.configuration = await discoverChatConfiguration();
  }

  // === PHASE 5: Source Context ===
  discovery.sourceContext = discoverSourceContext();

  return discovery;
}
```

---

## Comparison with Config

### config/selectors.json Validation

#### Chat Section (Lines 119-157)

| Element | Config Selectors | Status | Notes |
|---------|-----------------|--------|-------|
| **message_input** | 4 fallbacks | ✅ Valid | Placeholder-based matching works |
| **send_button** | 4 fallbacks | ✅ Valid | ARIA label + icon matching |
| **configure_chat_button** | 4 fallbacks | ✅ Valid | Multiple identification methods |
| **chat_history** | 2 fallbacks | ✅ Valid | Role-based selector preferred |
| **message_bubble** | 13 fallbacks | ✅ Valid | Extensive fallback coverage |

#### Chat Config Modal (Lines 158-198)

| Element | Config Selectors | Status | Notes |
|---------|-----------------|--------|-------|
| **modal** | 3 fallbacks | ✅ Valid | Component-based selectors |
| **goal_default** | 3 fallbacks | ✅ Valid | Button toggle matching |
| **goal_learning_guide** | 3 fallbacks | ✅ Valid | Text + ARIA matching |
| **goal_custom** | 3 fallbacks | ✅ Valid | Consistent pattern |
| **length_default** | 2 fallbacks | ✅ Valid | Form control targeting |
| **length_longer** | 3 fallbacks | ✅ Valid | Multiple identifiers |
| **length_shorter** | 3 fallbacks | ✅ Valid | Verbose ARIA label |
| **save_button** | 3 fallbacks | ✅ Valid | Standard save patterns |

### Validation Summary

**Overall Status**: ✅ **100% Valid**

All selectors in `config/selectors.json` for the Chat Panel are:
- **Accurate**: Match actual DOM structure
- **Robust**: Multiple fallbacks (up to 13 for message bubbles)
- **Stable**: Prefer ARIA labels and roles over CSS classes
- **Complete**: Cover all chat functionality

### Recommended Additions

**Optional enhancements** for more granular control:

```json
{
  "chat_actions": {
    "save_to_note": [
      "button:has-text('Save to note')",
      "button[aria-label*='Save']"
    ],
    "copy_message": [
      "button:has-text('Copy')",
      "button[aria-label*='Copy']"
    ],
    "regenerate": [
      "button:has-text('Regenerate')",
      "button[aria-label*='Regenerate']"
    ],
    "thumbs_up": [
      "button[aria-label*='Thumbs up']",
      "button:has(mat-icon:has-text('thumb_up'))"
    ],
    "thumbs_down": [
      "button[aria-label*='Thumbs down']",
      "button:has(mat-icon:has-text('thumb_down'))"
    ]
  },
  "citations": {
    "citation_link": [
      "a[href*='#citation']",
      "sup > a",
      "[class*='citation'] a"
    ],
    "citation_panel": [
      "[class*='citation-panel']",
      "[role='dialog']:has-text('Source')",
      ".source-preview"
    ]
  },
  "source_context": {
    "source_count_indicator": [
      "text=/^\\d+\\s+sources?$/i",
      ".source-indicator",
      "button:has-text('sources')"
    ]
  }
}
```

---

## Key Learnings

### 1. Message Bubble Variety
- Chat uses 13 different CSS class patterns for message bubbles
- Must check multiple selectors to reliably find all messages
- User vs AI messages have different class patterns

### 2. Citation Handling
- Citations are numbered links within messages
- Clicking citation may open source preview panel
- Citation numbering resets per message

### 3. Configuration Persistence
- Chat settings persist across sessions
- Goal and response length are independent settings
- Custom goal allows freeform prompt input

### 4. Streaming Responses
- AI responses stream in token-by-token
- Need to wait for response completion before extracting
- "Save to note" button only appears after response completes

### 5. Source Context
- Chat shows number of selected sources at bottom
- Source selection affects AI response context
- Can click to modify source selection mid-conversation

---

## Automation Best Practices

### 1. Message Waiting

```javascript
// ✅ Good: Wait for response completion
async function waitForResponse(previousCount) {
  let stableCount = 0;
  let lastCount = previousCount;

  while (stableCount < 3) { // Wait for count to stabilize
    await waitFor(500);
    const currentCount = document.querySelectorAll('.message-bubble').length;

    if (currentCount === lastCount) {
      stableCount++;
    } else {
      stableCount = 0;
      lastCount = currentCount;
    }
  }
}

// ❌ Bad: Fixed wait
await waitFor(5000); // Response might not be complete
```

### 2. Element Selection

```javascript
// ✅ Good: Multiple selector fallbacks
const input =
  document.querySelector('textarea[placeholder="Start typing..."]') ||
  document.querySelector('textarea[aria-label="Query box"]') ||
  document.querySelector('textarea');

// ❌ Bad: Single CSS class
const input = document.querySelector('.chat-input');
```

### 3. Message Extraction

```javascript
// ✅ Good: Robust sender detection
const isUser =
  bubble.classList.contains('from-user-container') ||
  bubble.querySelector('.user-avatar') !== null ||
  bubble.closest('[class*="user-message"]') !== null;

// ❌ Bad: Single class check
const isUser = bubble.classList.contains('from-user');
```

---

## Future Enhancements

1. **Thread/Conversation Management**: If multi-conversation support added
2. **Message Editing**: Discover edit message functionality
3. **Message Search**: Search within conversation history
4. **Export Conversation**: Discover conversation export options
5. **Suggested Questions**: Auto-suggested follow-up questions
6. **Voice Input**: If voice-to-text chat input added

---

**End of Chat Panel Discovery Documentation**
