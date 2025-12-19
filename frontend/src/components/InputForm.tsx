import { useState, memo } from "react";
import { Button } from "@/components/ui/button";
import { SquarePen, Brain, Send, StopCircle, Zap, Cpu } from "lucide-react";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

// Updated InputFormProps
interface InputFormProps {
  onSubmit: (inputValue: string, effort: string, model: string) => void;
  onCancel: () => void;
  isLoading: boolean;
  hasHistory: boolean;
}

// ⚡ Bolt Optimization: Memoize InputForm to prevent re-renders on every token update
// caused by parent ChatMessagesView re-rendering.
// Since onSubmit/onCancel are now stable (via useAgentState optimization),
// and isLoading/hasHistory change infrequently, this component will stay idle during streaming.
export const InputForm: React.FC<InputFormProps> = memo(({
  onSubmit,
  onCancel,
  isLoading,
  hasHistory,
}) => {
  const [internalInputValue, setInternalInputValue] = useState("");
  const [effort, setEffort] = useState("medium");
  // Default to gemma-3-27b-it as it is the standard accessible model
  const [model, setModel] = useState("gemma-3-27b-it");

  const handleInternalSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!internalInputValue.trim()) return;
    onSubmit(internalInputValue, effort, model);
    setInternalInputValue("");
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Submit with Ctrl+Enter (Windows/Linux) or Cmd+Enter (Mac)
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      handleInternalSubmit();
    }
  };

  const isSubmitDisabled = !internalInputValue.trim() || isLoading;

  return (
    <form
      onSubmit={handleInternalSubmit}
      className={`flex flex-col gap-2 p-3 pb-4`}
    >
      <div
        className={`flex flex-row items-center justify-between text-white rounded-3xl rounded-bl-sm ${hasHistory ? "rounded-br-sm" : ""
          } break-words min-h-7 bg-neutral-700 px-4 pt-3 `}
      >
        <Textarea
          aria-label="Chat input"
          value={internalInputValue}
          onChange={(e) => setInternalInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Who won the Euro 2024 and scored the most goals?"
          className={`w-full text-neutral-100 placeholder-neutral-500 resize-none border-0 focus:outline-none focus:ring-0 outline-none focus-visible:ring-2 focus-visible:ring-neutral-500 shadow-none
                        md:text-base  min-h-[56px] max-h-[200px]`}
          rows={1}
        />
        <div className="-mt-3">
          {isLoading ? (
            <Button
              type="button"
              variant="ghost"
              size="icon"
              aria-label="Stop generating"
              className="text-red-500 hover:text-red-400 hover:bg-red-500/10 p-2 cursor-pointer rounded-full transition-all duration-200"
              onClick={onCancel}
            >
              <StopCircle className="h-5 w-5" />
            </Button>
          ) : (
            <Button
              type="submit"
              variant="ghost"
              className={`${isSubmitDisabled
                ? "text-neutral-500"
                : "text-blue-500 hover:text-blue-400 hover:bg-blue-500/10"
                } p-2 cursor-pointer rounded-full transition-all duration-200 text-base`}
              disabled={isSubmitDisabled}
            >
              Search
              <Send className="h-5 w-5" />
            </Button>
          )}
        </div>
      </div>
      <div className="flex items-center justify-between">
        <div className="flex flex-row gap-2">
          <div className="flex flex-row gap-2 bg-neutral-700 border-neutral-600 text-neutral-300 rounded-xl rounded-t-sm pl-2  max-w-[100%] sm:max-w-[90%]">
            <label htmlFor="effort-select" className="flex flex-row items-center text-sm cursor-pointer">
              <Brain className="h-4 w-4 mr-2" />
              Effort
            </label>
            <Select value={effort} onValueChange={setEffort}>
              <SelectTrigger id="effort-select" aria-label="Effort selection" className="w-[120px] bg-transparent border-none cursor-pointer focus-visible:ring-2 focus-visible:ring-neutral-500">
                <SelectValue placeholder="Effort" />
              </SelectTrigger>
              <SelectContent className="bg-neutral-700 border-neutral-600 text-neutral-300 cursor-pointer">
                <SelectItem
                  value="low"
                  className="hover:bg-neutral-600 focus:bg-neutral-600 cursor-pointer"
                >
                  Low
                </SelectItem>
                <SelectItem
                  value="medium"
                  className="hover:bg-neutral-600 focus:bg-neutral-600 cursor-pointer"
                >
                  Medium
                </SelectItem>
                <SelectItem
                  value="high"
                  className="hover:bg-neutral-600 focus:bg-neutral-600 cursor-pointer"
                >
                  High
                </SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="flex flex-row gap-2 bg-neutral-700 border-neutral-600 text-neutral-300 rounded-xl rounded-t-sm pl-2  max-w-[100%] sm:max-w-[90%]">
            <label htmlFor="model-select" className="flex flex-row items-center text-sm ml-2 cursor-pointer">
              <Cpu className="h-4 w-4 mr-2" />
              Model
            </label>
            <Select value={model} onValueChange={setModel}>
              <SelectTrigger id="model-select" aria-label="Model selection" className="w-[150px] bg-transparent border-none cursor-pointer focus-visible:ring-2 focus-visible:ring-neutral-500">
                <SelectValue placeholder="Model" />
              </SelectTrigger>
              <SelectContent className="bg-neutral-700 border-neutral-600 text-neutral-300 cursor-pointer">
                <SelectItem
                  value="gemini-2.5-flash"
                  className="hover:bg-neutral-600 focus:bg-neutral-600 cursor-pointer"
                >
                  <div className="flex items-center">
                    <Zap className="h-4 w-4 mr-2 text-orange-400" /> 2.5 Flash
                  </div>
                </SelectItem>
                <SelectItem
                  value="gemini-2.5-pro"
                  className="hover:bg-neutral-600 focus:bg-neutral-600 cursor-pointer"
                >
                  <div className="flex items-center">
                    <Cpu className="h-4 w-4 mr-2 text-purple-400" /> 2.5 Pro
                  </div>
                </SelectItem>
                <SelectItem
                  value="gemma-3-27b-it"
                  className="hover:bg-neutral-600 focus:bg-neutral-600 cursor-pointer"
                >
                  <div className="flex items-center">
                    <Brain className="h-4 w-4 mr-2 text-blue-400" /> Gemma 3
                  </div>
                </SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        {hasHistory && (
          <Button
            className="bg-neutral-700 border-neutral-600 text-neutral-300 cursor-pointer rounded-xl rounded-t-sm pl-2 "
            variant="default"
            onClick={() => window.location.reload()}
          >
            <SquarePen size={16} />
            New Search
          </Button>
        )}
      </div>
    </form>
  );
});

InputForm.displayName = "InputForm";
