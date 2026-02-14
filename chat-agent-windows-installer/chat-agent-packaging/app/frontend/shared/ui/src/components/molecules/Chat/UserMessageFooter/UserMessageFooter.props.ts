import {
  ChangeVersionType,
  UpdateMessageByIdType,
} from '@shared/ui/types/messages.types';

export interface UserMessageFooterProps {
  version_count: number;
  version_index: number;
  message_id: string;
  onChangeVersion: ChangeVersionType;
  onToggleEdit: UpdateMessageByIdType;
  showEditBtn: boolean;
}
