import React from 'react';
import renderLayout from '@shared/jest-config/__mocks__/utils/renderLayout';
import UserAvatar from '@shared/ui/components/atoms/Avatars/UserAvatar';
import { screen } from '@testing-library/react';
describe('UserAvatar Component', () => {
  it('renders without crashing', () => {
    renderLayout(<UserAvatar userEmail='john.doe@example.com' />);
    expect(screen.getByTestId('user-avatar')).toBeInTheDocument();
  });

  it('displays the initials of the user email', () => {
    renderLayout(<UserAvatar userEmail='jane.smith@example.com' />);
    expect(screen.getByTestId('user-avatar')).toHaveTextContent('JS');
  });

  it('displays nothing if no email is provided', () => {
    renderLayout(<UserAvatar userEmail='' />);
    const avatar = screen.getByTestId('user-avatar');
    expect(avatar.textContent).toBe('');
  });

  it('applies custom className', () => {
    renderLayout(
      <UserAvatar userEmail='john.doe@example.com' className='custom-class' />,
    );
    const avatar = screen.getByTestId('user-avatar');
    expect(avatar).toHaveClass('custom-class');
  });

  it('passes additional props to the Avatar component', () => {
    renderLayout(<UserAvatar userEmail='john.doe@example.com' size={64} />);
    const avatar = screen.getByTestId('user-avatar');
    expect(avatar).toHaveAttribute(
      'style',
      expect.stringContaining('width: 64px;'),
    );
    expect(avatar).toHaveAttribute(
      'style',
      expect.stringContaining('height: 64px;'),
    );
  });
});
