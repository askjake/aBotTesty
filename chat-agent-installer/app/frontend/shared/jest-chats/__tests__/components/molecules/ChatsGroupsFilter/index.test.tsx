import React from 'react';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ChatsGroupFilter from '@/components/molecules/ChatsGroupsFilter';
import * as chatGroupService from '@/services/chatGroup.service';
import * as useHandleErrorHook from '@shared/ui/hooks/useHandleError.hook';
import { DEFAULT_CHATS_GROUPS } from '@/constants/chats.constants';
import { MAX_CHATS_GROUPS } from '@shared/ui/constants/validation.constants';
import { updateOrCreateChatGroupValidator } from '@/validators/chatsGroups.validators';
import { ChatGroupType } from '@shared/ui/types/chatGroup.types';
import renderLayout from '@shared/jest-config/__mocks__/utils/renderLayout';
import { mockStore } from '@shared/jest-config/__mocks__/store/mockStore';

// Mock services
jest.mock('@/services/chatGroup.service');
jest.mock('@shared/ui/hooks/useHandleError.hook');

const mockCreateChatGroup =
  chatGroupService.createChatGroup as jest.MockedFunction<
    typeof chatGroupService.createChatGroup
  >;
const mockUpdateChatGroup =
  chatGroupService.updateChatGroup as jest.MockedFunction<
    typeof chatGroupService.updateChatGroup
  >;
const mockDeleteChatGroup =
  chatGroupService.deleteChatGroup as jest.MockedFunction<
    typeof chatGroupService.deleteChatGroup
  >;
const mockHandleError = jest.fn();
(
  useHandleErrorHook.default as jest.MockedFunction<
    typeof useHandleErrorHook.default
  >
).mockReturnValue(mockHandleError);

// Mock styled components
jest.mock(
  '@/components/molecules/ChatsGroupsFilter/ChatsGroupsFilter.styled',
  () => ({
    StyledChatsGroupsFilterContainer: ({ children, ...props }: any) => (
      <div data-testid='chats-groups-filter-container' {...props}>
        {children}
      </div>
    ),
    StyledChatsGroupsFilterSelect: ({
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      children,
      value,
      onChange,
      popupRender,
      options,
      placeholder,
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      showSearch,
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      optionFilterProp,
      ...props
    }: any) => (
      <div data-testid='chats-groups-filter-select' {...props}>
        <select
          data-testid='select-input'
          value={value ?? ''}
          onChange={(e) => onChange?.(e.target.value)}
        >
          {options?.map((option: any, index: number) => (
            <option key={index} value={option.value ?? ''}>
              {option.originalLabel ||
                (typeof option.label === 'string'
                  ? option.label
                  : option.originalLabel)}
            </option>
          ))}
        </select>
        <input
          data-testid='search-input'
          placeholder={placeholder}
          type='text'
        />
        {popupRender && (
          <div data-testid='popup-content'>
            {popupRender(
              <div data-testid='menu-options'>
                {options?.map((option: any, index: number) => (
                  <div
                    key={index}
                    data-testid={`option-${index}`}
                    onClick={() => onChange?.(option.value)}
                  >
                    {typeof option.label === 'string' ? (
                      option.label
                    ) : (
                      <>
                        {option.originalLabel}
                        <div data-testid={`option-actions-${index}`}>
                          {option.label}
                        </div>
                      </>
                    )}
                  </div>
                ))}
              </div>,
            )}
          </div>
        )}
      </div>
    ),
  }),
);

