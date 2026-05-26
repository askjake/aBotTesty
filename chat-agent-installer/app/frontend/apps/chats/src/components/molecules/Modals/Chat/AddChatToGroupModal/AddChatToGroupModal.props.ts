import { ModalProps } from 'antd';
import { AddChatToGroupType } from '@/types/common.types';

export interface AddChatToGroupModalProps extends ModalProps {
  chat: AddChatToGroupType | null;
  setChat: (value: AddChatToGroupType | null) => void;
  onCloseCb: () => void;
}
