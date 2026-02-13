import { renderHook, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach, Mock } from 'vitest'
import { useAgentState } from './useAgentState'
import { useStream } from '@langchain/langgraph-sdk/react'

// Mock the SDK hook
vi.mock('@langchain/langgraph-sdk/react', () => ({
  useStream: vi.fn(),
}))

// Mock window.location.reload
const originalLocation = window.location;
const mockReload = vi.fn();

describe('useAgentState', () => {
  let mockSubmit: Mock;
  let mockStop: Mock;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let mockUseStreamConfig: any;

  beforeEach(() => {
    vi.clearAllMocks();
    mockSubmit = vi.fn();
    mockStop = vi.fn();

    // Setup window.location mock
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    delete (window as any).location;
    window.location = { ...originalLocation, reload: mockReload };

    // Setup useStream mock to capture config and return mock thread
    (useStream as Mock).mockImplementation((config) => {
      mockUseStreamConfig = config;
      return {
        messages: [],
        isLoading: false,
        submit: mockSubmit,
        stop: mockStop,
      };
    });
  })

  afterEach(() => {
    window.location = originalLocation;
  });

  it('should render with initial state', () => {
    const { result } = renderHook(() => useAgentState())
    expect(result.current.processedEventsTimeline).toEqual([])
    expect(result.current.historicalActivities).toEqual({})
    expect(result.current.planningContext).toBeNull()
    expect(result.current.error).toBeNull()
    expect(result.current.isArtifactOpen).toBe(false)
  })

  it('should handle generate_query event', () => {
    const { result } = renderHook(() => useAgentState())

    act(() => {
      mockUseStreamConfig.onUpdateEvent({
        generate_query: { search_query: ['query1', 'query2'] }
      })
    })

    expect(result.current.processedEventsTimeline).toHaveLength(1)
    expect(result.current.processedEventsTimeline[0]).toEqual({
      title: 'Generating Search Queries',
      data: 'query1, query2',
    })
  })

  it('should handle outline_gen event', () => {
    const { result } = renderHook(() => useAgentState())

    act(() => {
      mockUseStreamConfig.onUpdateEvent({
        outline_gen: { outline: { title: 'My Outline' } }
      })
    })

    expect(result.current.processedEventsTimeline).toHaveLength(1)
    expect(result.current.processedEventsTimeline[0]).toEqual({
      title: 'Research Outline generated',
      data: 'My Outline',
    })
  })

  it('should handle planning_mode event', () => {
    const { result } = renderHook(() => useAgentState())

    act(() => {
      mockUseStreamConfig.onUpdateEvent({
        planning_mode: {
          planning_steps: ['step1'],
          planning_status: 'in_progress',
          planning_feedback: ['feedback1']
        }
      })
    })

    expect(result.current.planningContext).toEqual({
      steps: ['step1'],
      status: 'in_progress',
      feedback: ['feedback1'],
    })
  })

  it('should handle web_research event', () => {
    const { result } = renderHook(() => useAgentState())

    // First set some planning context to verify status update
    act(() => {
      mockUseStreamConfig.onUpdateEvent({
        planning_mode: { planning_steps: [], planning_status: 'pending' }
      })
    })

    act(() => {
      mockUseStreamConfig.onUpdateEvent({
        web_research: {
          sources_gathered: [
            { label: 'Source A' },
            { label: 'Source B' }
          ]
        }
      })
    })

    expect(result.current.processedEventsTimeline).toContainEqual({
      title: 'Web Research',
      data: expect.stringContaining('Gathered 2 sources'),
    })
    expect(result.current.planningContext?.status).toBe('confirmed')
  })

  it('should handle artifacts event', () => {
    const { result } = renderHook(() => useAgentState())

    act(() => {
      mockUseStreamConfig.onUpdateEvent({
        artifacts: { doc1: 'content' }
      })
    })

    expect(result.current.artifacts).toEqual({ doc1: 'content' })
    expect(result.current.isArtifactOpen).toBe(true)
  })

  it('should handle planning_wait event', () => {
    const { result } = renderHook(() => useAgentState())

    act(() => {
      mockUseStreamConfig.onUpdateEvent({
        planning_wait: { planning_feedback: ['wait feedback'] }
      })
    })

    expect(result.current.planningContext).toEqual({
      steps: [],
      status: 'awaiting_confirmation',
      feedback: ['wait feedback'],
    })
  })

  it('should handle reflection event', () => {
    const { result } = renderHook(() => useAgentState())

    act(() => {
      mockUseStreamConfig.onUpdateEvent({
        reflection: true
      })
    })

    expect(result.current.processedEventsTimeline).toContainEqual({
      title: 'Reflection',
      data: 'Analysing Web Research Results',
    })
  })

  it('should handle denoising_refiner event', () => {
    const { result } = renderHook(() => useAgentState())

    act(() => {
      mockUseStreamConfig.onUpdateEvent({
        denoising_refiner: true
      })
    })

    expect(result.current.processedEventsTimeline).toContainEqual({
      title: 'Finalizing Answer',
      data: 'Synthesizing multiple drafts for high-quality report.',
    })
  })

  it('should handle error in stream', () => {
    const { result } = renderHook(() => useAgentState())

    act(() => {
      mockUseStreamConfig.onError(new Error('Stream failed'))
    })

    expect(result.current.error).toBe('Stream failed')
  })

  it('handleSubmit should call thread.submit with correct config for low effort', () => {
    const { result } = renderHook(() => useAgentState())

    act(() => {
      result.current.handleSubmit('test input', 'low', 'gpt-4')
    })

    expect(mockSubmit).toHaveBeenCalledWith(expect.objectContaining({
      initial_search_query_count: 1,
      max_research_loops: 1,
      reasoning_model: 'gpt-4',
      messages: expect.arrayContaining([
        expect.objectContaining({
          type: 'human',
          content: 'test input'
        })
      ])
    }))
  })

  it('handleSubmit should call thread.submit with correct config for high effort', () => {
    const { result } = renderHook(() => useAgentState())

    act(() => {
      result.current.handleSubmit('test input', 'high', 'gpt-4')
    })

    expect(mockSubmit).toHaveBeenCalledWith(expect.objectContaining({
      initial_search_query_count: 5,
      max_research_loops: 10,
    }))
  })

  it('handlePlanningCommand should call thread.submit with correct config', () => {
    const { result } = renderHook(() => useAgentState())

    // First submit to set lastConfig
    act(() => {
      result.current.handleSubmit('initial', 'low', 'gpt-4')
    })
    mockSubmit.mockClear()

    act(() => {
      result.current.handlePlanningCommand('yes')
    })

    expect(mockSubmit).toHaveBeenCalledWith(expect.objectContaining({
      initial_search_query_count: 1, // from 'low'
      max_research_loops: 1,
      reasoning_model: 'gpt-4',
      messages: expect.arrayContaining([
        expect.objectContaining({
          type: 'human',
          content: 'yes'
        })
      ])
    }))
  })

  it('handleCancel should stop thread and reload page', () => {
    const { result } = renderHook(() => useAgentState())

    act(() => {
      result.current.handleCancel()
    })

    expect(mockStop).toHaveBeenCalled()
    expect(mockReload).toHaveBeenCalled()
  })

  it('should auto-scroll when messages update', () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let mockMessages: any[] = [];
    (useStream as Mock).mockImplementation((config) => {
      mockUseStreamConfig = config;
      return {
        messages: mockMessages,
        isLoading: false,
        submit: mockSubmit,
        stop: mockStop,
      };
    });

    const { result, rerender } = renderHook(() => useAgentState())

    const mockScrollArea = document.createElement('div');
    const mockViewport = document.createElement('div');
    mockViewport.setAttribute('data-radix-scroll-area-viewport', '');
    Object.defineProperty(mockViewport, 'scrollHeight', { value: 500, writable: true });
    // Allow scrollTop to be written
    Object.defineProperty(mockViewport, 'scrollTop', { value: 0, writable: true });

    mockScrollArea.appendChild(mockViewport);

    // Assign ref
    // eslint-disable-next-line @typescript-eslint/ban-ts-comment
    // @ts-ignore
    result.current.scrollAreaRef.current = mockScrollArea;

    // Update messages and rerender
    mockMessages = [{ type: 'ai', content: 'new message', id: '1' }];
    rerender();

    expect(mockViewport.scrollTop).toBe(500);
  })

  it('should update historicalActivities when thread finishes', () => {
    // Setup mock to return messages
    (useStream as Mock).mockImplementation((config) => {
      mockUseStreamConfig = config;
      return {
        messages: [{ type: 'ai', id: 'msg-123', content: 'done' }],
        isLoading: false,
        submit: mockSubmit,
        stop: mockStop,
      };
    });

    const { result, rerender } = renderHook(() => useAgentState())

    // Simulate an event that marks finalization
    act(() => {
      mockUseStreamConfig.onUpdateEvent({
        finalize_answer: true
      })
    })

    // Rerender to trigger effect
    rerender()

    expect(result.current.historicalActivities['msg-123']).toBeDefined()
    expect(result.current.historicalActivities['msg-123'][0].title).toBe('Finalizing Answer')
  })
})
