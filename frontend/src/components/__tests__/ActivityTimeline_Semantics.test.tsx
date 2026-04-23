import { render, screen, fireEvent } from '@testing-library/react';
import { ActivityTimeline } from '../ActivityTimeline';
import { describe, it, expect } from 'vitest';

describe('ActivityTimeline Semantics', () => {
  it('renders a list of events using semantic ul and li elements', () => {
    const events = [
      { title: 'Event 1', data: 'Data 1' },
      { title: 'Event 2', data: 'Data 2' },
    ];

    render(<ActivityTimeline processedEvents={events} isLoading={false} />);

    // The timeline collapses by default when data is present and not loading.
    // We need to expand it to see the content.
    const button = screen.getByRole('button', { name: /research activity/i });
    fireEvent.click(button);

    // Check for the list role. This will fail if the container is a div.
    const list = screen.getByRole('list');
    expect(list).toBeInTheDocument();

    // Check for list items. This will fail if items are divs.
    const listItems = screen.getAllByRole('listitem');
    expect(listItems).toHaveLength(2);
    expect(listItems[0]).toHaveTextContent('Event 1');
    expect(listItems[1]).toHaveTextContent('Event 2');
  });
});
