import React from 'react';
import { render, screen } from '@testing-library/react';
import HomeTemplate from '@/components/templates/HomeTemplate';

// Mock dependencies
jest.mock('next/dynamic', () => {
  return jest.fn(() => {
    const MockChat = () => (
      <div data-testid='chat-component'>Chat Component</div>
    );
    return MockChat;
  });
});

jest.mock('@/components/templates/HomeTemplate/HomeTemplate.styled', () => ({
  StyledHomeLayout: ({ children }: { children: React.ReactNode }) => (
    <div data-testid='styled-home-layout'>{children}</div>
  ),
}));

jest.mock('@/components/containers/ContainerWithSidebar', () => {
  return ({
    children,
    showChats,
  }: {
    children: React.ReactNode;
    showChats?: boolean;
  }) => (
    <div data-testid='container-with-sidebar' data-show-chats={showChats}>
      {children}
    </div>
  );
});

describe('HomeTemplate', () => {
  it('should render with correct structure and props', () => {
    render(<HomeTemplate />);

    // Check main structure
    expect(screen.getByTestId('container-with-sidebar')).toBeInTheDocument();
    expect(screen.getByTestId('styled-home-layout')).toBeInTheDocument();
    expect(screen.getByTestId('chat-component')).toBeInTheDocument();

    // Check props
    const container = screen.getByTestId('container-with-sidebar');
    expect(container).toHaveAttribute('data-show-chats', 'true');
  });

  it('should have correct component hierarchy', () => {
    render(<HomeTemplate />);

    const container = screen.getByTestId('container-with-sidebar');
    const styledLayout = screen.getByTestId('styled-home-layout');
    const chatComponent = screen.getByTestId('chat-component');

    expect(container).toContainElement(styledLayout);
    expect(styledLayout).toContainElement(chatComponent);
  });
});