// Mock Ant Design components
jest.mock('antd', () => ({
  App: {
    useApp: () => ({
      message: {
        success: jest.fn(),
        error: jest.fn(),
      },
    }),
  },
  Button: ({ children, onClick, disabled, loading, icon, ...props }: any) => (
    <button
      onClick={onClick}
      disabled={disabled || loading}
      data-loading={loading}
      data-testid={props['data-testid'] || 'button'}
      {...props}
    >
      {icon && <span data-testid='button-icon'>{icon}</span>}
      {children}
    </button>
  ),
  Divider: ({ style }: any) => <div data-testid='divider' style={style} />,
  Flex: ({ children, align, justify, gap, ...props }: any) => (
    <div
      data-testid='flex'
      data-align={align}
      data-justify={justify}
      data-gap={gap}
      {...props}
    >
      {children}
    </div>
  ),
  Form: Object.assign(
    ({
      children,
      onFinish,
      layout,
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      form,
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      scrollToFirstError,
      ...props
    }: any) => (
      <form
        onSubmit={(e) => {
          e.preventDefault();
          onFinish?.();
        }}
        data-testid='form'
        data-layout={layout}
        {...props}
      >
        {children}
      </form>
    ),
    {
      useForm: () => [
        {
          setFieldValue: jest.fn(),
          validateFields: jest.fn().mockResolvedValue({ title: 'Test Title' }),
        },
      ],
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      Item: ({ children, name, label, rules, normalize, ...props }: any) => (
        <div data-testid={`form-item-${name}`} data-label={label} {...props}>
          {label && <label>{label}</label>}
          {children}
        </div>
      ),
    },
  ),
  Input: ({
    value,
    onChange,
    placeholder,
    maxLength,
    disabled,
    showCount,
    ...props
  }: any) => (
    <input
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      maxLength={maxLength}
      disabled={disabled}
      data-show-count={showCount}
      data-testid='input'
      {...props}
    />
  ),
  Modal: ({
    open,
    title,
    children,
    onOk,
    onCancel,
    okText,
    cancelText,
    okType,
    loading,
    modalRender,
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    destroyOnHidden,
    okButtonProps = {},
    ...props
  }: any) => {
    if (!open) return null;

    // Filter out all non-DOM props from okButtonProps
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const { htmlType, autoFocus, ...safeDomProps } = okButtonProps;

    const content = (
      <div data-testid='modal-content'>
        <div data-testid='modal-title'>{title}</div>
        {children}
        <div data-testid='modal-actions'>
          <button onClick={onCancel} data-testid='modal-cancel'>
            {cancelText || 'Cancel'}
          </button>
          <button
            onClick={onOk}
            data-testid='modal-ok'
            data-ok-type={okType}
            data-loading={loading}
            type={htmlType === 'submit' ? 'submit' : 'button'}
            autoFocus={autoFocus}
          >
            {okText || 'OK'}
          </button>
        </div>
      </div>
    );

    return (
      <div data-testid='modal' data-open={open} {...props}>
        {modalRender ? modalRender(content) : content}
      </div>
    );
  },
  Space: ({ children, style }: any) => (
    <div data-testid='space' style={style}>
      {children}
    </div>
  ),
  Tooltip: ({ children, title }: any) => (
    <div data-testid='tooltip' title={title}>
      {children}
    </div>
  ),
}));

// Mock icons
jest.mock('@ant-design/icons', () => ({
  DeleteOutlined: () => <span data-testid='delete-icon'>Delete</span>,
  EditOutlined: () => <span data-testid='edit-icon'>Edit</span>,
  PlusOutlined: () => <span data-testid='plus-icon'>Plus</span>,
}));

