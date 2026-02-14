import { SenderProps } from '@ant-design/x';
import { ChatRequestProps, ChatType } from '@shared/ui/types/chats.types';

export interface ChatSenderProps extends SenderProps {
  onRequest: ({ content, message_id }: ChatRequestProps) => void;
  activeChat: ChatType | null;
}
