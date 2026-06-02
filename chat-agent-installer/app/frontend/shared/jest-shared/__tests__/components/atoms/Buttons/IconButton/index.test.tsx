import React from 'react';
import { screen } from '@testing-library/react';
import renderLayout from '@shared/jest-config/__mocks__/utils/renderLayout';
import IconButton from '@shared/ui/components/atoms/Buttons/IconButton';

describe('IconButton Component', () => {
  it('renderLayouts without crashing', () => {
    renderLayout(<IconButton />);
    expect(screen.getByRole('button')).toBeInTheDocument();
  });

  it('passes additional props to the Button component', () => {
    renderLayout(<IconButton size='large' />);
    const button = screen.getByRole('button');
    // Check if the button has the correct size by checking its class or style
    expect(button).toHaveClass('ant-btn-lg'); // Assuming antd adds a class for size large
  });
});
