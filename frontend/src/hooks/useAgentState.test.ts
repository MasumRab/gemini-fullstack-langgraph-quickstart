import { renderHook } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useAgentState } from './useAgentState'

// Mock the SDK hook
vi.mock('@langchain/langgraph-sdk/react', () => ({
  useStream: vi.fn(() => ({
    messages: [],
    isLoading: false,
    submit: vi.fn(),
    stop: vi.fn(),
  })),
}))

describe('useAgentState', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // Basic sanity check that the hook renders without crashing
  it('should render without crashing', () => {
    const { result } = renderHook(() => useAgentState())
    expect(result.current).toBeDefined()
    expect(result.current.thread).toBeDefined()
    expect(result.current.processedEventsTimeline).toEqual([])
    expect(result.current.historicalActivities).toEqual({})
    expect(result.current.planningContext).toBeNull()
    expect(result.current.error).toBeNull()
  })

})
