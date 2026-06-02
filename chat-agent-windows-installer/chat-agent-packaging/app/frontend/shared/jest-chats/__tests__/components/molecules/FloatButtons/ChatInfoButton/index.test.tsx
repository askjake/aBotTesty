import React from 'react';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ChatInfoButton from '@/components/molecules/FloatButtons/ChatInfoButton';
import renderLayout from '@shared/jest-config/__mocks__/utils/renderLayout';

// Mock the ChatInfoDrawer component
jest.mock('@/components/molecules/Drawers/ChatInfoDrawer', () => {
  // eslint-disable-next-line react/display-name
  return ({ open, onClose }: { open: boolean; onClose: () => void }) => (
    <div data-testid='chat-info-drawer'>
      <div data-testid='drawer-open-state'>{open ? 'open' : 'closed'}</div>
      <button data-testid='drawer-close-button' onClick={onClose}>
        Close Drawer
      </button>
    </div>
  );
});

// Mock Ant Design icons
jest.mock('@ant-design/icons', () => ({
  InfoOutlined: () => <span data-testid='info-icon'>Info Icon</span>,
}));

describe('ChatInfoButton', () => {
  it('should render the float button with info icon', () => {
    renderLayout(<ChatInfoButton />);

    expect(screen.getAllByRole('button')).toHaveLength(2); // FloatButton + drawer close button
    expect(screen.getByTestId('info-icon')).toBeInTheDocument();
  });

  it('should initially render drawer as closed', () => {
    renderLayout(<ChatInfoButton />);

    expect(screen.getByTestId('drawer-open-state')).toHaveTextContent('closed');
  });

  it('should open drawer when float button is clicked', async () => {
    const user = userEvent.setup();
    renderLayout(<ChatInfoButton />);

    const floatButton = screen.getAllByRole('button')[0]; // First button is the FloatButton
    // @ts-ignore
    await user.click(floatButton);

    expect(screen.getByTestId('drawer-open-state')).toHaveTextContent('open');
  });

  it('should close drawer when onClose is called', async () => {
    const user = userEvent.setup();
    renderLayout(<ChatInfoButton />);

    // Open the drawer
    const floatButton = screen.getAllByRole('button')[0];
    // @ts-ignore
    await user.click(floatButton);
    expect(screen.getByTestId('drawer-open-state')).toHaveTextContent('open');

    // Close the drawer
    await user.click(screen.getByTestId('drawer-close-button'));
    expect(screen.getByTestId('drawer-open-state')).toHaveTextContent('closed');
  });

  it('should forward props to FloatButton', () => {
    // @ts-ignore
    renderLayout(<ChatInfoButton className='custom-class' disabled={true} />);

    const floatButton = screen.getAllByRole('button')[0];
    expect(floatButton).toHaveClass('custom-class');
    expect(floatButton).toBeDisabled();
  });

  it('should allow custom onClick to override internal handler', async () => {
    const customOnClick = jest.fn();
    const user = userEvent.setup();

    renderLayout(<ChatInfoButton onClick={customOnClick} />);

    const floatButton = screen.getAllByRole('button')[0];
    // @ts-ignore
    await user.click(floatButton);

    // Custom onClick should be called (overrides internal handler)
    expect(customOnClick).toHaveBeenCalled();

    // Drawer should remain closed since custom onClick overrides internal handler
    expect(screen.getByTestId('drawer-open-state')).toHaveTextContent('closed');
  });

  it('should use custom icon when provided', () => {
    const CustomIcon = () => <span data-testid='custom-icon'>Custom</span>;

    renderLayout(<ChatInfoButton icon={<CustomIcon />} />);

    // Should show custom icon since props spread after icon prop
    expect(screen.getByTestId('custom-icon')).toBeInTheDocument();
    expect(screen.queryByTestId('info-icon')).not.toBeInTheDocument();
  });

  it('should use InfoOutlined icon by default', () => {
    renderLayout(<ChatInfoButton />);

    expect(screen.getByTestId('info-icon')).toBeInTheDocument();
  });
});
