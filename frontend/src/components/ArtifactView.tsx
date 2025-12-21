import React from 'react';

// TODO: [Open Canvas] Implement ArtifactView component.
// See docs/tasks/03_OPEN_CANVAS_TASKS.md

interface ArtifactViewProps {
  content: string;
  type: 'markdown' | 'code' | 'text';
  isOpen: boolean;
  onClose: () => void;
}

export const ArtifactView: React.FC<ArtifactViewProps> = ({ content, isOpen, onClose }) => {
  if (!isOpen) return null;

  return (
    <div className="artifact-view">
      {/*
        TODO: Implement split-pane layout support.
        TODO: Render content based on type (Markdown vs Code).
        TODO: Add edit controls if needed.
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