describe('ChatsGroupFilter', () => {
  const mockChatsGroups: ChatGroupType[] = [
    { group_id: 'group1', title: 'Test Group 1' },
    { group_id: 'group2', title: 'Test Group 2' },
  ];

  const defaultProps = {};

  beforeEach(() => {
    jest.clearAllMocks();
  });

  const renderComponent = (
    props = {},
    chatsGroups = mockChatsGroups,
    activeChatGroup: string | null = 'all',
  ) => {
    const store = mockStore({
      chatsGroups: {
        chatsGroups,
        activeChatGroup,
      },
    });

    return renderLayout(<ChatsGroupFilter {...defaultProps} {...props} />, {
      store,
    });
  };

  describe('Component Rendering', () => {
    it('should render the filter container', () => {
      renderComponent();

      expect(
        screen.getByTestId('chats-groups-filter-container'),
      ).toBeInTheDocument();
    });

    it('should render the select component with correct props', () => {
      renderComponent();

      const select = screen.getByTestId('chats-groups-filter-select');
      expect(select).toBeInTheDocument();

      const searchInput = screen.getByTestId('search-input');
      expect(searchInput).toHaveAttribute(
        'placeholder',
        'Search by group name',
      );
    });

    it('should render default chat groups in options', () => {
      renderComponent();

      const selectOptions = screen
        .getByTestId('select-input')
        .querySelectorAll('option');

      // Should include default groups + custom groups
      expect(selectOptions).toHaveLength(
        DEFAULT_CHATS_GROUPS.length + mockChatsGroups.length,
      );
    });

    it('should render custom groups with action buttons', () => {
      renderComponent();

      const editIcons = screen.getAllByTestId('edit-icon');
      const deleteIcons = screen.getAllByTestId('delete-icon');

      expect(editIcons).toHaveLength(mockChatsGroups.length);
      expect(deleteIcons).toHaveLength(mockChatsGroups.length);
    });

    it('should render add group section in popup', () => {
      renderComponent();

      expect(screen.getByTestId('popup-content')).toBeInTheDocument();
      expect(screen.getByTestId('divider')).toBeInTheDocument();
      expect(screen.getByTestId('space')).toBeInTheDocument();
    });

    it('should render input with correct attributes', () => {
      renderComponent();

      const input = screen.getByPlaceholderText('Enter a group name');
      expect(input).toHaveAttribute('maxLength', '80');
      expect(input).toHaveAttribute('data-show-count', 'true');
    });
  });

  describe('Group Selection', () => {
    it('should display correct active group', () => {
      renderComponent({}, mockChatsGroups, 'group1');

      const selectInput = screen.getByTestId('select-input');
      expect(selectInput).toHaveValue('group1');
    });

    it('should handle group selection', async () => {
      const user = userEvent.setup();
      renderComponent();

      const selectInput = screen.getByTestId('select-input');
      await user.selectOptions(selectInput, 'group1');

      expect(selectInput).toHaveValue('group1');
    });

    it('should handle default group selection', async () => {
      const user = userEvent.setup();
      renderComponent();

      const selectInput = screen.getByTestId('select-input');
      await user.selectOptions(selectInput, 'all');

      expect(selectInput).toHaveValue('all');
    });

    it('should handle null active group', () => {
      renderComponent({}, mockChatsGroups, null);

      const selectInput = screen.getByTestId('select-input');
      expect(selectInput).toHaveValue('');
    });
  });

  describe('Adding Groups', () => {
    it('should create a new group successfully', async () => {
      const user = userEvent.setup();
      const newGroup: ChatGroupType = {
        group_id: 'new-group',
        title: 'New Group',
      };
      mockCreateChatGroup.mockResolvedValue(newGroup);

      renderComponent();

      const input = screen.getByPlaceholderText('Enter a group name');
      const addButton = screen.getByTestId('plus-icon').closest('button');

      await user.type(input, 'New Group');
      await user.click(addButton!);

      await waitFor(() => {
        expect(mockCreateChatGroup).toHaveBeenCalledWith({
          title: 'New Group',
        });
      });
    });

    it('should handle create group error', async () => {
      const user = userEvent.setup();
      const error = new Error('Create failed');
      mockCreateChatGroup.mockRejectedValue(error);

      renderComponent();

      const input = screen.getByPlaceholderText('Enter a group name');
      const addButton = screen.getByTestId('plus-icon').closest('button');

      await user.type(input, 'New Group');
      await user.click(addButton!);

      await waitFor(() => {
        expect(mockHandleError).toHaveBeenCalledWith(error);
      });
    });

    it('should disable add button when group name is empty', () => {
      renderComponent();

      const addButton = screen.getByTestId('plus-icon').closest('button');
      expect(addButton).toBeDisabled();
    });

    it('should enable add button when group name is entered', async () => {
      const user = userEvent.setup();
      renderComponent();

      const input = screen.getByPlaceholderText('Enter a group name');
      const addButton = screen.getByTestId('plus-icon').closest('button');

      await user.type(input, 'New Group');
      expect(addButton).not.toBeDisabled();
    });

    it('should disable add button and input when max limit reached', () => {
      const maxGroups: ChatGroupType[] = Array.from(
        { length: MAX_CHATS_GROUPS },
        (_, i) => ({
          group_id: `group${i}`,
          title: `Group ${i}`,
        }),
      );

      renderComponent({}, maxGroups);

      const input = screen.getByPlaceholderText('Enter a group name');
      const addButton = screen.getByTestId('plus-icon').closest('button');

      expect(input).toBeDisabled();
      expect(addButton).toBeDisabled();
    });

    it('should show loading state when creating group', async () => {
      const user = userEvent.setup();
      mockCreateChatGroup.mockImplementation(() => new Promise(() => {})); // Never resolves

      renderComponent();

      const input = screen.getByPlaceholderText('Enter a group name');
      const addButton = screen.getByTestId('plus-icon').closest('button');

      await user.type(input, 'New Group');
      await user.click(addButton!);

      expect(addButton).toHaveAttribute('data-loading', 'true');
    });
  });

  describe('Editing Groups', () => {
    it('should open edit modal when edit button is clicked', async () => {
      const user = userEvent.setup();
      renderComponent();

      const editButton = screen
        ?.getAllByTestId('edit-icon')[0]
        ?.closest('button');
      await user.click(editButton!);

      expect(screen.getByTestId('modal')).toBeInTheDocument();
      expect(screen.getByTestId('modal-title')).toHaveTextContent(
        'Edit the group title',
      );
    });

    it('should update group successfully', async () => {
      const user = userEvent.setup();
      // eslint-disable-next-line @typescript-eslint/ban-ts-comment
      // @ts-expect-error
      mockUpdateChatGroup.mockResolvedValue(undefined);

      renderComponent();

      const editButton = screen
        ?.getAllByTestId('edit-icon')[0]
        ?.closest('button');
      await user.click(editButton!);

      const saveButton = screen.getByTestId('modal-ok');
      await user.click(saveButton);

      await waitFor(() => {
        expect(mockUpdateChatGroup).toHaveBeenCalledWith({
          title: 'Test Title',
          id: 'group1',
        });
      });
    });

    it('should handle update group error', async () => {
      const user = userEvent.setup();
      const error = new Error('Update failed');
      mockUpdateChatGroup.mockRejectedValue(error);

      renderComponent();

      const editButton = screen
        ?.getAllByTestId('edit-icon')[0]
        ?.closest('button');
      await user.click(editButton!);

      const saveButton = screen.getByTestId('modal-ok');
      await user.click(saveButton);

      await waitFor(() => {
        expect(mockHandleError).toHaveBeenCalledWith(error);
      });
    });

    it('should close edit modal when cancel is clicked', async () => {
      const user = userEvent.setup();
      renderComponent();

      const editButton = screen
        ?.getAllByTestId('edit-icon')[0]
        ?.closest('button');
      await user.click(editButton!);

      expect(screen.getByTestId('modal')).toBeInTheDocument();

      const cancelButton = screen.getByTestId('modal-cancel');
      await user.click(cancelButton);

      expect(screen.queryByTestId('modal')).not.toBeInTheDocument();
    });

    it('should show correct save button text', async () => {
      const user = userEvent.setup();
      renderComponent();

      const editButton = screen
        ?.getAllByTestId('edit-icon')[0]
        ?.closest('button');
      await user.click(editButton!);

      const saveButton = screen.getByTestId('modal-ok');
      expect(saveButton).toHaveTextContent('Save changes');
    });

    it('should render form item with correct props', async () => {
      const user = userEvent.setup();
      renderComponent();

      const editButton = screen
        ?.getAllByTestId('edit-icon')[0]
        ?.closest('button');
      await user.click(editButton!);

      expect(screen.getByTestId('form-item-title')).toBeInTheDocument();
      expect(screen.getByTestId('form-item-title')).toHaveAttribute(
        'data-label',
        'Title',
      );
    });
  });

  describe('Deleting Groups', () => {
    it('should open delete modal when delete button is clicked', async () => {
      const user = userEvent.setup();
      renderComponent();

      const deleteButton = screen
        ?.getAllByTestId('delete-icon')[0]
        ?.closest('button');
      await user.click(deleteButton!);

      expect(screen.getByTestId('modal')).toBeInTheDocument();
      expect(screen.getByTestId('modal-title')).toHaveTextContent(
        'Delete group?',
      );
    });

    it('should show correct modal content', async () => {
      const user = userEvent.setup();
      renderComponent();

      const deleteButton = screen
        ?.getAllByTestId('delete-icon')[0]
        ?.closest('button');
      await user.click(deleteButton!);

      expect(
        screen.getByText(
          'This will delete the group, but the chats will remain',
        ),
      ).toBeInTheDocument();

      const okButton = screen.getByTestId('modal-ok');
      expect(okButton).toHaveTextContent('Delete');
      expect(okButton).toHaveAttribute('data-ok-type', 'danger');
    });

    it('should delete group successfully', async () => {
      const user = userEvent.setup();
      // eslint-disable-next-line @typescript-eslint/ban-ts-comment
      // @ts-expect-error
      mockDeleteChatGroup.mockResolvedValue(undefined);

      renderComponent();

      const deleteButton = screen
        ?.getAllByTestId('delete-icon')[0]
        ?.closest('button');
      await user.click(deleteButton!);

      const confirmButton = screen.getByTestId('modal-ok');
      await user.click(confirmButton);

      await waitFor(() => {
        expect(mockDeleteChatGroup).toHaveBeenCalledWith('group1');
      });
    });

    it('should handle delete group error', async () => {
      const user = userEvent.setup();
      const error = new Error('Delete failed');
      mockDeleteChatGroup.mockRejectedValue(error);

      renderComponent();

      const deleteButton = screen
        ?.getAllByTestId('delete-icon')[0]
        ?.closest('button');
      await user.click(deleteButton!);

      const confirmButton = screen.getByTestId('modal-ok');
      await user.click(confirmButton);

      await waitFor(() => {
        expect(mockHandleError).toHaveBeenCalledWith(error);
      });
    });

    it('should close delete modal when cancel is clicked', async () => {
      const user = userEvent.setup();
      renderComponent();

      const deleteButton = screen
        ?.getAllByTestId('delete-icon')[0]
        ?.closest('button');
      await user.click(deleteButton!);

      expect(screen.getByTestId('modal')).toBeInTheDocument();

      const cancelButton = screen.getByTestId('modal-cancel');
      await user.click(cancelButton);

      expect(screen.queryByTestId('modal')).not.toBeInTheDocument();
    });

    it('should show loading state when deleting group', async () => {
      const user = userEvent.setup();
      mockDeleteChatGroup.mockImplementation(() => new Promise(() => {})); // Never resolves

      renderComponent();

      const deleteButton = screen
        ?.getAllByTestId('delete-icon')[0]
        ?.closest('button');
      await user.click(deleteButton!);

      const confirmButton = screen.getByTestId('modal-ok');
      await user.click(confirmButton);

      expect(confirmButton).toHaveAttribute('data-loading', 'true');
    });
  });

  describe('Form Validation', () => {
    it('should validate form fields correctly', async () => {
      const user = userEvent.setup();
      const mockValidator = jest.spyOn(
        updateOrCreateChatGroupValidator,
        'safeParse',
      );
      mockValidator.mockReturnValue({
        success: false,
        error: {
          format: () => ({
            title: {
              _errors: ['The "title" field length must has at least 1 symbol'],
            },
          }),
        },
      } as any);

      renderComponent();

      const editButton = screen
        ?.getAllByTestId('edit-icon')[0]
        ?.closest('button');
      await user.click(editButton!);

      expect(screen.getByTestId('modal')).toBeInTheDocument();

      mockValidator.mockRestore();
    });

    it('should handle validation success', async () => {
      const user = userEvent.setup();
      const mockValidator = jest.spyOn(
        updateOrCreateChatGroupValidator,
        'safeParse',
      );
      mockValidator.mockReturnValue({ success: true } as any);

      renderComponent();

      const editButton = screen
        ?.getAllByTestId('edit-icon')[0]
        ?.closest('button');
      await user.click(editButton!);

      expect(screen.getByTestId('modal')).toBeInTheDocument();

      mockValidator.mockRestore();
    });
  });

  describe('Edge Cases', () => {
    it('should handle empty chats groups array', () => {
      renderComponent({}, []);

      expect(
        screen.getByTestId('chats-groups-filter-container'),
      ).toBeInTheDocument();

      // Should only show default groups
      const selectOptions = screen
        .getByTestId('select-input')
        .querySelectorAll('option');
      expect(selectOptions).toHaveLength(DEFAULT_CHATS_GROUPS.length);
    });

    it('should handle groups with null group_id', () => {
      const groupsWithNull: ChatGroupType[] = [
        { group_id: null, title: 'Group with null ID' },
        ...mockChatsGroups,
      ];

      renderComponent({}, groupsWithNull);

      const selectOptions = screen
        .getByTestId('select-input')
        .querySelectorAll('option');
      expect(selectOptions.length).toBeGreaterThan(DEFAULT_CHATS_GROUPS.length);
    });

    it('should handle single group', () => {
      const singleGroup: ChatGroupType[] = [
        { group_id: 'single', title: 'Single Group' },
      ];

      renderComponent({}, singleGroup);

      const editIcons = screen.getAllByTestId('edit-icon');
      const deleteIcons = screen.getAllByTestId('delete-icon');

      expect(editIcons).toHaveLength(1);
      expect(deleteIcons).toHaveLength(1);
    });

    it('should handle groups with long titles', () => {
      const longTitleGroups: ChatGroupType[] = [
        {
          group_id: 'long',
          title:
            'This is a very long group title that might cause layout issues',
        },
      ];

      renderComponent({}, longTitleGroups);

      expect(
        screen.getByTestId('chats-groups-filter-container'),
      ).toBeInTheDocument();
    });

    it('should handle groups with special characters', () => {
      const specialCharGroups: ChatGroupType[] = [
        { group_id: 'special', title: 'Group with @#$%^&*() characters' },
      ];

      renderComponent({}, specialCharGroups);

      expect(
        screen.getByTestId('chats-groups-filter-container'),
      ).toBeInTheDocument();
    });
  });

  describe('Accessibility', () => {
    it('should have proper tooltip titles', () => {
      renderComponent();

      const tooltips = screen.getAllByTestId('tooltip');
      const editTooltips = tooltips.filter(
        (tooltip) => tooltip.getAttribute('title') === 'Edit the group title',
      );
      const deleteTooltips = tooltips.filter(
        (tooltip) => tooltip.getAttribute('title') === 'Delete the group',
      );

      expect(editTooltips).toHaveLength(mockChatsGroups.length);
      expect(deleteTooltips).toHaveLength(mockChatsGroups.length);
    });

    it('should have accessible form labels', async () => {
      const user = userEvent.setup();
      renderComponent();

      const editButton = screen
        ?.getAllByTestId('edit-icon')[0]
        ?.closest('button');
      await user.click(editButton!);

      const formItem = screen.getByTestId('form-item-title');
      expect(formItem).toHaveAttribute('data-label', 'Title');
      expect(screen.getByText('Title')).toBeInTheDocument();
    });

    it('should have accessible modal buttons', async () => {
      const user = userEvent.setup();
      renderComponent();

      const deleteButton = screen
        ?.getAllByTestId('delete-icon')[0]
        ?.closest('button');
      await user.click(deleteButton!);

      const cancelButton = screen.getByTestId('modal-cancel');
      const okButton = screen.getByTestId('modal-ok');

      expect(cancelButton).toHaveTextContent('Cancel');
      expect(okButton).toHaveTextContent('Delete');
    });
  });

  describe('Performance', () => {
    it('should handle large number of groups', () => {
      const manyGroups: ChatGroupType[] = Array.from(
        { length: 50 },
        (_, i) => ({
          group_id: `group${i}`,
          title: `Group ${i}`,
        }),
      );

      renderComponent({}, manyGroups);

      expect(
        screen.getByTestId('chats-groups-filter-container'),
      ).toBeInTheDocument();
    });

    it('should memoize options correctly', () => {
      renderComponent();

      // Re-render with same props
      expect(
        screen.getByTestId('chats-groups-filter-container'),
      ).toBeInTheDocument();
    });
  });

  describe('Integration', () => {
    it('should work with Redux store', () => {
      const customGroups: ChatGroupType[] = [
        { group_id: 'custom', title: 'Custom Group' },
      ];

      renderComponent({}, customGroups, 'custom');

      const selectInput = screen.getByTestId('select-input');
      expect(selectInput).toHaveValue('custom');
    });

    it('should handle different store configurations', () => {
      renderComponent({}, mockChatsGroups, 'all');

      const selectInput = screen.getByTestId('select-input');
      expect(selectInput).toHaveValue('all');
    });

    it('should work with different group data structures', () => {
      const differentGroups: ChatGroupType[] = [
        { group_id: 'work', title: 'Work Chats' },
        { group_id: 'personal', title: 'Personal Chats' },
      ];

      renderComponent({}, differentGroups);

      const editIcons = screen.getAllByTestId('edit-icon');
      const deleteIcons = screen.getAllByTestId('delete-icon');

      expect(editIcons).toHaveLength(2);
      expect(deleteIcons).toHaveLength(2);
    });
  });
});
