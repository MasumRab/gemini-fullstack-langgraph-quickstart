import React, { useState } from 'react';
import { Button } from "@/components/ui/button";
import { X, Copy, Check, Maximize2, Minimize2, FileText, Code as CodeIcon } from "lucide-react";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeSanitize from 'rehype-sanitize';
import rehypeRaw from 'rehype-raw';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { atomDark as highlighterStyle } from 'react-syntax-highlighter/dist/esm/styles/prism';

interface ArtifactViewProps {
  content: string;
  type: 'markdown' | 'code' | 'text';
  title?: string;
  isOpen: boolean;
  onClose: () => void;
}

export const ArtifactView: React.FC<ArtifactViewProps> = ({ content, type, title, isOpen, onClose }) => {
  const [copied, setCopied] = useState(false);
  const [isMaximized, setIsMaximized] = useState(false);

  if (!isOpen) return null;

  const handleCopy = () => {
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const renderContent = () => {
    switch (type) {
      case 'markdown':
        return (
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            rehypePlugins={[rehypeRaw, rehypeSanitize]}
            components={{
              // eslint-disable-next-line @typescript-eslint/no-unused-vars
              h1: ({ node: _node, ...props }) => <h1 className="text-2xl font-bold mt-8 mb-4 text-neutral-100 border-b border-neutral-800 pb-2" {...props} />,
              // eslint-disable-next-line @typescript-eslint/no-unused-vars
              h2: ({ node: _node, ...props }) => <h2 className="text-xl font-semibold mt-6 mb-3 text-neutral-200" {...props} />,
              // eslint-disable-next-line @typescript-eslint/no-unused-vars
              h3: ({ node: _node, ...props }) => <h3 className="text-lg font-medium mt-4 mb-2 text-neutral-300" {...props} />,
              // eslint-disable-next-line @typescript-eslint/no-unused-vars
              p: ({ node: _node, ...props }) => <p className="text-neutral-400 leading-relaxed mb-4 text-sm md:text-base" {...props} />,
              // eslint-disable-next-line @typescript-eslint/no-unused-vars
              ul: ({ node: _node, ...props }) => <ul className="list-disc pl-5 mb-4 space-y-2 text-neutral-400" {...props} />,
              // eslint-disable-next-line @typescript-eslint/no-unused-vars
              ol: ({ node: _node, ...props }) => <ol className="list-decimal pl-5 mb-4 space-y-2 text-neutral-400" {...props} />,
              // eslint-disable-next-line @typescript-eslint/no-unused-vars
              li: ({ node: _node, ...props }) => <li className="text-sm md:text-base" {...props} />,
              // eslint-disable-next-line @typescript-eslint/no-explicit-any, @typescript-eslint/no-unused-vars
              code: ({ node: _node, inline, className, children, ...props }: any) => {
                const match = /language-(\w+)/.exec(className || '');
                return !inline && match ? (
                  <SyntaxHighlighter
                    style={highlighterStyle}
                    language={match[1]}
                    PreTag="div"
                    {...props}
                  >
                    {String(children).replace(/\n$/, '')}
                  </SyntaxHighlighter>
                ) : (
                  <code className="bg-neutral-800 text-blue-400 px-1.5 py-0.5 rounded text-sm" {...props}>
                    {children}
                  </code>
                );
              },
              // eslint-disable-next-line @typescript-eslint/no-unused-vars
              blockquote: ({ node: _node, ...props }) => <blockquote className="border-l-4 border-blue-500/50 pl-4 italic text-neutral-500 my-4" {...props} />,
              // eslint-disable-next-line @typescript-eslint/no-unused-vars
              table: ({ node: _node, ...props }) => <div className="overflow-x-auto my-6"><table className="w-full border-collapse border border-neutral-800 text-sm" {...props} /></div>,
              // eslint-disable-next-line @typescript-eslint/no-unused-vars
              th: ({ node: _node, ...props }) => <th className="border border-neutral-800 bg-neutral-800/50 px-4 py-2 text-left font-semibold" {...props} />,
              // eslint-disable-next-line @typescript-eslint/no-unused-vars
              td: ({ node: _node, ...props }) => <td className="border border-neutral-800 px-4 py-2" {...props} />,
              // eslint-disable-next-line @typescript-eslint/no-unused-vars
              a: ({ node: _node, ...props }) => <a className="text-blue-400 hover:text-blue-300 underline decoration-blue-500/30 underline-offset-4 transition-colors" target="_blank" rel="noopener noreferrer" {...props} />,
            }}
          >
            {content}
          </ReactMarkdown>
        );
      case 'code':
        return (
          <SyntaxHighlighter
            style={highlighterStyle}
            language="javascript" // Default to javascript, could be dynamic
            showLineNumbers={true}
            className="rounded-xl"
          >
            {content}
          </SyntaxHighlighter>
        );
      case 'text':
      default:
        return (
          <div className="whitespace-pre-wrap text-neutral-400 font-sans text-sm md:text-base leading-relaxed">
            {content}
          </div>
        );
    }
  };

  return (
    <div className={`fixed inset-y-0 right-0 z-50 flex flex-col bg-neutral-900 border-l border-neutral-800 shadow-2xl transition-all duration-300 ease-in-out ${isMaximized ? 'left-0' : 'w-full md:w-1/2 lg:w-2/5 xl:w-1/3'
      }`}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-neutral-800 bg-neutral-900/50 backdrop-blur-sm sticky top-0 z-10">
        <div className="flex items-center gap-3 overflow-hidden">
          <div className="p-2 rounded-lg bg-blue-500/10 text-blue-400">
            {type === 'code' ? <CodeIcon size={18} /> : <FileText size={18} />}
          </div>
          <div className="flex flex-col overflow-hidden">
            <h3 className="text-sm font-semibold text-neutral-100 truncate">
              {title || (type === 'code' ? 'Code Artifact' : 'Research Artifact')}
            </h3>
            <span className="text-[10px] uppercase tracking-wider text-neutral-500 font-bold">
              {type}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            onClick={handleCopy}
            className="h-8 w-8 text-neutral-400 hover:text-neutral-100 hover:bg-neutral-800"
            title="Copy content"
          >
            {copied ? <Check size={16} className="text-green-500" /> : <Copy size={16} />}
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setIsMaximized(!isMaximized)}
            className="h-8 w-8 text-neutral-400 hover:text-neutral-100 hover:bg-neutral-800 hidden md:flex"
            title={isMaximized ? "Restore size" : "Maximize"}
          >
            {isMaximized ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
          </Button>
          <div className="w-px h-4 bg-neutral-800 mx-1" />
          <Button
            variant="ghost"
            size="icon"
            onClick={onClose}
            className="h-8 w-8 text-neutral-400 hover:text-red-400 hover:bg-red-500/10"
            title="Close"
          >
            <X size={18} />
          </Button>
        </div>
      </div>

      {/* Content Area */}
      <div className="flex-1 overflow-y-auto custom-scrollbar bg-neutral-900 scroll-smooth">
        <div className="max-w-4xl mx-auto p-6 md:p-8">
          <div className="prose prose-invert prose-blue max-w-none">
            {renderContent()}
          </div>
        </div>
      </div>

      {/* Footer / Status */}
      <div className="px-4 py-2 border-t border-neutral-800 bg-neutral-900/50 flex items-center justify-between">
        <span className="text-[10px] text-neutral-500 uppercase tracking-widest font-medium">
          Last updated: {new Date().toLocaleTimeString()}
        </span>
        <span className="text-[10px] text-blue-500/70 font-medium">
          Generated via SOTA Researcher
        </span>
      </div>
    </div>
  );
};
