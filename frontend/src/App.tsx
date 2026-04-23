import { WelcomeScreen } from "@/components/WelcomeScreen";
import { ChatMessagesView } from "@/components/ChatMessagesView";
import { Button } from "@/components/ui/button";
import { useAgentState } from "@/hooks/useAgentState";
import { ArtifactView } from "@/components/ArtifactView";

export default function App() {
  const {
    thread,
    processedEventsTimeline,
    historicalActivities,
    planningContext,
    artifacts,
    isArtifactOpen,
    error,
    scrollAreaRef,
    handleSubmit,
    handlePlanningCommand,
    handleCancel,
    setIsArtifactOpen,
  } = useAgentState();

  // Get the latest artifact
  const latestArtifactId = Object.keys(artifacts).pop();
  const latestArtifact = latestArtifactId ? artifacts[latestArtifactId] : null;

  return (
    <div className="flex h-screen bg-neutral-900 text-neutral-100 font-sans antialiased overflow-hidden">
      {/* Sidebar/Left panel could go here if needed in future */}

      {/* Main Content Area */}
      <main className={`flex-1 flex flex-col transition-all duration-300 ease-in-out ${isArtifactOpen ? 'mr-0 md:mr-[40%] lg:mr-[30%] xl:mr-[25%]' : ''
        }`}>
        <div className="h-full w-full max-w-4xl mx-auto px-4 overflow-hidden flex flex-col">
          {thread.messages.length === 0 ? (
            <WelcomeScreen
              handleSubmit={handleSubmit}
              isLoading={thread.isLoading}
              onCancel={handleCancel}
            />
          ) : error ? (
            <div className="flex flex-col items-center justify-center h-full">
              <div className="flex flex-col items-center justify-center gap-4 bg-red-500/10 border border-red-500/20 p-8 rounded-2xl">
                <h1 className="text-2xl text-red-400 font-bold">Error Encountered</h1>
                <p className="text-red-400/80 text-center max-w-md">{JSON.stringify(error)}</p>

                <Button
                  variant="destructive"
                  onClick={() => window.location.reload()}
                  className="mt-4"
                >
                  Retry Session
                </Button>
              </div>
            </div>
          ) : (
            <div className="flex-1 flex flex-col min-h-0">
              <ChatMessagesView
                messages={thread.messages}
                isLoading={thread.isLoading}
                scrollAreaRef={scrollAreaRef}
                onSubmit={handleSubmit}
                onCancel={handleCancel}
                liveActivityEvents={processedEventsTimeline}
                historicalActivities={historicalActivities}
                planningContext={planningContext}
                onSendCommand={handlePlanningCommand}
              />
            </div>
          )}
        </div>
      </main>

      {/* Artifact Panel */}
      {latestArtifact && (
        <ArtifactView
          isOpen={isArtifactOpen}
          onClose={() => setIsArtifactOpen(false)}
          content={latestArtifact.content}
          type={latestArtifact.type as 'markdown' | 'code' | 'text'}
          title={latestArtifact.title}
        />
      )}
    </div>
  );
}
