import { useState, useRef, useCallback, useEffect } from "react";
import { useStream } from "@langchain/langgraph-sdk/react";
import type { Message } from "@langchain/langgraph-sdk";
import { ProcessedEvent } from "@/components/ActivityTimeline";

export function useAgentState() {
  const [processedEventsTimeline, setProcessedEventsTimeline] = useState<
    ProcessedEvent[]
  >([]);
  const [historicalActivities, setHistoricalActivities] = useState<
    Record<string, ProcessedEvent[]>
  >({});
  const [planningContext, setPlanningContext] = useState<{
    steps: any[];
    status?: string | null;
    feedback?: string[];
  } | null>(null);

  const [error, setError] = useState<string | null>(null);
  const hasFinalizeEventOccurredRef = useRef(false);
  const scrollAreaRef = useRef<HTMLDivElement>(null);

  // Default configuration
  const lastConfigRef = useRef({
    initial_search_query_count: 1,
    max_research_loops: 1,
    reasoning_model: "gemini-1.5-flash",
  });

  const thread = useStream<{
    messages: Message[];
    initial_search_query_count: number;
    max_research_loops: number;
    reasoning_model: string;
  }>({
    apiUrl: import.meta.env.VITE_API_URL || (import.meta.env.DEV
      ? "http://localhost:2024"
      : "http://localhost:8123"),
    assistantId: "agent",
    messagesKey: "messages",
    onUpdateEvent: (event: any) => {
      let processedEvent: ProcessedEvent | null = null;
      if (event.generate_query) {
        processedEvent = {
          title: "Generating Search Queries",
          data: event.generate_query?.search_query?.join(", ") || "",
        };
      } else if (event.planning_mode) {
        setPlanningContext({
          steps: event.planning_mode.planning_steps || [],
          status: event.planning_mode.planning_status,
          feedback: event.planning_mode.planning_feedback || [],
        });
      } else if (event.planning_wait) {
        setPlanningContext((prev) => ({
          steps: prev?.steps || [],
          status: "awaiting_confirmation",
          feedback: event.planning_wait.planning_feedback || [],
        }));
      } else if (event.web_research) {
        const sources = event.web_research.sources_gathered || [];
        const numSources = sources.length;
        const uniqueLabels = [
          ...new Set(sources.map((s: any) => s.label).filter(Boolean)),
        ];
        const exampleLabels = uniqueLabels.slice(0, 3).join(", ");
        setPlanningContext((prev) =>
          prev
            ? {
              ...prev,
              status: "confirmed",
            }
            : prev
        );
        processedEvent = {
          title: "Web Research",
          data: `Gathered ${numSources} sources. Related to ${exampleLabels || "N/A"
            }.`,
        };
      } else if (event.reflection) {
        processedEvent = {
          title: "Reflection",
          data: "Analysing Web Research Results",
        };
      } else if (event.finalize_answer) {
        processedEvent = {
          title: "Finalizing Answer",
          data: "Composing and presenting the final answer.",
        };
        hasFinalizeEventOccurredRef.current = true;
      }
      if (processedEvent) {
        setProcessedEventsTimeline((prevEvents) => [
          ...prevEvents,
          processedEvent!,
        ]);
      }
    },
    onError: (error: any) => {
      setError(error.message);
    },
  });

  // Auto-scroll logic
  useEffect(() => {
    if (scrollAreaRef.current) {
      const scrollViewport = scrollAreaRef.current.querySelector(
        "[data-radix-scroll-area-viewport]"
      );
      if (scrollViewport) {
        scrollViewport.scrollTop = scrollViewport.scrollHeight;
      }
    }
  }, [thread.messages]);

  // Historical activity tracking
  useEffect(() => {
    if (
      hasFinalizeEventOccurredRef.current &&
      !thread.isLoading &&
      thread.messages.length > 0
    ) {
      const lastMessage = thread.messages[thread.messages.length - 1];
      if (lastMessage && lastMessage.type === "ai" && lastMessage.id) {
        setHistoricalActivities((prev) => ({
          ...prev,
          [lastMessage.id!]: [...processedEventsTimeline],
        }));
      }
      hasFinalizeEventOccurredRef.current = false;
    }
  }, [thread.messages, thread.isLoading, processedEventsTimeline]);

  const handleSubmit = useCallback(
    (submittedInputValue: string, effort: string, model: string) => {
      if (!submittedInputValue.trim()) return;
      setProcessedEventsTimeline([]);
      hasFinalizeEventOccurredRef.current = false;

      let initial_search_query_count = 0;
      let max_research_loops = 0;
      switch (effort) {
        case "low":
          initial_search_query_count = 1;
          max_research_loops = 1;
          break;
        case "medium":
          initial_search_query_count = 3;
          max_research_loops = 3;
          break;
        case "high":
          initial_search_query_count = 5;
          max_research_loops = 10;
          break;
      }

      const newMessages: Message[] = [
        ...(thread.messages || []),
        {
          type: "human",
          content: submittedInputValue,
          id: Date.now().toString(),
        },
      ];
      const config = {
        initial_search_query_count,
        max_research_loops,
        reasoning_model: model,
      };
      lastConfigRef.current = config;
      setPlanningContext(null);
      thread.submit({
        messages: newMessages,
        ...config,
      });
    },
    [thread]
  );

  const handlePlanningCommand = useCallback(
    (command: string) => {
      const config = lastConfigRef.current;
      const newMessages: Message[] = [
        ...(thread.messages || []),
        {
          type: "human",
          content: command,
          id: Date.now().toString(),
        },
      ];
      thread.submit({
        messages: newMessages,
        ...config,
      });
    },
    [thread]
  );

  const handleCancel = useCallback(() => {
    thread.stop();
    window.location.reload();
  }, [thread]);

  return {
    thread,
    processedEventsTimeline,
    historicalActivities,
    planningContext,
    error,
    scrollAreaRef,
    handleSubmit,
    handlePlanningCommand,
    handleCancel,
  };
}
