import { ChatType } from '@shared/ui/types/chats.types';

export type AddChatToGroupType = Pick<ChatType, 'chat_id' | 'group_id'>;

export type EditGroupType = Pick<ChatType, 'title' | 'group_id'>;
