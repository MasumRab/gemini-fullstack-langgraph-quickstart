# Planning Mode Frontend Testing Guide

## Overview
This document provides a comprehensive test plan for the Planning Mode feature implemented in the Gemini Fullstack LangGraph Quickstart application.

## Current Implementation Status

### ✅ Backend Implementation (Complete)
Located in `backend/src/agent/graph.py`:

1. **Planning Mode Node** (lines 238-289)
   - Creates structured plan steps from generated queries
   - Supports `/plan`, `/end_plan` commands
   - Configurable auto-approval vs manual confirmation
   - Returns planning steps, status, and feedback

2. **Planning Wait Node** (lines 298-303)
   - Pauses execution until user confirms
   - Provides feedback messages

3. **Planning Router** (lines 306-328)
   - Routes based on planning status and commands
   - Handles `/plan`, `/end_plan`, `/confirm_plan` commands
   - Integrates with `continue_to_web_research`

### ✅ Frontend Implementation (Complete)
Located in `frontend/src/App.tsx` and `frontend/src/components/ChatMessagesView.tsx`:

1. **State Management** (`App.tsx` lines 16-20)
   ```typescript
   const [planningContext, setPlanningContext] = useState<{
     steps: any[];
     status?: string | null;
     feedback?: string[];
   } | null>(null);
   ```

2. **Event Handling** (`App.tsx` lines 47-58)
   - Captures `planning_mode` events
   - Captures `planning_wait` events
   - Updates planning context state

3. **Planning UI** (`ChatMessagesView.tsx` lines 267-347)
   - Displays planning card with steps
   - Shows status badges
   - Provides action buttons (Enter Planning, Skip Planning, Confirm Plan)
   - Conditional rendering based on planning status

4. **Command Handling** (`App.tsx` lines 182-199)
   - `handlePlanningCommand` function
   - Sends commands to backend via thread.submit()

## Test Scenarios

### Test 1: Basic Planning Mode Display
**Objective**: Verify planning mode UI appears when planning context is set

**Steps**:
1. Navigate to `http://localhost:5173/app/`
2. Enter a research query: "What are the latest trends in renewable energy?"
3. Select effort level: "medium" (3 queries, 3 loops)
4. Submit the query

**Expected Results**:
- Planning mode card appears at the top of the chat
- Shows "Planning Mode" header
- Displays "3 proposed steps" (or similar)
- Shows status badge (e.g., "auto_approved" or "awaiting_confirmation")
- Lists the generated search queries as plan steps
- Each step shows:
  - Title (e.g., "Investigate: renewable energy trends 2024")
  - Status badge
  - Tool name ("web_research")

**Verification Points**:
- [ ] Planning card is visible
- [ ] Step count is accurate
- [ ] Status is displayed correctly
- [ ] All steps are rendered

---

### Test 2: Planning Confirmation Workflow
**Objective**: Test the human-in-the-loop confirmation flow

**Prerequisites**: Set `require_planning_confirmation: true` in backend configuration

**Steps**:
1. Start a new conversation
2. Enter query: "Explain quantum computing"
3. Select effort: "low" (1 query, 1 loop)
4. Submit query
5. Wait for planning mode to appear
6. Observe status: should be "awaiting_confirmation"
7. Click "Confirm Plan" button

**Expected Results**:
- Planning status changes to "confirmed"
- Web research begins after confirmation
- Activity timeline shows "Web Research" events
- Planning card remains visible during execution

**Verification Points**:
- [ ] Status shows "awaiting_confirmation" initially
- [ ] "Confirm Plan" button is visible
- [ ] Clicking button triggers web research
- [ ] Status updates to "confirmed"

---

### Test 3: Skip Planning Command
**Objective**: Test the `/end_plan` command functionality

**Steps**:
1. Start a new conversation
2. Enter query: "What is machine learning?"
3. Select effort: "medium"
4. Submit query
5. When planning mode appears, click "Skip Planning" button

**Expected Results**:
- Planning status changes to "auto_approved"
- Planning steps array becomes empty
- Feedback shows "Planning disabled via /end_plan"
- Web research proceeds immediately

**Verification Points**:
- [ ] "Skip Planning" button works
- [ ] Planning is bypassed
- [ ] Research continues normally

---

### Test 4: Enter Planning Command
**Objective**: Test the `/plan` command functionality

