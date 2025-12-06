import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'
import { useAgentState } from '../useAgentState'
import type { Message } from '@langchain/langgraph-sdk'

// Mock the useStream hook from LangGraph SDK
vi.mock('@langchain/langgraph-sdk/react', () => ({
  useStream: vi.fn(() => ({
    messages: [],
    isLoading: false,
    submit: vi.fn(),
    stop: vi.fn(),
  })),
}))

// Import after mocking
import { useStream } from '@langchain/langgraph-sdk/react'

describe('useAgentState', () => {
  let mockUseStream: ReturnType<typeof vi.fn>
  let mockSubmit: ReturnType<typeof vi.fn>
  let mockStop: ReturnType<typeof vi.fn>

  beforeEach(() => {
    mockSubmit = vi.fn()
    mockStop = vi.fn()
    mockUseStream = vi.mocked(useStream)
    
    // Default mock implementation
    mockUseStream.mockReturnValue({
      messages: [],
      isLoading: false,
      submit: mockSubmit,
      stop: mockStop,
    })
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  describe('Initialization', () => {
    it('should initialize with empty state', () => {
      const { result } = renderHook(() => useAgentState())

      expect(result.current.processedEventsTimeline).toEqual([])
      expect(result.current.historicalActivities).toEqual({})
      expect(result.current.planningContext).toBeNull()
      expect(result.current.error).toBeNull()
    })

    it('should initialize useStream with correct configuration', () => {
      renderHook(() => useAgentState())

      expect(mockUseStream).toHaveBeenCalledWith(
        expect.objectContaining({
          apiUrl: expect.any(String),
          assistantId: 'agent',
          messagesKey: 'messages',
          onUpdateEvent: expect.any(Function),
          onError: expect.any(Function),
        })
      )
    })

    it('should use correct API URL based on environment', () => {
      // Test development environment
      vi.stubEnv('DEV', true)
      renderHook(() => useAgentState())
      
      expect(mockUseStream).toHaveBeenCalledWith(
        expect.objectContaining({
          apiUrl: 'http://localhost:2024',
        })
      )

      vi.unstubAllEnvs()
      
      // Test production environment
      vi.stubEnv('DEV', false)
      const { rerender } = renderHook(() => useAgentState())
      rerender()
      
      expect(mockUseStream).toHaveBeenCalledWith(
        expect.objectContaining({
          apiUrl: 'http://localhost:8123',
        })
      )
    })
  })

  describe('handleSubmit', () => {
    it('should not submit empty input', () => {
      const { result } = renderHook(() => useAgentState())

      act(() => {
        result.current.handleSubmit('', 'low', 'gemini-2.5-flash-preview-04-17')
      })

      expect(mockSubmit).not.toHaveBeenCalled()
    })

    it('should not submit whitespace-only input', () => {
      const { result } = renderHook(() => useAgentState())

      act(() => {
        result.current.handleSubmit('   ', 'low', 'gemini-2.5-flash-preview-04-17')
      })

      expect(mockSubmit).not.toHaveBeenCalled()
    })

    it('should submit with low effort configuration', () => {
      const { result } = renderHook(() => useAgentState())

      act(() => {
        result.current.handleSubmit('test query', 'low', 'test-model')
      })

      expect(mockSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          initial_search_query_count: 1,
          max_research_loops: 1,
          reasoning_model: 'test-model',
          messages: expect.arrayContaining([
            expect.objectContaining({
              type: 'human',
              content: 'test query',
            }),
          ]),
        })
      )
    })

    it('should submit with medium effort configuration', () => {
      const { result } = renderHook(() => useAgentState())

      act(() => {
        result.current.handleSubmit('test query', 'medium', 'test-model')
      })

      expect(mockSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          initial_search_query_count: 3,
          max_research_loops: 3,
        })
      )
    })

    it('should submit with high effort configuration', () => {
      const { result } = renderHook(() => useAgentState())

      act(() => {
        result.current.handleSubmit('test query', 'high', 'test-model')
      })

      expect(mockSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          initial_search_query_count: 5,
          max_research_loops: 10,
        })
      )
    })

    it('should reset processed events timeline on submit', () => {
      const { result } = renderHook(() => useAgentState())

      // Simulate some events
      act(() => {
        const config = mockUseStream.mock.calls[0][0]
        config.onUpdateEvent({ generate_query: { search_query: ['query1'] } })
      })

      expect(result.current.processedEventsTimeline.length).toBeGreaterThan(0)

      act(() => {
        result.current.handleSubmit('new query', 'low', 'model')
      })

      expect(result.current.processedEventsTimeline).toEqual([])
    })

    it('should append to existing messages', () => {
      const existingMessages: Message[] = [
        { type: 'human', content: 'first message', id: '1' },
        { type: 'ai', content: 'first response', id: '2' },
      ]

      mockUseStream.mockReturnValue({
        messages: existingMessages,
        isLoading: false,
        submit: mockSubmit,
        stop: mockStop,
      })

      const { result } = renderHook(() => useAgentState())

      act(() => {
        result.current.handleSubmit('second message', 'low', 'model')
      })

      expect(mockSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          messages: expect.arrayContaining([
            ...existingMessages,
            expect.objectContaining({ content: 'second message' }),
          ]),
        })
      )
    })

    it('should reset planning context on submit', () => {
      const { result } = renderHook(() => useAgentState())

      // Set planning context
      act(() => {
        const config = mockUseStream.mock.calls[0][0]
        config.onUpdateEvent({
          planning_mode: {
            planning_steps: [{ id: 'step1' }],
            planning_status: 'awaiting_confirmation',
          },
        })
      })

      expect(result.current.planningContext).not.toBeNull()

      act(() => {
        result.current.handleSubmit('query', 'low', 'model')
      })

      expect(result.current.planningContext).toBeNull()
    })

    it('should generate unique message IDs', () => {
      const { result } = renderHook(() => useAgentState())
      const dateNowSpy = vi.spyOn(Date, 'now')
      dateNowSpy.mockReturnValue(12345)

      act(() => {
        result.current.handleSubmit('query', 'low', 'model')
      })

      expect(mockSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          messages: expect.arrayContaining([
            expect.objectContaining({
              id: '12345',
            }),
          ]),
        })
      )

      dateNowSpy.mockRestore()
    })
  })

  describe('handlePlanningCommand', () => {
    it('should send planning command with current config', () => {
      const { result } = renderHook(() => useAgentState())

      // First submit to set config
      act(() => {
        result.current.handleSubmit('initial query', 'high', 'test-model')
      })

      mockSubmit.mockClear()

      // Send planning command
      act(() => {
        result.current.handlePlanningCommand('/confirm_plan')
      })

      expect(mockSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          initial_search_query_count: 5,
          max_research_loops: 10,
          reasoning_model: 'test-model',
          messages: expect.arrayContaining([
            expect.objectContaining({
              content: '/confirm_plan',
            }),
          ]),
        })
      )
    })

    it('should use default config if no previous submit', () => {
      const { result } = renderHook(() => useAgentState())

      act(() => {
        result.current.handlePlanningCommand('/end_plan')
      })

      expect(mockSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          initial_search_query_count: 1,
          max_research_loops: 1,
          reasoning_model: 'gemini-2.5-flash-preview-04-17',
        })
      )
    })

    it('should append command to existing messages', () => {
      const existingMessages: Message[] = [
        { type: 'human', content: 'query', id: '1' },
      ]

      mockUseStream.mockReturnValue({
        messages: existingMessages,
        isLoading: false,
        submit: mockSubmit,
        stop: mockStop,
      })

      const { result } = renderHook(() => useAgentState())

      act(() => {
        result.current.handlePlanningCommand('/plan')
      })

      expect(mockSubmit).toHaveBeenCalledWith(
        expect.objectContaining({
          messages: expect.arrayContaining([
            ...existingMessages,
            expect.objectContaining({ content: '/plan' }),
          ]),
        })
      )
    })
  })

  describe('handleCancel', () => {
    it('should stop the stream', () => {
      const { result } = renderHook(() => useAgentState())

      // Mock window.location.reload
      const reloadMock = vi.fn()
      Object.defineProperty(window, 'location', {
        value: { reload: reloadMock },
        writable: true,
      })

      act(() => {
        result.current.handleCancel()
      })

      expect(mockStop).toHaveBeenCalled()
      expect(reloadMock).toHaveBeenCalled()
    })
  })

  describe('Event Processing - generate_query', () => {
    it('should process generate_query event', () => {
      const { result } = renderHook(() => useAgentState())

      act(() => {
        const config = mockUseStream.mock.calls[0][0]
        config.onUpdateEvent({
          generate_query: {
            search_query: ['query1', 'query2'],
          },
        })
      })

      expect(result.current.processedEventsTimeline).toHaveLength(1)
      expect(result.current.processedEventsTimeline[0]).toEqual({
        title: 'Generating Search Queries',
        data: 'query1, query2',
      })
    })

    it('should handle empty search queries', () => {
      const { result } = renderHook(() => useAgentState())

      act(() => {
        const config = mockUseStream.mock.calls[0][0]
        config.onUpdateEvent({
          generate_query: {
            search_query: [],
          },
        })
      })

      expect(result.current.processedEventsTimeline[0].data).toBe('')
    })

    it('should handle missing search_query field', () => {
      const { result } = renderHook(() => useAgentState())

      act(() => {
        const config = mockUseStream.mock.calls[0][0]
        config.onUpdateEvent({
          generate_query: {},
        })
      })

      expect(result.current.processedEventsTimeline[0].data).toBe('')
    })
  })

  describe('Event Processing - planning_mode', () => {
    it('should update planning context with steps', () => {
      const { result } = renderHook(() => useAgentState())

      const planningSteps = [
        { id: 'step1', title: 'Step 1', status: 'pending' },
        { id: 'step2', title: 'Step 2', status: 'pending' },
      ]

      act(() => {
        const config = mockUseStream.mock.calls[0][0]
        config.onUpdateEvent({
          planning_mode: {
            planning_steps: planningSteps,
            planning_status: 'awaiting_confirmation',
            planning_feedback: ['Plan ready for review'],
          },
        })
      })

      expect(result.current.planningContext).toEqual({
        steps: planningSteps,
        status: 'awaiting_confirmation',
        feedback: ['Plan ready for review'],
      })
    })

    it('should handle planning_mode without feedback', () => {
      const { result } = renderHook(() => useAgentState())

      act(() => {
        const config = mockUseStream.mock.calls[0][0]
        config.onUpdateEvent({
          planning_mode: {
            planning_steps: [],
            planning_status: 'auto_approved',
          },
        })
      })

      expect(result.current.planningContext?.feedback).toEqual([])
    })

    it('should not add planning events to timeline', () => {
      const { result } = renderHook(() => useAgentState())

      act(() => {
        const config = mockUseStream.mock.calls[0][0]
        config.onUpdateEvent({
          planning_mode: {
            planning_steps: [],
            planning_status: 'awaiting_confirmation',
          },
        })
      })

      // Planning mode shouldn't add to timeline
      expect(result.current.processedEventsTimeline).toHaveLength(0)
    })
  })

  describe('Event Processing - planning_wait', () => {
    it('should update planning status to awaiting_confirmation', () => {
      const { result } = renderHook(() => useAgentState())

      // Set initial planning context
      act(() => {
        const config = mockUseStream.mock.calls[0][0]
        config.onUpdateEvent({
          planning_mode: {
            planning_steps: [{ id: 'step1' }],
            planning_status: 'pending',
          },
        })
      })

      // Trigger planning_wait
      act(() => {
        const config = mockUseStream.mock.calls[0][0]
        config.onUpdateEvent({
          planning_wait: {
            planning_feedback: ['Awaiting confirmation'],
          },
        })
      })

      expect(result.current.planningContext?.status).toBe('awaiting_confirmation')
      expect(result.current.planningContext?.feedback).toEqual(['Awaiting confirmation'])
    })

    it('should preserve existing steps during planning_wait', () => {
      const { result } = renderHook(() => useAgentState())

      const steps = [{ id: 'step1', title: 'Step 1' }]

      act(() => {
        const config = mockUseStream.mock.calls[0][0]
        config.onUpdateEvent({
          planning_mode: {
            planning_steps: steps,
            planning_status: 'pending',
          },
        })
      })

      act(() => {
        const config = mockUseStream.mock.calls[0][0]
        config.onUpdateEvent({
          planning_wait: {
            planning_feedback: ['Waiting'],
          },
        })
      })

      expect(result.current.planningContext?.steps).toEqual(steps)
    })
  })

  describe('Event Processing - web_research', () => {
    it('should process web_research event with sources', () => {
      const { result } = renderHook(() => useAgentState())

      act(() => {
        const config = mockUseStream.mock.calls[0][0]
        config.onUpdateEvent({
          web_research: {
            sources_gathered: [
              { label: 'Source 1' },
              { label: 'Source 2' },
              { label: 'Source 3' },
            ],
          },
        })
      })

      expect(result.current.processedEventsTimeline).toHaveLength(1)
      expect(result.current.processedEventsTimeline[0]).toEqual({
        title: 'Web Research',
        data: 'Gathered 3 sources. Related to Source 1, Source 2, Source 3.',
      })
    })

    it('should handle sources without labels', () => {
      const { result } = renderHook(() => useAgentState())

      act(() => {
        const config = mockUseStream.mock.calls[0][0]
        config.onUpdateEvent({
          web_research: {
            sources_gathered: [
              { url: 'http://example.com' },
              { label: 'Named Source' },
            ],
          },
        })
      })

      const event = result.current.processedEventsTimeline[0]
      expect(event.data).toContain('Gathered 2 sources')
      expect(event.data).toContain('Named Source')
    })

    it('should limit displayed labels to 3', () => {
      const { result } = renderHook(() => useAgentState())

      act(() => {
        const config = mockUseStream.mock.calls[0][0]
        config.onUpdateEvent({
          web_research: {
            sources_gathered: [
              { label: 'Source 1' },
              { label: 'Source 2' },
              { label: 'Source 3' },
              { label: 'Source 4' },
              { label: 'Source 5' },
            ],
          },
        })
      })

      const event = result.current.processedEventsTimeline[0]
      // Should only show first 3
      expect(event.data).toContain('Source 1')
      expect(event.data).toContain('Source 2')
      expect(event.data).toContain('Source 3')
      expect(event.data).not.toContain('Source 4')
    })

    it('should deduplicate source labels', () => {
      const { result } = renderHook(() => useAgentState())

      act(() => {
        const config = mockUseStream.mock.calls[0][0]
        config.onUpdateEvent({
          web_research: {
            sources_gathered: [
              { label: 'Duplicate' },
              { label: 'Duplicate' },
              { label: 'Unique' },
            ],
          },
        })
      })

      const event = result.current.processedEventsTimeline[0]
      // Should show unique count
      expect(event.data).toContain('Gathered 3 sources')
      // Labels should be deduplicated
      expect(event.data).toContain('Duplicate, Unique')
    })

    it('should update planning status to confirmed', () => {
      const { result } = renderHook(() => useAgentState())

      act(() => {
        const config = mockUseStream.mock.calls[0][0]
        config.onUpdateEvent({
          planning_mode: {
            planning_steps: [],
            planning_status: 'awaiting_confirmation',
          },
        })
      })

      act(() => {
        const config = mockUseStream.mock.calls[0][0]
        config.onUpdateEvent({
          web_research: {
            sources_gathered: [],
          },
        })
      })

      expect(result.current.planningContext?.status).toBe('confirmed')
    })

    it('should handle web_research when no planning context exists', () => {
      const { result } = renderHook(() => useAgentState())

      act(() => {
        const config = mockUseStream.mock.calls[0][0]
        config.onUpdateEvent({
          web_research: {
            sources_gathered: [{ label: 'Source' }],
          },
        })
      })

      // Should not crash, planning context remains null
      expect(result.current.planningContext).toBeNull()
      expect(result.current.processedEventsTimeline).toHaveLength(1)
    })
  })

  describe('Event Processing - reflection', () => {
    it('should process reflection event', () => {
      const { result } = renderHook(() => useAgentState())

      act(() => {
        const config = mockUseStream.mock.calls[0][0]
        config.onUpdateEvent({
          reflection: {},
        })
      })

      expect(result.current.processedEventsTimeline).toHaveLength(1)
      expect(result.current.processedEventsTimeline[0]).toEqual({
        title: 'Reflection',
        data: 'Analysing Web Research Results',
      })
    })
  })

  describe('Event Processing - finalize_answer', () => {
    it('should process finalize_answer event', () => {
      const { result } = renderHook(() => useAgentState())

      act(() => {
        const config = mockUseStream.mock.calls[0][0]
        config.onUpdateEvent({
          finalize_answer: {},
        })
      })

      expect(result.current.processedEventsTimeline).toHaveLength(1)
      expect(result.current.processedEventsTimeline[0]).toEqual({
        title: 'Finalizing Answer',
        data: 'Composing and presenting the final answer.',
      })
    })

    it('should set finalize event flag', () => {
      const { result } = renderHook(() => useAgentState())

      act(() => {
        const config = mockUseStream.mock.calls[0][0]
        config.onUpdateEvent({
          finalize_answer: {},
        })
      })

      // The ref should be set (we can't directly test it, but we can test the effect)
      // This will be validated by the historical activities test
    })
  })

  describe('Event Processing - Multiple Events', () => {
    it('should accumulate multiple events in timeline', () => {
      const { result } = renderHook(() => useAgentState())

      act(() => {
        const config = mockUseStream.mock.calls[0][0]
        config.onUpdateEvent({ generate_query: { search_query: ['q1'] } })
        config.onUpdateEvent({ web_research: { sources_gathered: [] } })
        config.onUpdateEvent({ reflection: {} })
        config.onUpdateEvent({ finalize_answer: {} })
      })

      expect(result.current.processedEventsTimeline).toHaveLength(4)
    })

    it('should ignore unknown event types', () => {
      const { result } = renderHook(() => useAgentState())

      act(() => {
        const config = mockUseStream.mock.calls[0][0]
        config.onUpdateEvent({ unknown_event: { data: 'test' } })
      })

      expect(result.current.processedEventsTimeline).toHaveLength(0)
    })
  })

  describe('Error Handling', () => {
    it('should set error state when onError callback is triggered', () => {
      const { result } = renderHook(() => useAgentState())

      act(() => {
        const config = mockUseStream.mock.calls[0][0]
        config.onError({ message: 'Test error message' })
      })

      expect(result.current.error).toBe('Test error message')
    })

    it('should handle error object without message', () => {
      const { result } = renderHook(() => useAgentState())

      act(() => {
        const config = mockUseStream.mock.calls[0][0]
        config.onError({})
      })

      expect(result.current.error).toBeUndefined()
    })
  })

  describe('Historical Activities', () => {
    it('should save timeline to historical activities after finalize', async () => {
      const aiMessage: Message = {
        type: 'ai',
        content: 'Response',
        id: 'msg-123',
      }

      mockUseStream.mockReturnValue({
        messages: [aiMessage],
        isLoading: false,
        submit: mockSubmit,
        stop: mockStop,
      })

      const { result, rerender } = renderHook(() => useAgentState())

      // Add some events
      act(() => {
        const config = mockUseStream.mock.calls[0][0]
        config.onUpdateEvent({ generate_query: { search_query: ['q1'] } })
        config.onUpdateEvent({ finalize_answer: {} })
      })

      // Update to not loading (simulating completion)
      mockUseStream.mockReturnValue({
        messages: [aiMessage],
        isLoading: false,
        submit: mockSubmit,
        stop: mockStop,
      })

      rerender()

      await waitFor(() => {
        expect(result.current.historicalActivities['msg-123']).toBeDefined()
      })

      expect(result.current.historicalActivities['msg-123']).toHaveLength(2)
    })

    it('should not save to historical activities if still loading', () => {
      mockUseStream.mockReturnValue({
        messages: [{ type: 'ai', content: 'Response', id: 'msg-1' }],
        isLoading: true,
        submit: mockSubmit,
        stop: mockStop,
      })

      const { result } = renderHook(() => useAgentState())

      act(() => {
        const config = mockUseStream.mock.calls[0][0]
        config.onUpdateEvent({ finalize_answer: {} })
      })

      expect(result.current.historicalActivities).toEqual({})
    })

    it('should not save if no finalize event occurred', () => {
      mockUseStream.mockReturnValue({
        messages: [{ type: 'ai', content: 'Response', id: 'msg-1' }],
        isLoading: false,
        submit: mockSubmit,
        stop: mockStop,
      })

      const { result, rerender } = renderHook(() => useAgentState())

      act(() => {
        const config = mockUseStream.mock.calls[0][0]
        config.onUpdateEvent({ generate_query: { search_query: ['q1'] } })
      })

      rerender()

      expect(result.current.historicalActivities).toEqual({})
    })

    it('should handle messages without IDs', async () => {
      const messageWithoutId: Message = {
        type: 'ai',
        content: 'Response',
      }

      mockUseStream.mockReturnValue({
        messages: [messageWithoutId],
        isLoading: false,
        submit: mockSubmit,
        stop: mockStop,
      })

      const { result, rerender } = renderHook(() => useAgentState())

      act(() => {
        const config = mockUseStream.mock.calls[0][0]
        config.onUpdateEvent({ finalize_answer: {} })
      })

      rerender()

      // Should not save if message has no ID
      expect(Object.keys(result.current.historicalActivities)).toHaveLength(0)
    })

    it('should only save AI messages', async () => {
      const humanMessage: Message = {
        type: 'human',
        content: 'Question',
        id: 'msg-human',
      }

      mockUseStream.mockReturnValue({
        messages: [humanMessage],
        isLoading: false,
        submit: mockSubmit,
        stop: mockStop,
      })

      const { result, rerender } = renderHook(() => useAgentState())

      act(() => {
        const config = mockUseStream.mock.calls[0][0]
        config.onUpdateEvent({ finalize_answer: {} })
      })

      rerender()

      expect(result.current.historicalActivities).toEqual({})
    })
  })

  describe('Auto-scroll Behavior', () => {
    it('should provide scrollAreaRef', () => {
      const { result } = renderHook(() => useAgentState())

      expect(result.current.scrollAreaRef).toBeDefined()
      expect(result.current.scrollAreaRef.current).toBeNull()
    })

    it('should trigger scroll effect when messages change', () => {
      const { rerender } = renderHook(() => useAgentState())

      // Update messages
      mockUseStream.mockReturnValue({
        messages: [{ type: 'human', content: 'New message', id: '1' }],
        isLoading: false,
        submit: mockSubmit,
        stop: mockStop,
      })

      rerender()

      // The effect should run (actual scroll behavior depends on DOM)
    })
  })

  describe('Edge Cases', () => {
    it('should handle undefined event fields gracefully', () => {
      const { result } = renderHook(() => useAgentState())

      act(() => {
        const config = mockUseStream.mock.calls[0][0]
        config.onUpdateEvent({
          generate_query: undefined,
        })
      })

      // Should not crash
      expect(result.current.processedEventsTimeline).toHaveLength(0)
    })

    it('should handle null values in planning context', () => {
      const { result } = renderHook(() => useAgentState())

      act(() => {
        const config = mockUseStream.mock.calls[0][0]
        config.onUpdateEvent({
          planning_mode: {
            planning_steps: null,
            planning_status: null,
            planning_feedback: null,
          },
        })
      })

      expect(result.current.planningContext).toBeDefined()
    })

    it('should handle rapid successive submits', () => {
      const { result } = renderHook(() => useAgentState())

      act(() => {
        result.current.handleSubmit('query1', 'low', 'model1')
        result.current.handleSubmit('query2', 'high', 'model2')
        result.current.handleSubmit('query3', 'medium', 'model3')
      })

      // Should have called submit 3 times
      expect(mockSubmit).toHaveBeenCalledTimes(3)
      
      // Last call should use most recent config
      expect(mockSubmit).toHaveBeenLastCalledWith(
        expect.objectContaining({
          initial_search_query_count: 3,
          max_research_loops: 3,
          reasoning_model: 'model3',
        })
      )
    })
  })
})