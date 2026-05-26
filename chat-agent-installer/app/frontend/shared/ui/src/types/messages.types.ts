import { GetProp } from 'antd';
import { Bubble } from '@ant-design/x';
import { RefObject } from 'react';
import { TextAreaRef } from 'antd/es/input/TextArea';

import { RoleEnum } from '@shared/ui/enums/chats.enums';
import { AttachmentType } from '@shared/ui/types/attachments.types';
import { MessageTypeEnum } from '@shared/ui/enums/message.enum';

export type MessageContentType = {
  type: MessageTypeEnum;
  reasoning?: string;
  text?: string;
};

export type OriginalMessageType = {
  message_id: string;
  content: {
    [key: number]: MessageContentType;
  };
  role: RoleEnum;
  message_config?: {
    temperature: null | number;
    reasoning: null | string;
  };
  version_count: number;
  version_index: number;
  created_at?: string;
  attachments: AttachmentType[];
};

export type RawMessageType = {
  [message_id: string]: Omit<OriginalMessageType, 'message_id'> & {
    edit?: boolean;
    loading?: boolean;
  };
};

export type MessageType = {
  message_id: string;
  content: string;
  role: RoleEnum;
  version_count: number;
  version_index: number;
  created_at?: string;
  attachments: AttachmentType[];
  edit?: boolean;
};

export type MessageVersionsType = {
  version: Pick<MessageType, 'version_index' | 'content' | 'created_at'>[];
};

export type MessageVersionsInfoType = {
  active_message: RawMessageType;
  branched_history: RawMessageType[];
};

export type MessageListType = GetProp<typeof Bubble.List, 'items'>[0] & {
  edit?: boolean;
  readyOnlyChat?: boolean;
  version_count: number;
  version_index: number;
};

export type ChangeVersionType = (value: {
  message_id: string;
  version_index: number;
}) => void;

export type UpdateMessageByIdType = (message_id: string) => void;

export type TransformMessagesType = {
  messages: RawMessageType;
  onChangeVersion: ChangeVersionType;
  onToggleEdit: UpdateMessageByIdType;
  refInput: RefObject<TextAreaRef | null>;
  onSaveEdit: UpdateMessageByIdType;
  onCancelEdit: UpdateMessageByIdType;
  readyOnlyChat: boolean;
  statusMessage?: string;
};

export type RenderUserMessagesResultType = MessageListType &
  Pick<
    TransformMessagesType,
    | 'refInput'
    | 'onChangeVersion'
    | 'onToggleEdit'
    | 'onSaveEdit'
    | 'onCancelEdit'
  > & {
    showEditBtn: boolean;
    content: RawMessageType[string]['content'];
  };
