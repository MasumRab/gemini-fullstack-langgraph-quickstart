import type React from "react";
import type { Message } from "@langchain/langgraph-sdk";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Loader2, Copy, CopyCheck } from "lucide-react";
import { InputForm } from "@/components/InputForm";
import { Button } from "@/components/ui/button";
import { useState, ReactNode, memo, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import {
  ActivityTimeline,
  ProcessedEvent,
} from "@/components/ActivityTimeline";

// Markdown component props type from former ReportView
type MdComponentProps = {
  className?: string;
  children?: ReactNode;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  [key: string]: any;
};

// Markdown components (from former ReportView.tsx)
const mdComponents = {
  h1: ({ className, children, ...props }: MdComponentProps) => (
    <h1 className={cn("text-2xl font-bold mt-4 mb-2", className)} {...props}>
      {children}
    </h1>
  ),
  h2: ({ className, children, ...props }: MdComponentProps) => (
    <h2 className={cn("text-xl font-bold mt-3 mb-2", className)} {...props}>
      {children}
    </h2>
  ),
  h3: ({ className, children, ...props }: MdComponentProps) => (
    <h3 className={cn("text-lg font-bold mt-3 mb-1", className)} {...props}>
      {children}
    </h3>
  ),
  p: ({ className, children, ...props }: MdComponentProps) => (
    <p className={cn("mb-3 leading-7", className)} {...props}>
      {children}
    </p>
  ),
  a: ({ className, children, href, ...props }: MdComponentProps) => (
    <Badge className="text-xs mx-0.5" asChild>
      <a
        className={cn(
          "text-blue-400 hover:text-blue-300 text-xs focus-visible:ring-2 focus-visible:ring-neutral-500 rounded-sm",
          className
        )}
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        {...props}
      >
        {children}
        <span className="sr-only">(opens in a new tab)</span>
      </a>
    </Badge>
  ),
  ul: ({ className, children, ...props }: MdComponentProps) => (
    <ul className={cn("list-disc pl-6 mb-3", className)} {...props}>
      {children}
    </ul>
  ),
  ol: ({ className, children, ...props }: MdComponentProps) => (
    <ol className={cn("list-decimal pl-6 mb-3", className)} {...props}>
      {children}
    </ol>
  ),
  li: ({ className, children, ...props }: MdComponentProps) => (
    <li className={cn("mb-1", className)} {...props}>
      {children}
    </li>
  ),
  blockquote: ({ className, children, ...props }: MdComponentProps) => (
    <blockquote
      className={cn(
        "border-l-4 border-neutral-600 pl-4 italic my-3 text-sm",
        className
      )}
      {...props}
    >
      {children}
    </blockquote>
  ),
  code: ({ className, children, ...props }: MdComponentProps) => (
    <code
      className={cn(
        "bg-neutral-900 rounded px-1 py-0.5 font-mono text-xs",
        className
      )}
      {...props}
    >
      {children}
    </code>
  ),
  pre: ({ className, children, ...props }: MdComponentProps) => (
    <pre
      className={cn(
        "bg-neutral-900 p-3 rounded-lg overflow-x-auto font-mono text-xs my-3",
        className
      )}
      {...props}
    >
      {children}
    </pre>
  ),
  hr: ({ className, ...props }: MdComponentProps) => (
    <hr className={cn("border-neutral-600 my-4", className)} {...props} />
  ),
  table: ({ className, children, ...props }: MdComponentProps) => (
    <div className="my-3 overflow-x-auto">
      <table className={cn("border-collapse w-full", className)} {...props}>
        {children}
      </table>
    </div>
  ),
  th: ({ className, children, ...props }: MdComponentProps) => (
    <th
      className={cn(
        "border border-neutral-600 px-3 py-2 text-left font-bold",
        className
      )}
      {...props}
    >
      {children}
    </th>
  ),
  td: ({ className, children, ...props }: MdComponentProps) => (
    <td
      className={cn("border border-neutral-600 px-3 py-2", className)}
      {...props}
    >
      {children}
    </td>
  ),
};

// ⚡ Bolt Optimization: Define remark plugins as a constant to ensure referential stability.
const markdownPlugins = [remarkGfm];

// Props for HumanMessageBubble
interface HumanMessageBubbleProps {
  message: Message;
  mdComponents: typeof mdComponents;
}

// ⚡ Bolt Optimization: Custom comparator to ignore object reference changes
// when content and ID are identical (crucial for streaming lists).
function areHumanMessageBubblePropsEqual(
  prev: HumanMessageBubbleProps,
  next: HumanMessageBubbleProps
) {
  return (
    prev.message.id === next.message.id &&
    prev.message.content === next.message.content &&
    prev.message.type === next.message.type &&
    prev.mdComponents === next.mdComponents
  );
}

// ⚡ Bolt Optimization: Memoize to prevent unnecessary re-renders of historical messages
const HumanMessageBubble: React.FC<HumanMessageBubbleProps> = memo(({
  message,
  mdComponents,
}: HumanMessageBubbleProps) => {
  return (
    <div
      className={`text-white rounded-3xl break-words min-h-7 bg-neutral-700 max-w-[100%] sm:max-w-[90%] px-4 pt-3 rounded-br-lg`}
    >
      <ReactMarkdown components={mdComponents} remarkPlugins={markdownPlugins}>
        {typeof message.content === "string"
          ? message.content
          : JSON.stringify(message.content)}
      </ReactMarkdown>
    </div>
  );
}, areHumanMessageBubblePropsEqual);
HumanMessageBubble.displayName = "HumanMessageBubble";

// Props for AiMessageBubble
interface AiMessageBubbleProps {
  message: Message;
  historicalActivity: ProcessedEvent[] | undefined;
  liveActivity: ProcessedEvent[] | undefined;
  isLastMessage: boolean;
  isOverallLoading: boolean;
  mdComponents: typeof mdComponents;
  handleCopy: (text: string, messageId: string) => void;
  isCopied: boolean;
}

// ⚡ Bolt Optimization: Custom comparator for AI bubbles.
// Explicitly checks primitive values and specific props to avoid re-rendering
// when the parent passes new message objects with identical content.
function areAiMessageBubblePropsEqual(
  prev: AiMessageBubbleProps,
  next: AiMessageBubbleProps
) {
  return (
    prev.message.id === next.message.id &&
    prev.message.content === next.message.content &&
    prev.isLastMessage === next.isLastMessage &&
    prev.isOverallLoading === next.isOverallLoading &&
    prev.isCopied === next.isCopied &&
    prev.historicalActivity === next.historicalActivity &&
    prev.liveActivity === next.liveActivity &&
    prev.handleCopy === next.handleCopy &&
    prev.mdComponents === next.mdComponents
  );
}

// ⚡ Bolt Optimization: Memoize to prevent unnecessary re-renders of historical messages
const AiMessageBubble: React.FC<AiMessageBubbleProps> = memo(({
  message,
  historicalActivity,
  liveActivity,
  isLastMessage,
  isOverallLoading,
  mdComponents,
  handleCopy,
  isCopied,
}: AiMessageBubbleProps) => {
  // Determine which activity events to show and if it's for a live loading message
  const activityForThisBubble =
    isLastMessage && isOverallLoading ? liveActivity : historicalActivity;
  const isLiveActivityForThisBubble = isLastMessage && isOverallLoading;

  return (
    <div className={`relative break-words flex flex-col`}>
      {activityForThisBubble && activityForThisBubble.length > 0 && (
        <div className="mb-3 border-b border-neutral-700 pb-3 text-xs">
          <ActivityTimeline
            processedEvents={activityForThisBubble}
            isLoading={isLiveActivityForThisBubble}
          />
        </div>
      )}
      <ReactMarkdown components={mdComponents} remarkPlugins={markdownPlugins}>
        {typeof message.content === "string"
          ? message.content
          : JSON.stringify(message.content)}
      </ReactMarkdown>
      <Button
        variant="default"
        className={`cursor-pointer bg-neutral-700 border-neutral-600 text-neutral-300 self-end focus-visible:ring-2 focus-visible:ring-neutral-500 ${message.content.length > 0 ? "visible" : "hidden"
          }`}
        onClick={() =>
          handleCopy(
            typeof message.content === "string"
              ? message.content
              : JSON.stringify(message.content),
            message.id!
          )
        }
      >
        {isCopied ? "Copied" : "Copy"}
        {isCopied ? <CopyCheck aria-hidden="true" /> : <Copy aria-hidden="true" />}
      </Button>
    </div>
  );
}, areAiMessageBubblePropsEqual);
AiMessageBubble.displayName = "AiMessageBubble";

// ⚡ Bolt Optimization: Extracted MessageItem with purely derived props.
// By accepting 'isLast', 'liveActivity', and 'isOverallLoading' (calculated by parent),
// this component now has stable props for all historical messages, guaranteeing that
// React.memo will skip re-renders during streaming updates.
interface MessageItemProps {
  message: Message;
  isLast: boolean;
  liveActivity: ProcessedEvent[] | undefined;
  historicalActivities: Record<string, ProcessedEvent[]>;
  isOverallLoading: boolean;
  copiedMessageId: string | null;
  handleCopy: (text: string, messageId: string) => void;
  mdComponents: typeof mdComponents;
}

function areMessageItemPropsEqual(
  prev: MessageItemProps,
  next: MessageItemProps
) {
  return (
    prev.message.id === next.message.id &&
    prev.message.content === next.message.content &&
    prev.message.type === next.message.type &&
    prev.isLast === next.isLast &&
    prev.isOverallLoading === next.isOverallLoading &&
    prev.copiedMessageId === next.copiedMessageId &&
    prev.liveActivity === next.liveActivity &&
    prev.historicalActivities === next.historicalActivities &&
    prev.handleCopy === next.handleCopy &&
    prev.mdComponents === next.mdComponents
  );
}

const MessageItem = memo(({
  message,
  isLast,
  liveActivity,
  historicalActivities,
  isOverallLoading,
  copiedMessageId,
  handleCopy,
  mdComponents,
}: MessageItemProps) => {
  return (
    <div className="space-y-3">
      <div
        className={`flex items-start gap-3 ${message.type === "human" ? "justify-end" : ""
          }`}
      >
        {message.type === "human" ? (
          <HumanMessageBubble
            message={message}
            mdComponents={mdComponents}
          />
        ) : (
          <AiMessageBubble
            message={message}
            historicalActivity={historicalActivities[message.id!]}
            liveActivity={liveActivity}
            isLastMessage={isLast}
            isOverallLoading={isOverallLoading}
            mdComponents={mdComponents}
            handleCopy={handleCopy}
            isCopied={copiedMessageId === message.id}
          />
        )}
      </div>
    </div>
  );
}, areMessageItemPropsEqual);
MessageItem.displayName = "MessageItem";


interface PlanningContext {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  steps: any[];
  status?: string | null;
  feedback?: string[];
}

interface PlanningStatusProps {
  planningContext: PlanningContext;
  onSendCommand?: (command: string) => void;
}

// ⚡ Bolt Optimization: Memoize PlanningStatus to isolate it from frequent
// message streaming updates in the parent view.
const PlanningStatus = memo(({ planningContext, onSendCommand }: PlanningStatusProps) => {
  return (
    <div className="px-4 pt-4">
      <div
        className="border border-neutral-700 rounded-2xl bg-neutral-900/50 p-4 space-y-3"
        role="region"
        aria-label="Planning Status"
        aria-live="polite"
      >
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-sm text-neutral-400 uppercase tracking-wide">
              Planning Mode
            </p>
            <h3 className="text-lg font-semibold">
              {planningContext.steps?.length
                ? `${planningContext.steps.length} proposed step${planningContext.steps.length > 1 ? "s" : ""}`
                : "Awaiting plan details"}
            </h3>
          </div>
          {planningContext.status && (
            <Badge className="bg-neutral-700 text-xs">
              {planningContext.status}
            </Badge>
          )}
        </div>
        {planningContext.feedback?.length ? (
          <ul className="text-xs text-neutral-400 list-disc pl-4 space-y-1">
            {planningContext.feedback.map((note, idx) => (
              <li key={`feedback-${idx}`}>{note}</li>
            ))}
          </ul>
        ) : null}
        {planningContext.steps?.length ? (
          <ol className="space-y-2">
            {planningContext.steps.map((step, idx) => (
              <li
                key={step.id || `plan-${idx}`}
                className="border border-neutral-700 rounded-xl p-3 text-sm"
              >
                <div className="flex items-center justify-between gap-3">
                  <span className="text-neutral-200 font-medium">
                    {step.title || step.query || `Step ${idx + 1}`}
                  </span>
                  {step.status && (
                    <Badge variant="outline" className="text-xs">
                      {step.status}
                    </Badge>
                  )}
                </div>
                <p className="text-xs text-neutral-400 mt-1">
                  Tool: {step.suggested_tool || "web_research"}
                </p>
              </li>
            ))}
          </ol>
        ) : null}
        {onSendCommand && (
          <div className="flex flex-wrap gap-2 justify-end">
            <Button
              size="sm"
              variant="outline"
              className="focus-visible:ring-2 focus-visible:ring-neutral-500"
              onClick={() => onSendCommand("/plan")}
            >
              Enter Planning
            </Button>
            <Button
              size="sm"
              variant="ghost"
              className="focus-visible:ring-2 focus-visible:ring-neutral-500"
              onClick={() => onSendCommand("/end_plan")}
            >
              Skip Planning
            </Button>
            {planningContext.status === "awaiting_confirmation" && (
              <Button
                size="sm"
                className="focus-visible:ring-2 focus-visible:ring-neutral-500"
                onClick={() => onSendCommand("/confirm_plan")}
              >
                Confirm Plan
              </Button>
            )}
          </div>
        )}
      </div>
    </div>
  );
});
PlanningStatus.displayName = "PlanningStatus";

// ⚡ Bolt Optimization: Extracted PlanningFooter to prevent re-rendering buttons on every token.
interface PlanningFooterProps {
  onSendCommand?: (command: string) => void;
}

const PlanningFooter = memo(({ onSendCommand }: PlanningFooterProps) => {
  if (!onSendCommand) return null;

  return (
    <div className="flex flex-wrap gap-2 justify-end px-4 pb-4 text-xs text-neutral-400">
      <span className="mr-auto">
        Use planning toggles to guide the agent before web research.
      </span>
      <Button
        size="sm"
        variant="outline"
        className="focus-visible:ring-2 focus-visible:ring-neutral-500"
        onClick={() => onSendCommand("/plan")}
      >
        Start Planning
      </Button>
      <Button
        size="sm"
        variant="ghost"
        className="focus-visible:ring-2 focus-visible:ring-neutral-500"
        onClick={() => onSendCommand("/end_plan")}
      >
        End Planning
      </Button>
    </div>
  );
});
PlanningFooter.displayName = "PlanningFooter";

interface ChatMessagesViewProps {
  messages: Message[];
  isLoading: boolean;
  scrollAreaRef: React.RefObject<HTMLDivElement | null>;
  onSubmit: (inputValue: string, effort: string, model: string) => void;
  onCancel: () => void;
  liveActivityEvents: ProcessedEvent[];
  historicalActivities: Record<string, ProcessedEvent[]>;
  planningContext?: PlanningContext | null;
  onSendCommand?: (command: string) => void;
}

export function ChatMessagesView({
  messages,
  isLoading,
  scrollAreaRef,
  onSubmit,
  onCancel,
  liveActivityEvents,
  historicalActivities,
  planningContext,
  onSendCommand,
}: ChatMessagesViewProps) {
  const [copiedMessageId, setCopiedMessageId] = useState<string | null>(null);

  // ⚡ Bolt Optimization: useCallback ensures handleCopy reference remains stable
  const handleCopy = useCallback(async (text: string, messageId: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedMessageId(messageId);
      setTimeout(() => setCopiedMessageId(null), 2000); // Reset after 2 seconds
    } catch (err) {
      console.error("Failed to copy text: ", err);
    }
  }, []); // Empty deps as setCopiedMessageId is stable

  return (
    <div className="flex flex-col h-full">
      {planningContext && (
        <PlanningStatus
          planningContext={planningContext}
          onSendCommand={onSendCommand}
        />
      )}
      <ScrollArea
        className="flex-1 overflow-y-auto"
        ref={scrollAreaRef}
        role="log"
        aria-label="Chat history"
      >
        <div className="p-4 md:p-6 space-y-2 max-w-4xl mx-auto pt-16">
          {messages.map((message, index) => {
            const isLast = index === messages.length - 1;
            // ⚡ Bolt Optimization: Pre-calculate derived props here.
            // Historical messages will receive strict 'false' and 'undefined' values,
            // preventing MessageItem from receiving changed objects (like liveActivityEvents)
            // and bypassing re-renders entirely.
            return (
              <MessageItem
                key={message.id || `msg-${index}`}
                message={message}
                isLast={isLast}
                isOverallLoading={isLast ? isLoading : false}
                liveActivity={isLast ? liveActivityEvents : undefined}
                historicalActivities={historicalActivities}
                copiedMessageId={copiedMessageId}
                handleCopy={handleCopy}
                mdComponents={mdComponents}
              />
            );
          })}
          {isLoading &&
            (messages.length === 0 ||
              messages[messages.length - 1].type === "human") && (
              <div className="flex items-start gap-3 mt-3">
                <div className="relative group max-w-[85%] md:max-w-[80%] rounded-xl p-3 shadow-sm break-words bg-neutral-800 text-neutral-100 rounded-bl-none w-full min-h-[56px]">
                  {liveActivityEvents.length > 0 ? (
                    <div className="text-xs">
                      <ActivityTimeline
                        processedEvents={liveActivityEvents}
                        isLoading={true}
                      />
                    </div>
                  ) : (
                    <div className="flex items-center justify-start h-full" role="status">
                      <Loader2 className="h-5 w-5 animate-spin text-neutral-400 mr-2" aria-hidden="true" />
                      <span>Processing...</span>
                    </div>
                  )}
                </div>
              </div>
            )}
        </div>
      </ScrollArea>
      <InputForm
        onSubmit={onSubmit}
        isLoading={isLoading}
        onCancel={onCancel}
        hasHistory={messages.length > 0}
      />
      <PlanningFooter onSendCommand={onSendCommand} />
    </div>
  );
}