**Steps**:
1. Start a new conversation
2. Click "Start Planning" button (at bottom of chat)
3. Observe the planning mode activation

**Expected Results**:
- Planning mode enters "awaiting_confirmation" state
- Planning card appears
- User must confirm before research begins

**Verification Points**:
- [ ] "/plan" command triggers planning mode
- [ ] Status is "awaiting_confirmation"
- [ ] Confirmation required before proceeding

---

### Test 5: Planning Mode with Different Effort Levels
**Objective**: Verify planning adapts to different query counts

**Test Cases**:

#### Case A: Low Effort
- Effort: "low" → 1 query, 1 loop
- Expected: 1 plan step

#### Case B: Medium Effort
- Effort: "medium" → 3 queries, 3 loops
- Expected: 3 plan steps

#### Case C: High Effort
- Effort: "high" → 5 queries, 10 loops
- Expected: 5 plan steps

**Verification Points**:
- [ ] Plan step count matches query count
- [ ] Each step has unique query
- [ ] All steps are properly formatted

---

### Test 6: Planning Feedback Messages
**Objective**: Verify feedback messages are displayed correctly

**Steps**:
1. Trigger planning mode
2. Check for feedback messages in the planning card

**Expected Feedback Examples**:
- "Generated 3 plan steps from initial queries."
- "Awaiting user confirmation. Update planning_status to 'confirmed' to continue."
- "Planning disabled via /end_plan."
- "Planning skipped via /end_plan."

**Verification Points**:
- [ ] Feedback messages appear in UI
- [ ] Messages are contextually appropriate
- [ ] Messages update based on actions

---

### Test 7: Planning Status Transitions
**Objective**: Verify all status transitions work correctly

**Status Flow**:
```
null → awaiting_confirmation → confirmed → (research begins)
null → auto_approved → (research begins)
null → skip_planning → auto_approved → (research begins)
```

**Verification Points**:
- [ ] Status badge updates in real-time
- [ ] UI adapts to each status
- [ ] Transitions are smooth

---

### Test 8: Planning Mode During Active Research
**Objective**: Verify planning UI behavior during web research

**Steps**:
1. Submit a query with medium effort
2. Confirm the plan (if required)
3. Observe planning card during web research

**Expected Results**:
- Planning card remains visible
- Status updates to "confirmed"
- Activity timeline shows research progress below planning card
- Planning card doesn't interfere with chat messages

**Verification Points**:
- [ ] Planning card persists during research
- [ ] No UI conflicts
- [ ] Activity timeline works correctly

---

### Test 9: Multiple Queries in Sequence
**Objective**: Test planning mode across multiple conversations

**Steps**:
1. Submit first query, complete research
2. Submit second query
3. Verify planning mode activates again
4. Check that previous planning context is cleared

**Expected Results**:
- Each query gets its own planning context
- Previous planning data doesn't persist
- UI resets properly between queries

**Verification Points**:
- [ ] Planning context resets
- [ ] No data leakage between queries
- [ ] UI state is clean

---

### Test 10: Error Handling
**Objective**: Verify graceful handling of edge cases

**Test Cases**:

#### Case A: No Queries Generated
- Scenario: Backend returns empty query list
- Expected: Feedback shows "No queries available"

#### Case B: Backend Error
- Scenario: Backend fails during planning
- Expected: Error message displayed, no crash

#### Case C: Network Interruption
- Scenario: Connection lost during planning
- Expected: Appropriate error handling

**Verification Points**:
- [ ] No crashes on edge cases
- [ ] Error messages are user-friendly
- [ ] App remains functional

---

## Manual Testing Checklist

### Visual Inspection
- [ ] Planning card has proper styling (border, background, padding)
- [ ] Text is readable (contrast, font size)
- [ ] Buttons are properly styled and accessible
- [ ] Status badges are color-coded appropriately
- [ ] Layout is responsive on different screen sizes

### Interaction Testing
- [ ] All buttons are clickable
- [ ] Hover states work
- [ ] Click feedback is immediate
- [ ] No UI lag or freezing

### Integration Testing
- [ ] Planning mode integrates with chat flow
- [ ] Activity timeline works alongside planning
- [ ] Messages display correctly
- [ ] Scrolling works properly

