import { RawMessageType } from '@shared/ui/types/messages.types';
import { ChatStatusEnum } from '@shared/ui/enums/chats.enums';
import { AttachmentType } from '@shared/ui/types/attachments.types';

export type ChatType = {
  chat_id: string;
  title: string;
  created_at: string;
  owner_id: string;
  last_message_at: string;
  vault_mode: boolean;
  messages: RawMessageType;
  active: boolean;
  favorite: boolean;
  status: ChatStatusEnum;
  status_msg: null | string;
  group_id: string | null;
};

export type ChatUsageType = {
  input_token: number;
  output_token: number;
  cost: number;
};

export type ChatRequestProps = {
  content: string;
  message_id?: string;
  attachments?: AttachmentType[];
  selectedKey?: string[];
};
