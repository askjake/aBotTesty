import { FC, useMemo, useRef, useState } from 'react';
import {
  App,
  Button,
  Divider,
  Flex,
  Input,
  InputRef,
  Space,
  Tooltip,
} from 'antd';
import { DeleteOutlined, EditOutlined, PlusOutlined } from '@ant-design/icons';
import dynamic from 'next/dynamic';

import { useAppDispatch, useAppSelector } from '@shared/ui/store';
import { MAX_CHATS_GROUPS } from '@shared/ui/constants/validation.constants';
import useHandleError from '@shared/ui/hooks/useHandleError.hook';
import { createChatGroup } from '@/services/chatGroup.service';
import { DEFAULT_CHATS_GROUPS } from '@/constants/chats.constants';
import {
  setActiveChatGroup,
  setChatsGroups,
} from '@shared/ui/store/chatsGroups/chatsGroups.slice';

import {
  StyledChatsGroupsFilterContainer,
  StyledChatsGroupsFilterSelect,
} from '@/components/molecules/ChatsGroupsFilter/ChatsGroupsFilter.styled';
const DeleteGroupModal = dynamic(
  () => import('@/components/molecules/Modals/Chat/DeleteGroupModal'),
  {
    ssr: false,
  },
);
const EditGroupModal = dynamic(
  () => import('@/components/molecules/Modals/Chat/EditGroupModal'),
  {
    ssr: false,
  },
);

import { ChatsGroupsFilterProps } from '@/components/molecules/ChatsGroupsFilter/ChatsGroupsFilter.props';
import { EditGroupType } from '@/types/common.types';

const ChatsGroupFilter: FC<ChatsGroupsFilterProps> = (props) => {
  const dispatch = useAppDispatch();
  const { message } = App.useApp();
  const inputRef = useRef<InputRef>(null);
  const chatsGroups = useAppSelector((store) => store.chatsGroups.chatsGroups);
  const activeChatGroup = useAppSelector(
    (store) => store.chatsGroups.activeChatGroup,
  );
  const handleError = useHandleError();
  const [groupName, setGroupName] = useState('');
  const [isLoadingCreate, setIsLoadingCreate] = useState(false);
  const [editGroup, setEditGroup] = useState<EditGroupType | null>(null);
  const [deleteId, setDeleteId] = useState<string | null>(null);

  const chatsGroupsOptions = useMemo(
    () => [
      ...DEFAULT_CHATS_GROUPS.map(({ group_id, title }) => ({
        label: title,
        originalLabel: title,
        value: group_id,
      })),
      ...chatsGroups.map(({ group_id, title }) => ({
        originalLabel: title,
        label: (
          <Flex align='center' justify='space-between' gap={1}>
            <span>{title}</span>
            <Flex align='center' justify='flex-end' gap={0.5}>
              <Tooltip title='Edit the group title'>
                <Button
                  onClick={() =>
                    handleOpenEdit({ group_id: group_id as string, title })
                  }
                  size='small'
                  type='text'
                  icon={<EditOutlined />}
                />
              </Tooltip>
              <Tooltip title='Delete the group'>
                <Button
                  onClick={() => handleOpenDelete(group_id as string)}
                  color='danger'
                  size='small'
                  variant='text'
                  type='text'
                  icon={<DeleteOutlined />}
                />
              </Tooltip>
            </Flex>
          </Flex>
        ),
        value: group_id,
      })),
    ],
    [chatsGroups],
  );

  const isReachedMaxLimit = useMemo(
    () => chatsGroups.length === MAX_CHATS_GROUPS,
    [chatsGroups],
  );

  const isDisabledAddGroup = useMemo(
    () => isReachedMaxLimit || !groupName.length,
    [isReachedMaxLimit, groupName],
  );

  const handleAddGroup = async () => {
    try {
      setIsLoadingCreate(true);
      const newGroup = await createChatGroup({
        title: groupName,
      });
      dispatch(setChatsGroups([newGroup, ...chatsGroups]));
      message.success(`The group "${groupName}" has successfully added`);
    } catch (e) {
      handleError(e);
    } finally {
      setGroupName('');
      setIsLoadingCreate(false);
    }
  };

  const handleOpenEdit = ({
    group_id,
    title,
  }: {
    group_id: string;
    title: string;
  }) => {
    setEditGroup({
      group_id,
      title,
    });
  };

  const handleOpenDelete = (id: string) => {
    setDeleteId(id);
  };

  return (
    <StyledChatsGroupsFilterContainer {...props}>
      <StyledChatsGroupsFilterSelect
        value={activeChatGroup}
        showSearch={{
          optionFilterProp: 'originalLabel',
        }}
        placeholder='Search by group name'
        onChange={(value) => dispatch(setActiveChatGroup(value as string))}
        popupRender={(menu) => (
          <>
            {menu}
            <Divider style={{ margin: '8px 0' }} />
            <Space style={{ padding: '0 8px 4px' }}>
              <Input
                placeholder='Enter a group name'
                showCount
                ref={inputRef}
                value={groupName}
                onChange={(e) => setGroupName(e.target.value)}
                onKeyDown={(e) => e.stopPropagation()}
                disabled={isReachedMaxLimit}
                maxLength={80}
              />
              <Button
                disabled={isDisabledAddGroup}
                type='text'
                icon={<PlusOutlined />}
                onClick={handleAddGroup}
                loading={isLoadingCreate}
              />
            </Space>
          </>
        )}
        options={chatsGroupsOptions}
      />
      <DeleteGroupModal setDeleteId={setDeleteId} deleteId={deleteId} />
      <EditGroupModal group={editGroup} setGroup={setEditGroup} />
    </StyledChatsGroupsFilterContainer>
  );
};

export default ChatsGroupFilter;
