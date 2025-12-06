/**
 * Comprehensive unit tests for frontend/src/hooks/useAgentState.ts
 *
 * Tests cover:
 * - Hook initialization
 * - State updates from events
 * - Research results processing
 * - Planning context handling
 * - Activity tracking
 * - Edge cases and error handling
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'
import { useAgentState } from './useAgentState'

// Mock data
const mockWebResearchEvent = {
  web_research: [
    {
      query: 'test query',
      url: 'https://example.com',
      content: 'test content',
    },
  ],
}

const mockPlanningModeEvent = {
  planning_mode: {
    planning_steps: [
      {
        id: '1',
        title: 'Step 1',
        status: 'pending',
        query: 'test query',
        suggested_tool: 'web_research',
      },
    ],
    planning_status: 'auto_approved',
    planning_feedback: ['Planning initialized'],
  },
}

const mockPlanningWaitEvent = {
  planning_wait: {
    planning_feedback: ['Awaiting confirmation'],
  },
}

const mockReflectionEvent = {
  reflection: {
    message: 'Reflecting on results',
  },
}

const mockFinalizeAnswerEvent = {
  finalize_answer: {
    message: 'Final answer generated',
  },
}

describe('useAgentState', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Initialization', () => {
    it('should initialize with empty state', () => {
      const { result } = renderHook(() => useAgentState())

      expect(result.current.researchResults).toEqual([])
      expect(result.current.planningContext).toBeNull()
      expect(result.current.activityLog).toEqual([])
    })

    it('should return handler functions', () => {
      const { result } = renderHook(() => useAgentState())

      expect(typeof result.current.handleUpdateEvent).toBe('function')
      expect(typeof result.current.resetState).toBe('function')
    })
  })

  describe('Web Research Event Handling', () => {
    it('should process web_research events', () => {
      const { result } = renderHook(() => useAgentState())

      act(() => {
        result.current.handleUpdateEvent(mockWebResearchEvent)
      })

      expect(result.current.researchResults).toHaveLength(1)
      expect(result.current.researchResults[0]).toMatchObject({
        query: 'test query',
        url: 'https://example.com',
        content: 'test content',
      })
    })

    it('should handle multiple web_research events', () => {
      const { result } = renderHook(() => useAgentState())

      act(() => {
        result.current.handleUpdateEvent({
          web_research: [
            { query: 'query1', url: 'http://example1.com', content: 'content1' },
          ],
        })
      })

      act(() => {
        result.current.handleUpdateEvent({
          web_research: [
            { query: 'query2', url: 'http://example2.com', content: 'content2' },
          ],
        })
      })

      expect(result.current.researchResults).toHaveLength(2)
    })

    it('should handle empty web_research array', () => {
      const { result } = renderHook(() => useAgentState())

      act(() => {
        result.current.handleUpdateEvent({
          web_research: [],
        })
      })

      expect(result.current.researchResults).toEqual([])
    })

    it('should add web_research to activity log', () => {
      const { result } = renderHook(() => useAgentState())

      act(() => {
        result.current.handleUpdateEvent(mockWebResearchEvent)
      })

      expect(result.current.activityLog).toHaveLength(1)
      expect(result.current.activityLog[0].type).toBe('web_research')
    })

    it('should include timestamp in activity log', () => {
      const { result } = renderHook(() => useAgentState())

      act(() => {
        result.current.handleUpdateEvent(mockWebResearchEvent)
      })

      expect(result.current.activityLog[0]).toHaveProperty('timestamp')
      expect(typeof result.current.activityLog[0].timestamp).toBe('number')
    })
  })

  describe('Planning Mode Event Handling', () => {
    it('should process planning_mode events', () => {
      const { result } = renderHook(() => useAgentState())

      act(() => {
        result.current.handleUpdateEvent(mockPlanningModeEvent)
      })

      expect(result.current.planningContext).not.toBeNull()
      expect(result.current.planningContext?.steps).toHaveLength(1)
      expect(result.current.planningContext?.status).toBe('auto_approved')
    })

    it('should handle planning_mode with multiple steps', () => {
      const { result } = renderHook(() => useAgentState())

      act(() => {
        result.current.handleUpdateEvent({
          planning_mode: {
            planning_steps: [
              { id: '1', title: 'Step 1', status: 'pending', query: 'query1', suggested_tool: 'web_research' },
              { id: '2', title: 'Step 2', status: 'pending', query: 'query2', suggested_tool: 'web_research' },
              { id: '3', title: 'Step 3', status: 'pending', query: 'query3', suggested_tool: 'web_research' },
            ],
            planning_status: 'awaiting_confirmation',
            planning_feedback: ['Awaiting confirmation'],
          },
        })
      })

      expect(result.current.planningContext?.steps).toHaveLength(3)
      expect(result.current.planningContext?.status).toBe('awaiting_confirmation')
    })

    it('should handle empty planning_steps array', () => {
      const { result } = renderHook(() => useAgentState())

      act(() => {
        result.current.handleUpdateEvent({
          planning_mode: {
            planning_steps: [],
            planning_status: 'auto_approved',
            planning_feedback: [],
          },
        })
      })

      expect(result.current.planningContext?.steps).toEqual([])
    })

    it('should update planning_feedback', () => {
      const { result } = renderHook(() => useAgentState())

      act(() => {
        result.current.handleUpdateEvent({
          planning_mode: {
            planning_steps: [],
            planning_status: 'confirmed',
            planning_feedback: ['Feedback 1', 'Feedback 2'],
          },
        })
      })

      expect(result.current.planningContext?.feedback).toEqual(['Feedback 1', 'Feedback 2'])
    })

    it('should add planning_mode to activity log', () => {
      const { result } = renderHook(() => useAgentState())

      act(() => {
        result.current.handleUpdateEvent(mockPlanningModeEvent)
      })

      expect(result.current.activityLog).toHaveLength(1)
      expect(result.current.activityLog[0].type).toBe('planning_mode')
    })
  })

  describe('Planning Wait Event Handling', () => {
    it('should process planning_wait events', () => {
      const { result } = renderHook(() => useAgentState())

      // First set initial planning context
      act(() => {
        result.current.handleUpdateEvent(mockPlanningModeEvent)
      })

      // Then process planning_wait
      act(() => {
        result.current.handleUpdateEvent(mockPlanningWaitEvent)
      })

      expect(result.current.planningContext?.status).toBe('awaiting_confirmation')
      expect(result.current.planningContext?.feedback).toContain('Awaiting confirmation')
    })

    it('should handle planning_wait without prior planning_mode', () => {
      const { result } = renderHook(() => useAgentState())

      act(() => {
        result.current.handleUpdateEvent(mockPlanningWaitEvent)
      })

      // Should create planning context with default values
      expect(result.current.planningContext).not.toBeNull()
      expect(result.current.planningContext?.status).toBe('awaiting_confirmation')
    })

    it('should preserve planning steps during planning_wait', () => {
      const { result } = renderHook(() => useAgentState())

      act(() => {
        result.current.handleUpdateEvent(mockPlanningModeEvent)
      })

      const initialSteps = result.current.planningContext?.steps

      act(() => {
        result.current.handleUpdateEvent(mockPlanningWaitEvent)
      })

      expect(result.current.planningContext?.steps).toEqual(initialSteps)
    })
  })

  describe('Reflection Event Handling', () => {
    it('should process reflection events', () => {
      const { result } = renderHook(() => useAgentState())

      act(() => {
        result.current.handleUpdateEvent(mockReflectionEvent)
      })

      expect(result.current.activityLog).toHaveLength(1)
      expect(result.current.activityLog[0].type).toBe('reflection')
    })

    it('should include reflection message in activity log', () => {
      const { result } = renderHook(() => useAgentState())

      act(() => {
        result.current.handleUpdateEvent(mockReflectionEvent)
      })

      expect(result.current.activityLog[0].data).toMatchObject(mockReflectionEvent.reflection)
    })
  })

  describe('Finalize Answer Event Handling', () => {
    it('should process finalize_answer events', () => {
      const { result } = renderHook(() => useAgentState())

      act(() => {
        result.current.handleUpdateEvent(mockFinalizeAnswerEvent)
      })

      expect(result.current.activityLog).toHaveLength(1)
      expect(result.current.activityLog[0].type).toBe('finalize_answer')
    })
  })

  describe('Activity Log Management', () => {
    it('should maintain chronological order in activity log', () => {
      const { result } = renderHook(() => useAgentState())

      act(() => {
        result.current.handleUpdateEvent(mockPlanningModeEvent)
      })

      act(() => {
        result.current.handleUpdateEvent(mockWebResearchEvent)
      })

      act(() => {
        result.current.handleUpdateEvent(mockReflectionEvent)
      })

      expect(result.current.activityLog).toHaveLength(3)
      expect(result.current.activityLog[0].type).toBe('planning_mode')
      expect(result.current.activityLog[1].type).toBe('web_research')
      expect(result.current.activityLog[2].type).toBe('reflection')
    })

    it('should assign unique IDs to activity log entries', () => {
      const { result } = renderHook(() => useAgentState())

      act(() => {
        result.current.handleUpdateEvent(mockWebResearchEvent)
      })

      act(() => {
        result.current.handleUpdateEvent(mockReflectionEvent)
      })

      const ids = result.current.activityLog.map(entry => entry.id)
      const uniqueIds = new Set(ids)

      expect(uniqueIds.size).toBe(ids.length)
    })

    it('should include event data in activity log', () => {
      const { result } = renderHook(() => useAgentState())

      act(() => {
        result.current.handleUpdateEvent(mockWebResearchEvent)
      })

      expect(result.current.activityLog[0].data).toEqual(mockWebResearchEvent.web_research)
    })
  })

  describe('State Reset', () => {
    it('should reset all state', () => {
      const { result } = renderHook(() => useAgentState())

      // Populate state
      act(() => {
        result.current.handleUpdateEvent(mockPlanningModeEvent)
        result.current.handleUpdateEvent(mockWebResearchEvent)
      })

      // Reset
      act(() => {
        result.current.resetState()
      })

      expect(result.current.researchResults).toEqual([])
      expect(result.current.planningContext).toBeNull()
      expect(result.current.activityLog).toEqual([])
    })

    it('should allow state updates after reset', () => {
      const { result } = renderHook(() => useAgentState())

      act(() => {
        result.current.handleUpdateEvent(mockWebResearchEvent)
        result.current.resetState()
        result.current.handleUpdateEvent(mockWebResearchEvent)
      })

      expect(result.current.researchResults).toHaveLength(1)
    })
  })

  describe('Edge Cases', () => {
    it('should handle null event', () => {
      const { result } = renderHook(() => useAgentState())

      act(() => {
        result.current.handleUpdateEvent(null as any)
      })

      expect(result.current.researchResults).toEqual([])
      expect(result.current.planningContext).toBeNull()
      expect(result.current.activityLog).toEqual([])
    })

    it('should handle undefined event', () => {
      const { result } = renderHook(() => useAgentState())

      act(() => {
        result.current.handleUpdateEvent(undefined as any)
      })

      expect(result.current.researchResults).toEqual([])
    })

    it('should handle empty event object', () => {
      const { result } = renderHook(() => useAgentState())

      act(() => {
        result.current.handleUpdateEvent({})
      })

      expect(result.current.researchResults).toEqual([])
      expect(result.current.activityLog).toEqual([])
    })

    it('should handle event with unknown type', () => {
      const { result } = renderHook(() => useAgentState())

      act(() => {
        result.current.handleUpdateEvent({
          unknown_event: { data: 'test' },
        })
      })

      // Should not crash
      expect(result.current.researchResults).toEqual([])
    })

    it('should handle malformed web_research data', () => {
      const { result } = renderHook(() => useAgentState())

      act(() => {
        result.current.handleUpdateEvent({
          web_research: 'not an array',
        } as any)
      })

      // Should handle gracefully without crashing
      expect(result.current.researchResults).toBeDefined()
    })

    it('should handle malformed planning_mode data', () => {
      const { result } = renderHook(() => useAgentState())

      act(() => {
        result.current.handleUpdateEvent({
          planning_mode: 'not an object',
        } as any)
      })

      // Should handle gracefully
      expect(result.current.planningContext).toBeDefined()
    })

    it('should handle very large activity log', () => {
      const { result } = renderHook(() => useAgentState())

      act(() => {
        for (let i = 0; i < 1000; i++) {
          result.current.handleUpdateEvent({
            reflection: { message: `Message ${i}` },
          })
        }
      })

      expect(result.current.activityLog.length).toBeGreaterThan(0)
    })

    it('should handle rapid successive events', () => {
      const { result } = renderHook(() => useAgentState())

      act(() => {
        result.current.handleUpdateEvent(mockPlanningModeEvent)
        result.current.handleUpdateEvent(mockWebResearchEvent)
        result.current.handleUpdateEvent(mockReflectionEvent)
        result.current.handleUpdateEvent(mockFinalizeAnswerEvent)
      })

      expect(result.current.activityLog).toHaveLength(4)
    })
  })

  describe('State Immutability', () => {
    it('should not mutate research results on new events', () => {
      const { result } = renderHook(() => useAgentState())

      act(() => {
        result.current.handleUpdateEvent(mockWebResearchEvent)
      })

      const firstResults = result.current.researchResults

      act(() => {
        result.current.handleUpdateEvent({
          web_research: [
            { query: 'query2', url: 'http://example2.com', content: 'content2' },
          ],
        })
      })

      // Original reference should not be mutated
      expect(firstResults).toHaveLength(1)
      expect(result.current.researchResults).toHaveLength(2)
    })

    it('should not mutate planning context on updates', () => {
      const { result } = renderHook(() => useAgentState())

      act(() => {
        result.current.handleUpdateEvent(mockPlanningModeEvent)
      })

      const firstContext = result.current.planningContext

      act(() => {
        result.current.handleUpdateEvent(mockPlanningWaitEvent)
      })

      // Original reference should not be mutated
      expect(firstContext?.status).toBe('auto_approved')
      expect(result.current.planningContext?.status).toBe('awaiting_confirmation')
    })
  })

  describe('Type Safety', () => {
    it('should handle web_research results with all fields', () => {
      const { result } = renderHook(() => useAgentState())

      act(() => {
        result.current.handleUpdateEvent({
          web_research: [
            {
              query: 'test query',
              url: 'https://example.com',
              content: 'test content',
              title: 'Test Title',
              score: 0.95,
            },
          ],
        })
      })

      expect(result.current.researchResults[0]).toHaveProperty('query')
      expect(result.current.researchResults[0]).toHaveProperty('url')
      expect(result.current.researchResults[0]).toHaveProperty('content')
    })

    it('should handle planning steps with all fields', () => {
      const { result } = renderHook(() => useAgentState())

      act(() => {
        result.current.handleUpdateEvent({
          planning_mode: {
            planning_steps: [
              {
                id: '1',
                title: 'Test Step',
                status: 'pending',
                query: 'test query',
                suggested_tool: 'web_research',
                result: 'test result',
              },
            ],
            planning_status: 'auto_approved',
            planning_feedback: ['test feedback'],
          },
        })
      })

      const step = result.current.planningContext?.steps[0]
      expect(step).toHaveProperty('id')
      expect(step).toHaveProperty('title')
      expect(step).toHaveProperty('status')
      expect(step).toHaveProperty('query')
      expect(step).toHaveProperty('suggested_tool')
    })
  })

  describe('Integration Scenarios', () => {
    it('should handle complete workflow', () => {
      const { result } = renderHook(() => useAgentState())

      // Planning phase
      act(() => {
        result.current.handleUpdateEvent(mockPlanningModeEvent)
      })

      expect(result.current.planningContext).not.toBeNull()

      // Research phase
      act(() => {
        result.current.handleUpdateEvent(mockWebResearchEvent)
      })

      expect(result.current.researchResults).toHaveLength(1)

      // Reflection phase
      act(() => {
        result.current.handleUpdateEvent(mockReflectionEvent)
      })

      // Finalize phase
      act(() => {
        result.current.handleUpdateEvent(mockFinalizeAnswerEvent)
      })

      expect(result.current.activityLog).toHaveLength(4)
    })

    it('should handle multiple research iterations', () => {
      const { result } = renderHook(() => useAgentState())

      // First iteration
      act(() => {
        result.current.handleUpdateEvent(mockWebResearchEvent)
        result.current.handleUpdateEvent(mockReflectionEvent)
      })

      // Second iteration
      act(() => {
        result.current.handleUpdateEvent({
          web_research: [
            { query: 'iteration 2', url: 'http://example2.com', content: 'content2' },
          ],
        })
        result.current.handleUpdateEvent(mockReflectionEvent)
      })

      expect(result.current.researchResults).toHaveLength(2)
      expect(result.current.activityLog.filter(e => e.type === 'reflection')).toHaveLength(2)
    })
  })
})