import { ModalProps } from 'antd';

export interface DeleteChatModalProps extends ModalProps {
  deleteId: string | null;
  setDeleteId: (value: string | null) => void;
  onCloseCb: () => void;
}
