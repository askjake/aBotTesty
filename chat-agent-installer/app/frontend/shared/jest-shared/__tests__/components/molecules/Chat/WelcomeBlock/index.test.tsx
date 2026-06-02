import React from 'react';
import { screen } from '@testing-library/react';
import renderLayout from '@shared/jest-config/__mocks__/utils/renderLayout';
import WelcomeBlock from '@shared/ui/components/molecules/Chat/WelcomeBlock';

// Mock Next.js Image component
jest.mock('next/image', () => {
  return function MockImage({
    src,
    alt,
    width,
    height,
    quality,
    ...props
  }: any) {
    return (
      <img
        src={src}
        alt={alt}
        width={width}
        height={height}
        data-quality={quality}
        data-testid='welcome-image'
        {...props}
      />
    );
  };
});

// Mock Ant Design X components
jest.mock('@ant-design/x', () => ({
  Welcome: ({
    variant,
    icon,
    title,
    description,
    className,
    ...props
  }: any) => (
    <div
      data-testid='welcome-component'
      className={className}
      data-variant={variant}
      data-title={title}
      data-description={description}
      {...props}
    >
      <div data-testid='welcome-icon'>{icon}</div>
      <div data-testid='welcome-title'>{title}</div>
      <div data-testid='welcome-description'>{description}</div>
    </div>
  ),
}));

// Mock styled component - Now properly mocking the styled Welcome component
jest.mock(
  '@shared/ui/components/molecules/Chat/WelcomeBlock/WelcomeBlock.styled',
  () => ({
    StyledWelcomeBlock: ({ children, ...props }: any) => {
      const { Welcome } = require('@ant-design/x');
      return (
        <div data-testid='styled-welcome-block' className='ant-welcome'>
          <Welcome {...props}>{children}</Welcome>
        </div>
      );
    },
  }),
);

