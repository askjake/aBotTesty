import React from 'react';
import { screen } from '@testing-library/react';
import renderLayout from '@shared/jest-config/__mocks__/utils/renderLayout';
import FavoriteIcon from '@/components/atoms/Icons/FavoriteIcon';

describe('FavoriteIcon Component', () => {
  it('renders an active star icon', () => {
    renderLayout(<FavoriteIcon active={true} />);
    const activeFavoriteIcon = screen.getByTestId('active-star-icon');
    expect(activeFavoriteIcon).toBeInTheDocument();
    expect(activeFavoriteIcon).toHaveClass('star-icon');
  });

  it('renders an inactive star icon', () => {
    renderLayout(<FavoriteIcon active={false} />);
    const inactiveFavoriteIcon = screen.getByTestId('inactive-star-icon');
    expect(inactiveFavoriteIcon).toBeInTheDocument();
    expect(inactiveFavoriteIcon).toHaveClass('star-icon');
  });

  it('renders inactive star icon by default when active prop is not provided', () => {
    // eslint-disable-next-line @typescript-eslint/ban-ts-comment
    // @ts-expect-error
    renderLayout(<FavoriteIcon />);
    const inactiveFavoriteIcon = screen.getByTestId('inactive-star-icon');
    expect(inactiveFavoriteIcon).toBeInTheDocument();
    expect(inactiveFavoriteIcon).toHaveClass('star-icon');
  });

  it('applies custom className to active star icon', () => {
    renderLayout(<FavoriteIcon active={true} className='custom-class' />);
    const activeFavoriteIcon = screen.getByTestId('active-star-icon');
    expect(activeFavoriteIcon).toHaveClass('star-icon');
    expect(activeFavoriteIcon).toHaveClass('custom-class');
  });

  it('applies custom className to inactive star icon', () => {
    renderLayout(<FavoriteIcon active={false} className='custom-class' />);
    const inactiveFavoriteIcon = screen.getByTestId('inactive-star-icon');
    expect(inactiveFavoriteIcon).toHaveClass('star-icon');
    expect(inactiveFavoriteIcon).toHaveClass('custom-class');
  });

  it('applies base className by default', () => {
    renderLayout(<FavoriteIcon active={true} />);
    const activeFavoriteIcon = screen.getByTestId('active-star-icon');
    expect(activeFavoriteIcon).toHaveClass('star-icon');
    // Just verify it has the base class, don't test the exact className string
    // since styled-components may modify it
  });

  it('passes additional props to the active star icon', () => {
    renderLayout(<FavoriteIcon active={true} data-size='24' />);
    const activeFavoriteIcon = screen.getByTestId('active-star-icon');
    expect(activeFavoriteIcon).toHaveAttribute('data-size', '24');
  });

  it('passes additional props to the inactive star icon', () => {
    renderLayout(<FavoriteIcon active={false} data-size='24' />);
    const inactiveFavoriteIcon = screen.getByTestId('inactive-star-icon');
    expect(inactiveFavoriteIcon).toHaveAttribute('data-size', '24');
  });

  it('passes multiple additional props correctly', () => {
    renderLayout(
      <FavoriteIcon
        active={true}
        data-size='24'
        data-color='red'
        id='test-icon'
        aria-label='Favorite this item'
      />,
    );
    const activeFavoriteIcon = screen.getByTestId('active-star-icon');
    expect(activeFavoriteIcon).toHaveAttribute('data-size', '24');
    expect(activeFavoriteIcon).toHaveAttribute('data-color', 'red');
    expect(activeFavoriteIcon).toHaveAttribute('id', 'test-icon');
    expect(activeFavoriteIcon).toHaveAttribute(
      'aria-label',
      'Favorite this item',
    );
  });

  it('does not render both icons simultaneously', () => {
    renderLayout(<FavoriteIcon active={true} />);

    expect(screen.getByTestId('active-star-icon')).toBeInTheDocument();
    expect(screen.queryByTestId('inactive-star-icon')).not.toBeInTheDocument();
  });

  it('switches between active and inactive states correctly', () => {
    const { rerender } = renderLayout(<FavoriteIcon active={false} />);

    // Initially inactive
    expect(screen.getByTestId('inactive-star-icon')).toBeInTheDocument();
    expect(screen.queryByTestId('active-star-icon')).not.toBeInTheDocument();

    // Rerender as active
    rerender(<FavoriteIcon active={true} />);
    expect(screen.getByTestId('active-star-icon')).toBeInTheDocument();
    expect(screen.queryByTestId('inactive-star-icon')).not.toBeInTheDocument();
  });

  it('maintains className consistency between active and inactive states', () => {
    const customClass = 'my-custom-class';

    const { rerender } = renderLayout(
      <FavoriteIcon active={false} className={customClass} />,
    );

    // Check inactive state
    const inactiveIcon = screen.getByTestId('inactive-star-icon');
    expect(inactiveIcon).toHaveClass('star-icon');
    expect(inactiveIcon).toHaveClass(customClass);

    // Rerender as active
    rerender(<FavoriteIcon active={true} className={customClass} />);

    // Check active state
    const activeIcon = screen.getByTestId('active-star-icon');
    expect(activeIcon).toHaveClass('star-icon');
    expect(activeIcon).toHaveClass(customClass);
  });

  it('handles boolean active prop correctly', () => {
    // Test with explicit boolean values
    const { rerender } = renderLayout(<FavoriteIcon active={Boolean(1)} />);
    expect(screen.getByTestId('active-star-icon')).toBeInTheDocument();

    rerender(<FavoriteIcon active={Boolean(0)} />);
    expect(screen.getByTestId('inactive-star-icon')).toBeInTheDocument();
  });

  it('handles undefined className gracefully', () => {
    renderLayout(<FavoriteIcon active={true} className={undefined} />);
    const activeFavoriteIcon = screen.getByTestId('active-star-icon');
    expect(activeFavoriteIcon).toHaveClass('star-icon');
    // Should handle undefined className without breaking
    expect(activeFavoriteIcon).toBeInTheDocument();
  });

  it('preserves data attributes correctly', () => {
    renderLayout(<FavoriteIcon active={true} data-custom='test-value' />);
    const activeFavoriteIcon = screen.getByTestId('active-star-icon');

    // Should have both the component's data-testid and custom data attribute
    expect(activeFavoriteIcon).toHaveAttribute(
      'data-testid',
      'active-star-icon',
    );
    expect(activeFavoriteIcon).toHaveAttribute('data-custom', 'test-value');
  });

  it('applies styled components correctly', () => {
    const { rerender } = renderLayout(<FavoriteIcon active={true} />);
    const activeIcon = screen.getByTestId('active-star-icon');

    // The styled component should be applied (we can't test the actual styles in jsdom,
    // but we can verify the component renders with the expected structure)
    expect(activeIcon.tagName).toBeDefined();

    rerender(<FavoriteIcon active={false} />);
    const inactiveIcon = screen.getByTestId('inactive-star-icon');
    expect(inactiveIcon.tagName).toBeDefined();
  });

  it('renders with proper component structure', () => {
    renderLayout(<FavoriteIcon active={true} />);
    const activeIcon = screen.getByTestId('active-star-icon');

    // Verify the component renders as expected
    expect(activeIcon).toBeInTheDocument();
    expect(activeIcon).toHaveClass('star-icon');
  });

  it('handles props spreading correctly', () => {
    const customProps = {
      'data-test': 'value',
      'aria-hidden': 'true',
      role: 'img',
    };
    // eslint-disable-next-line @typescript-eslint/ban-ts-comment
    // @ts-expect-error
    renderLayout(<FavoriteIcon active={true} {...customProps} />);
    const activeIcon = screen.getByTestId('active-star-icon');

    expect(activeIcon).toHaveAttribute('data-test', 'value');
    expect(activeIcon).toHaveAttribute('aria-hidden', 'true');
    expect(activeIcon).toHaveAttribute('role', 'img');
  });

  it('maintains correct test ids for both states', () => {
    const { rerender } = renderLayout(<FavoriteIcon active={true} />);

    // Active state
    expect(screen.getByTestId('active-star-icon')).toBeInTheDocument();
    expect(screen.queryByTestId('inactive-star-icon')).not.toBeInTheDocument();

    // Switch to inactive state
    rerender(<FavoriteIcon active={false} />);
    expect(screen.getByTestId('inactive-star-icon')).toBeInTheDocument();
    expect(screen.queryByTestId('active-star-icon')).not.toBeInTheDocument();
  });

  it('handles edge case with null className', () => {
    renderLayout(<FavoriteIcon active={true} className={null as any} />);
    const activeFavoriteIcon = screen.getByTestId('active-star-icon');
    expect(activeFavoriteIcon).toBeInTheDocument();
    expect(activeFavoriteIcon).toHaveClass('star-icon');
  });

  it('handles edge case with empty string className', () => {
    renderLayout(<FavoriteIcon active={true} className='' />);
    const activeFavoriteIcon = screen.getByTestId('active-star-icon');
    expect(activeFavoriteIcon).toBeInTheDocument();
    expect(activeFavoriteIcon).toHaveClass('star-icon');
  });
});
