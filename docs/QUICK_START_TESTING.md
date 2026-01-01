# 🚀 Planning Mode - Quick Reference Guide

## Current Status
✅ **Both servers are RUNNING and ready for testing!**

---

## 📍 Quick Links

| Resource | URL | Status |
|----------|-----|--------|
| **Frontend App** | http://localhost:5173/app/ | 🟢 Running |
| **Backend API** | http://localhost:2024 | 🟢 Running |
| **Test Interface** | `test_planning_mode.html` | 📄 Open in browser |

---

## 🎯 Quick Test (30 seconds)

1. **Open Frontend**: http://localhost:5173/app/
2. **Enter Query**: "What are the latest trends in renewable energy?"
3. **Select Effort**: Medium
4. **Click Submit**
5. **Observe**: Planning card should appear with 3 steps!

---

## 🎨 What You Should See

The planning mode UI looks like this:

![Planning Mode UI](C:/Users/masum/.gemini/antigravity/brain/8bed67b7-4513-4908-b832-f8506bf7f6a5/planning_mode_ui_1764944772547.png)

**Key Elements**:
- 📋 Planning card with blue border
- 🏷️ Status badge (auto_approved/awaiting_confirmation/confirmed)
- 📝 List of plan steps with titles and tools
- 🔘 Action buttons (Enter/Skip/Confirm)
- 💬 Feedback messages

---

## 🎮 Available Commands

| Command | Button | Action |
|---------|--------|--------|
| `/plan` | "Enter Planning" | Activates planning mode, requires confirmation |
| `/end_plan` | "Skip Planning" | Bypasses planning, starts research immediately |
| `/confirm_plan` | "Confirm Plan" | Confirms plan and starts web research |

---

## 📊 Status Flow

```
User submits query
        ↓
Generate search queries
        ↓
Planning Mode activates
        ↓
    ┌───────────────────────┐
    │ require_confirmation? │
    └───────┬───────────────┘
            │
    ┌───────┴────────┐
    │                │
   YES              NO
    │                │
    ↓                ↓
awaiting_      auto_approved
confirmation        │
    │               │
    ↓               │
User clicks        │
"Confirm Plan"     │
    │               │
    ↓               ↓
confirmed ────────→ Web Research Begins
```

---

## 🧪 Test Scenarios

### ✅ Scenario 1: Auto-Approved (Default)
```
Query: "What are the latest trends in renewable energy?"
Effort: Medium
Expected: Planning card appears, status = "auto_approved", research starts
```

### ✅ Scenario 2: Manual Confirmation
```
Config: Set require_planning_confirmation = true
Query: "Explain quantum computing"
Expected: Status = "awaiting_confirmation", "Confirm Plan" button appears
```

### ✅ Scenario 3: Skip Planning
```
Action: Click "Skip Planning" button
Expected: Planning bypassed, research starts immediately
```

---

## 📁 Key Files

### Backend
- `backend/src/agent/graph.py` - Planning nodes (lines 238-328)
- `backend/src/agent/state.py` - State definitions
- `backend/src/agent/configuration.py` - Config options
- `backend/tests/test_planning.py` - Unit tests

### Frontend
- `frontend/src/App.tsx` - State & event handling (lines 16-20, 47-58, 182-199)
- `frontend/src/components/ChatMessagesView.tsx` - Planning UI (lines 267-347)

---

## 🔧 Configuration

### Enable Manual Confirmation

Edit `backend/src/agent/configuration.py`:

```python
require_planning_confirmation: bool = Field(
    default=True,  # Change from False to True
    metadata={
        "description": "If true, pause after planning until the user confirms the plan"
    },
)
```

Then restart the backend server.

---

## 🐛 Troubleshooting

### Planning Card Doesn't Appear
**Check**:
1. Browser console for errors
2. Backend logs for planning_mode events
3. Network tab for API calls

**Debug**:
```typescript
// Add to App.tsx onUpdateEvent
console.log('Event:', event);
console.log('Planning context:', planningContext);
```

### Buttons Don't Work
**Check**:
1. `onSendCommand` is passed to ChatMessagesView
2. Commands are reaching backend (check backend logs)

**Debug**:
```typescript
// Add to handlePlanningCommand
console.log('Sending command:', command);
```

### Status Not Updating
**Check**:
1. Event structure matches expected format
2. setPlanningContext is being called

**Debug**:
```typescript
console.log('Planning mode event:', event.planning_mode);
console.log('Planning wait event:', event.planning_wait);
```

---

## 📝 Testing Checklist

Quick checklist for manual testing:

- [ ] Planning card appears on query submission
- [ ] Status badge displays correctly
- [ ] Plan steps are rendered (count matches effort level)
- [ ] "Enter Planning" button works
- [ ] "Skip Planning" button works
- [ ] "Confirm Plan" button appears when status = "awaiting_confirmation"
- [ ] "Confirm Plan" button starts research
- [ ] Feedback messages display
- [ ] Planning card persists during research
- [ ] UI is responsive and styled correctly

---

## 📚 Documentation

For detailed information, see:

1. **PLANNING_MODE_TEST_SUMMARY.md** - Complete implementation overview
2. **PLANNING_MODE_TEST_PLAN.md** - Comprehensive test plan with 10 scenarios
3. **test_planning_mode.html** - Interactive test interface

---

## 🎯 Success Criteria

Planning mode is working correctly if:

✅ Planning UI appears for all queries  
✅ All commands work (/plan, /end_plan, /confirm_plan)  
✅ Status transitions are correct  
✅ Plan steps display accurately  
✅ Confirmation workflow functions  
✅ No UI crashes or errors  

---

## 💡 Tips

1. **Use Test Interface**: Open `test_planning_mode.html` for guided testing
2. **Check Logs**: Monitor both browser console and backend logs
3. **Try Different Effort Levels**: Low (1 step), Medium (3 steps), High (5 steps)
4. **Test Commands**: Use the command buttons to test different flows
5. **Verify Status**: Watch the status badge change as you interact

---

## 🚀 Next Steps

1. ✅ Servers are running
2. ⏳ **Open frontend and test** → http://localhost:5173/app/
3. ⏳ Run through test scenarios
4. ⏳ Document any issues found
5. ⏳ Verify all features work as expected

---

## 📞 Quick Commands

```bash
# Start backend (if not running)
cd backend && langgraph dev

# Start frontend (if not running)
cd frontend && npm run dev

# Open test interface
start test_planning_mode.html

# Open frontend app
start http://localhost:5173/app/
```

---

**Happy Testing! 🎉**

The planning mode implementation is complete and ready for your review!
