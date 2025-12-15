import React from 'react';

// TODO(priority=Low, complexity=Medium): [Open Canvas] Implement ArtifactView component.
// See docs/tasks/03_OPEN_CANVAS_TASKS.md

interface ArtifactViewProps {
  content: string;
  type: 'markdown' | 'code' | 'text';
  isOpen: boolean;
  onClose: () => void;
}

export const ArtifactView: React.FC<ArtifactViewProps> = ({ content, type, isOpen, onClose }) => {
  if (!isOpen) return null;

  return (
    <div className="artifact-view">
      {/*
        TODO(priority=Low, complexity=Low): Implement split-pane layout support.
        TODO(priority=Low, complexity=Medium): Render content based on type (Markdown vs Code).
        TODO(priority=Low, complexity=Medium): Add edit controls if needed.
      */}
      <div className="artifact-header">
        <h3>Artifact Preview</h3>
        <button onClick={onClose}>Close</button>
      </div>
      <div className="artifact-content">
        {content}
      </div>
    </div>
  );
};
