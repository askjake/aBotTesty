// AppsItem.test.tsx
import React from 'react';
import { screen } from '@testing-library/react';

import { AppsItemProps } from '@/components/molecules/Apps/AppsItem/AppsItem.props';
import renderLayout from '@shared/jest-config/__mocks__/utils/renderLayout';
import AppsItem from '@/components/molecules/Apps/AppsItem';

// Mock Next.js Image component
jest.mock('next/image', () => ({
  __esModule: true,
  default: (props: any) => {
    // eslint-disable-next-line @next/next/no-img-element, jsx-a11y/alt-text
    return <img {...props} />;
  },
}));

describe('AppsItem Component', () => {
  const defaultProps: AppsItemProps = {
    name: 'Test App',
    path: '/test-app',
    image: '/img/test-app.png',
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders correctly with all props', () => {
    renderLayout(<AppsItem {...defaultProps} />);

    // Check if link is rendered with correct href
    const link = screen.getByRole('link');
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute('href', '/test-app');

    // Check if image is rendered with correct attributes
    const image = screen.getByAltText('Test App');
    expect(image).toBeInTheDocument();
    expect(image).toHaveAttribute('src', '/img/test-app.png');
    expect(image).toHaveAttribute('width', '55');
    expect(image).toHaveAttribute('height', '45');

    // Check if name is rendered
    expect(screen.getByText('Test App')).toBeInTheDocument();
  });

  it('renders with default image when image prop is not provided', () => {
    const propsWithoutImage = {
      name: 'Test App',
      path: '/test-app',
    };

    // @ts-ignore
    renderLayout(<AppsItem {...propsWithoutImage} />);

    const image = screen.getByAltText('Test App');
    expect(image).toHaveAttribute('src', '/img/logo.png');
  });

  it('renders with empty name when name prop is not provided', () => {
    const propsWithoutName = {
      path: '/test-app',
      image: '/img/test-app.png',
    };

    // @ts-ignore
    renderLayout(<AppsItem {...propsWithoutName} />);

    const image = screen.getByAltText('');
    expect(image).toBeInTheDocument();
  });

  it('applies custom className correctly', () => {
    const customClassName = 'custom-class';
    const propsWithClassName = {
      ...defaultProps,
      className: customClassName,
    };

    const { container } = renderLayout(<AppsItem {...propsWithClassName} />);

    const card = container.querySelector('.apps-item');
    expect(card).toHaveClass('apps-item');
    expect(card).toHaveClass(customClassName);
  });

  it('applies default className when className prop is not provided', () => {
    const { container } = renderLayout(<AppsItem {...defaultProps} />);

    const card = container.querySelector('.apps-item');
    expect(card).toBeInTheDocument();
  });

  it('passes additional CardProps to Card component', () => {
    const propsWithCardProps = {
      ...defaultProps,
      'data-testid': 'custom-card',
      style: { backgroundColor: 'red' },
    };

    renderLayout(<AppsItem {...propsWithCardProps} />);

    const card = screen.getByTestId('custom-card');
    expect(card).toBeInTheDocument();
    expect(card).toHaveStyle({ backgroundColor: 'red' });
  });

  it('renders Card with hoverable prop', () => {
    const { container } = renderLayout(<AppsItem {...defaultProps} />);

    const card = container.querySelector('.ant-card-hoverable');
    expect(card).toBeInTheDocument();
  });

  it('renders with correct link structure', () => {
    renderLayout(<AppsItem {...defaultProps} />);

    const link = screen.getByRole('link');
    expect(link).toContainElement(screen.getByText('Test App'));
    expect(link).toContainElement(screen.getByAltText('Test App'));
  });

  it('handles special characters in name prop', () => {
    const propsWithSpecialChars = {
      ...defaultProps,
      name: 'Test & App <Special>',
    };

    renderLayout(<AppsItem {...propsWithSpecialChars} />);

    expect(screen.getByText('Test & App <Special>')).toBeInTheDocument();
    expect(screen.getByAltText('Test & App <Special>')).toBeInTheDocument();
  });

  it('handles long path URLs correctly', () => {
    const propsWithLongPath = {
      ...defaultProps,
      path: '/very/long/path/to/application/page',
    };

    renderLayout(<AppsItem {...propsWithLongPath} />);

    const link = screen.getByRole('link');
    expect(link).toHaveAttribute('href', '/very/long/path/to/application/page');
  });

  it('handles external URLs in path', () => {
    const propsWithExternalPath = {
      ...defaultProps,
      path: 'https://external-app.com',
    };

    renderLayout(<AppsItem {...propsWithExternalPath} />);

    const link = screen.getByRole('link');
    expect(link).toHaveAttribute('href', 'https://external-app.com');
  });

  it('renders Flex component with correct layout', () => {
    const { container } = renderLayout(<AppsItem {...defaultProps} />);

    const flex = container.querySelector('.ant-flex-vertical');
    expect(flex).toBeInTheDocument();
  });

  it('maintains image dimensions', () => {
    renderLayout(<AppsItem {...defaultProps} />);

    const image = screen.getByAltText('Test App');
    expect(image).toHaveAttribute('width', '55');
    expect(image).toHaveAttribute('height', '45');
  });

  it('renders multiple AppsItem components independently', () => {
    const { rerender } = renderLayout(<AppsItem {...defaultProps} />);

    expect(screen.getByText('Test App')).toBeInTheDocument();

    const secondProps = {
      name: 'Second App',
      path: '/second-app',
      image: '/img/second-app.png',
    };

    rerender(
      <>
        <AppsItem {...defaultProps} />
        <AppsItem {...secondProps} />
      </>,
    );

    expect(screen.getByText('Test App')).toBeInTheDocument();
    expect(screen.getByText('Second App')).toBeInTheDocument();
  });

  it('renders link element in DOM', () => {
    const { container } = renderLayout(<AppsItem {...defaultProps} />);

    const link = container.querySelector('a');
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute('href', '/test-app');
  });

  it('card is wrapped inside a link', () => {
    const { container } = renderLayout(<AppsItem {...defaultProps} />);

    const link = container.querySelector('a');
    const card = container.querySelector('.ant-card');

    // @ts-ignore
    expect(link).toContainElement(card);
  });
});