describe('WelcomeBlock', () => {
  describe('Rendering', () => {
    it('renders the component with default props', () => {
      renderLayout(<WelcomeBlock />);

      expect(screen.getByTestId('styled-welcome-block')).toBeInTheDocument();
      expect(screen.getByTestId('welcome-component')).toBeInTheDocument();
      expect(screen.getByTestId('welcome-image')).toBeInTheDocument();
      expect(screen.getByTestId('welcome-title')).toHaveTextContent(
        "Hello, I'm Dish Chat",
      );
      expect(screen.getByTestId('welcome-description')).toHaveTextContent(
        'How can I help you today?',
      );
    });

    it('renders with correct variant', () => {
      renderLayout(<WelcomeBlock />);

      const welcomeComponent = screen.getByTestId('welcome-component');
      expect(welcomeComponent).toHaveAttribute('data-variant', 'borderless');
    });

    it('renders with ant-welcome class', () => {
      renderLayout(<WelcomeBlock />);

      const styledWelcomeBlock = screen.getByTestId('styled-welcome-block');
      expect(styledWelcomeBlock).toHaveClass('ant-welcome');
    });

    it('renders with custom className passed to Welcome component', () => {
      renderLayout(<WelcomeBlock className='custom-class' />);

      const welcomeComponent = screen.getByTestId('welcome-component');
      expect(welcomeComponent).toHaveClass('welcome-block custom-class');
    });

    it('renders with empty className when not provided', () => {
      renderLayout(<WelcomeBlock className='' />);

      const welcomeComponent = screen.getByTestId('welcome-component');
      expect(welcomeComponent).toHaveClass('welcome-block');
    });
  });

  describe('Image Component', () => {
    it('renders image with correct src', () => {
      renderLayout(<WelcomeBlock />);

      const image = screen.getByTestId('welcome-image');
      expect(image).toHaveAttribute('src', '/img/logo.png');
    });

    it('renders image with correct alt text', () => {
      renderLayout(<WelcomeBlock />);

      const image = screen.getByTestId('welcome-image');
      expect(image).toHaveAttribute('alt', 'logo');
    });

    it('renders image with correct dimensions', () => {
      renderLayout(<WelcomeBlock />);

      const image = screen.getByTestId('welcome-image');
      expect(image).toHaveAttribute('width', '85');
      expect(image).toHaveAttribute('height', '64');
    });

    it('renders image with correct quality', () => {
      renderLayout(<WelcomeBlock />);

      const image = screen.getByTestId('welcome-image');
      expect(image).toHaveAttribute('data-quality', '100');
    });
  });

  describe('Content', () => {
    it('displays correct title', () => {
      renderLayout(<WelcomeBlock />);

      const welcomeComponent = screen.getByTestId('welcome-component');
      expect(welcomeComponent).toHaveAttribute(
        'data-title',
        "Hello, I'm Dish Chat",
      );
    });

    it('displays correct description', () => {
      renderLayout(<WelcomeBlock />);

      const welcomeComponent = screen.getByTestId('welcome-component');
      expect(welcomeComponent).toHaveAttribute(
        'data-description',
        'How can I help you today?',
      );
    });
  });

  describe('Props Forwarding', () => {
    it('forwards additional props to Welcome component', () => {
      const customProps = {
        'data-custom': 'test-value',
        id: 'welcome-block-id',
      };

      renderLayout(<WelcomeBlock {...customProps} />);

      const welcomeComponent = screen.getByTestId('welcome-component');
      expect(welcomeComponent).toHaveAttribute('data-custom', 'test-value');
      expect(welcomeComponent).toHaveAttribute('id', 'welcome-block-id');
    });

    it('handles multiple custom props', () => {
      const customProps = {
        'data-testprop': 'value1',
        'aria-label': 'Welcome section',
        role: 'banner',
      };

      renderLayout(<WelcomeBlock {...customProps} />);

      const welcomeComponent = screen.getByTestId('welcome-component');
      expect(welcomeComponent).toHaveAttribute('data-testprop', 'value1');
      expect(welcomeComponent).toHaveAttribute('aria-label', 'Welcome section');
      expect(welcomeComponent).toHaveAttribute('role', 'banner');
    });
  });

  describe('Component Structure', () => {
    it('renders icon within the welcome block', () => {
      renderLayout(<WelcomeBlock />);

      const iconContainer = screen.getByTestId('welcome-icon');
      const image = screen.getByTestId('welcome-image');

      expect(iconContainer).toBeInTheDocument();
      expect(iconContainer).toContainElement(image);
    });

    it('maintains proper component hierarchy', () => {
      renderLayout(<WelcomeBlock />);

      const styledWelcomeBlock = screen.getByTestId('styled-welcome-block');
      const welcomeComponent = screen.getByTestId('welcome-component');
      const icon = screen.getByTestId('welcome-icon');
      const title = screen.getByTestId('welcome-title');
      const description = screen.getByTestId('welcome-description');

      expect(styledWelcomeBlock).toContainElement(welcomeComponent);
      expect(welcomeComponent).toContainElement(icon);
      expect(welcomeComponent).toContainElement(title);
      expect(welcomeComponent).toContainElement(description);
    });
  });

  describe('Accessibility', () => {
    it('renders image with proper alt text for accessibility', () => {
      renderLayout(<WelcomeBlock />);

      const image = screen.getByAltText('logo');
      expect(image).toBeInTheDocument();
    });

    it('supports custom accessibility props', () => {
      renderLayout(
        // eslint-disable-next-line @typescript-eslint/ban-ts-comment
        // @ts-expect-error
        <WelcomeBlock aria-label='Welcome to Dish Chat' role='banner' />,
      );

      const welcomeComponent = screen.getByTestId('welcome-component');
      expect(welcomeComponent).toHaveAttribute(
        'aria-label',
        'Welcome to Dish Chat',
      );
      expect(welcomeComponent).toHaveAttribute('role', 'banner');
    });
  });

  describe('Theme Integration', () => {
    it('renders correctly with light theme', () => {
      renderLayout(<WelcomeBlock />, { theme: 'light' });

      expect(screen.getByTestId('styled-welcome-block')).toBeInTheDocument();
      expect(screen.getByTestId('welcome-component')).toBeInTheDocument();
      expect(screen.getByTestId('welcome-image')).toBeInTheDocument();
    });

    it('renders correctly with dark theme', () => {
      renderLayout(<WelcomeBlock />, { theme: 'dark' });

      expect(screen.getByTestId('styled-welcome-block')).toBeInTheDocument();
      expect(screen.getByTestId('welcome-component')).toBeInTheDocument();
      expect(screen.getByTestId('welcome-image')).toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    it('handles undefined className gracefully', () => {
      renderLayout(<WelcomeBlock className={undefined as any} />);

      const welcomeComponent = screen.getByTestId('welcome-component');
      // When className is undefined, template literal results in "welcome-block " (with trailing space)
      expect(welcomeComponent).toHaveAttribute('class', 'welcome-block ');
    });

    it('handles null className gracefully', () => {
      renderLayout(<WelcomeBlock className={null as any} />);

      const welcomeComponent = screen.getByTestId('welcome-component');
      expect(welcomeComponent).toHaveAttribute('class', 'welcome-block null');
    });

    it('handles multiple spaces in className', () => {
      renderLayout(<WelcomeBlock className='  multiple   spaces  ' />);

      const welcomeComponent = screen.getByTestId('welcome-component');
      expect(welcomeComponent).toHaveAttribute(
        'class',
        'welcome-block   multiple   spaces  ',
      );
    });
  });

  describe('Component Props Interface', () => {
    it('accepts WelcomeProps interface properties', () => {
      const welcomeProps = {
        className: 'test-class',
        style: { backgroundColor: 'red' },
      };

      renderLayout(<WelcomeBlock {...welcomeProps} />);

      const welcomeComponent = screen.getByTestId('welcome-component');
      expect(welcomeComponent).toHaveClass('welcome-block test-class');
      expect(welcomeComponent).toHaveStyle('background-color: red');
    });
  });

  describe('Styled Component Behavior', () => {
    it('applies styled component wrapper with ant-welcome class', () => {
      renderLayout(<WelcomeBlock />);

      const styledWrapper = screen.getByTestId('styled-welcome-block');
      expect(styledWrapper).toHaveClass('ant-welcome');
    });

    it('renders the underlying Welcome component within styled wrapper', () => {
      renderLayout(<WelcomeBlock />);

      const styledWrapper = screen.getByTestId('styled-welcome-block');
      const welcomeComponent = screen.getByTestId('welcome-component');

      expect(styledWrapper).toContainElement(welcomeComponent);
    });
  });
});
