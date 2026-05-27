import { UpdateMessageByIdType } from '@shared/ui/types/messages.types';

export interface EditUserMessageFooterProps {
  message_id: string;
  onCancel: UpdateMessageByIdType;
  onSave: UpdateMessageByIdType;
}
