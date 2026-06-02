// SearchModal.test.tsx
import React from 'react';
import { screen, fireEvent } from '@testing-library/react';
import SearchModal from '@/components/molecules/Modals/SearchModal';
import { SearchModalProps } from '@/components/molecules/Modals/SearchModal/SearchModal.props';
import renderLayout from '@shared/jest-config/__mocks__/utils/renderLayout';

// Mock dependencies
jest.mock('react-infinite-scroll-component', () => ({
  __esModule: true,
  default: ({ children, loader, hasMore }: any) => (
    <div data-testid='infinite-scroll'>
      {children}
      {hasMore && <div data-testid='loader'>{loader}</div>}
    </div>
  ),
}));

jest.mock('@ant-design/x', () => ({
  Conversations: ({ items, activeKey, onActiveChange }: any) => (
    <div data-testid='conversations'>
      {items.map((item: any) => (
        <div
          key={item.key}
          data-testid={`conversation-item-${item.key}`}
          onClick={() => onActiveChange(item.key)}
          data-active={item.key === activeKey}
        >
          {item.label}
        </div>
      ))}
    </div>
  ),
}));

jest.mock('@shared/ui/utils/messages.utils', () => ({
  groupable: jest.fn((icon) => ({ icon })),
}));

describe('SearchModal Component', () => {
  const mockOnSearchChange = jest.fn();
  const mockOnLoadMore = jest.fn();
  const mockOnActiveKeyChange = jest.fn();

  const mockItems = [
    { key: '1', label: 'Item 1' },
    { key: '2', label: 'Item 2' },
    { key: '3', label: 'Item 3' },
  ];

  const defaultProps: SearchModalProps = {
    open: true,
    onSearchChange: mockOnSearchChange,
    items: mockItems,
    onLoadMore: mockOnLoadMore,
    hasMoreData: false,
    onCancel: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders correctly when open', () => {
    renderLayout(<SearchModal {...defaultProps} />);

    expect(screen.getByTestId('infinite-scroll')).toBeInTheDocument();
    expect(screen.getByTestId('conversations')).toBeInTheDocument();
  });

  it('renders search input with default placeholder', () => {
    renderLayout(<SearchModal {...defaultProps} />);

    expect(screen.getByPlaceholderText('Search items...')).toBeInTheDocument();
  });

  it('calls onSearchChange when typing in search input', () => {
    renderLayout(<SearchModal {...defaultProps} />);

    const searchInput = screen.getByPlaceholderText('Search items...');
    fireEvent.change(searchInput, { target: { value: 'test search' } });

    expect(mockOnSearchChange).toHaveBeenCalledWith('test search');
  });

  it('renders all conversation items', () => {
    renderLayout(<SearchModal {...defaultProps} />);

    expect(screen.getByText('Item 1')).toBeInTheDocument();
    expect(screen.getByText('Item 2')).toBeInTheDocument();
    expect(screen.getByText('Item 3')).toBeInTheDocument();
  });

  it('shows loader when hasMoreData is true', () => {
    renderLayout(<SearchModal {...defaultProps} hasMoreData={true} />);

    expect(screen.getByTestId('loader')).toBeInTheDocument();
  });

  it('calls onActiveKeyChange when conversation item is clicked', () => {
    renderLayout(
      <SearchModal
        {...defaultProps}
        onActiveKeyChange={mockOnActiveKeyChange}
      />,
    );

    fireEvent.click(screen.getByTestId('conversation-item-1'));

    expect(mockOnActiveKeyChange).toHaveBeenCalledWith('1');
  });

  it('does not render when open is false', () => {
    renderLayout(<SearchModal {...defaultProps} open={false} />);

    expect(screen.queryByTestId('infinite-scroll')).not.toBeInTheDocument();
  });
});