### Accessibility Testing
- [ ] Keyboard navigation works
- [ ] Screen reader compatibility (if applicable)
- [ ] Focus indicators are visible
- [ ] ARIA labels are present

---

## Configuration Testing

### Backend Configuration Options
Test with different `Configuration` settings in `backend/src/agent/configuration.py`:

```python
require_planning_confirmation: bool = Field(
    default=False,  # Test with True and False
    metadata={
        "description": "If true, pause after planning until the user confirms the plan"
    },
)
```

**Test Matrix**:
| `require_planning_confirmation` | Expected Behavior |
|--------------------------------|-------------------|
| `False` | Auto-approve, research starts immediately |
| `True` | Wait for user confirmation |

---

## Debugging Tips

### Check Browser Console
Look for:
- Event logs from `onUpdateEvent`
- State updates for `planningContext`
- Network requests to backend
- Any JavaScript errors

### Check Backend Logs
Look for:
- Planning mode node execution
- Planning router decisions
- State transitions
- Any Python exceptions

### Common Issues

#### Planning Card Doesn't Appear
**Possible Causes**:
- `planningContext` state not set
- Event handler not capturing `planning_mode` events
- Conditional rendering logic issue

**Debug**:
```typescript
// Add to App.tsx onUpdateEvent
console.log('Event received:', event);
console.log('Planning context:', planningContext);
```

#### Buttons Don't Work
**Possible Causes**:
- `onSendCommand` not passed to component
- Command not reaching backend
- Backend not processing command

**Debug**:
```typescript
// Add to handlePlanningCommand
console.log('Sending command:', command);
```

#### Status Not Updating
**Possible Causes**:
- State not updating in `setPlanningContext`
- Backend not emitting status updates
- Event structure mismatch

**Debug**:
```typescript
// Check event structure
console.log('Planning event:', event.planning_mode);
console.log('Planning wait event:', event.planning_wait);
```

---

## Success Criteria

The planning mode implementation is considered successful if:

1. ✅ Planning UI appears for all queries
2. ✅ All three commands work (`/plan`, `/end_plan`, `/confirm_plan`)
3. ✅ Status transitions are correct
4. ✅ Feedback messages are displayed
5. ✅ Plan steps are accurately shown
6. ✅ Confirmation workflow functions properly
7. ✅ No UI crashes or errors
8. ✅ Integration with research flow is seamless
9. ✅ Configuration options work as expected
10. ✅ User experience is smooth and intuitive

---

## Next Steps

After testing, consider:

1. **Add Unit Tests**: Create Jest tests for planning components
2. **Add E2E Tests**: Use Playwright for automated testing
3. **Performance Testing**: Measure rendering performance with many steps
4. **Accessibility Audit**: Run axe or similar tools
5. **User Feedback**: Gather feedback on UX
6. **Documentation**: Update user-facing docs with planning mode instructions

---

## Test Results Template

```markdown
## Test Session: [Date]
**Tester**: [Name]
**Environment**: 
- OS: Windows 11
- Browser: Chrome/Firefox/Edge
- Backend: LangGraph 1.0.4
- Frontend: React 19 + Vite 6

### Test Results

| Test # | Test Name | Status | Notes |
|--------|-----------|--------|-------|
| 1 | Basic Planning Display | ✅/❌ | |
| 2 | Confirmation Workflow | ✅/❌ | |
| 3 | Skip Planning | ✅/❌ | |
| 4 | Enter Planning | ✅/❌ | |
| 5 | Different Effort Levels | ✅/❌ | |
| 6 | Feedback Messages | ✅/❌ | |
| 7 | Status Transitions | ✅/❌ | |
| 8 | Active Research | ✅/❌ | |
| 9 | Multiple Queries | ✅/❌ | |
| 10 | Error Handling | ✅/❌ | |

### Issues Found
1. [Issue description]
2. [Issue description]

### Recommendations
1. [Recommendation]
2. [Recommendation]
```

---

## Quick Start Testing

**For immediate testing, run these commands**:

```bash
# Terminal 1: Start backend
cd backend
langgraph dev

# Terminal 2: Start frontend
cd frontend
npm run dev

# Open browser to http://localhost:5173/app/
```

**Quick Test Query**:
```
What are the latest developments in artificial intelligence?
```

**Expected**: Planning mode should activate, showing 1-5 plan steps depending on effort level selected.
