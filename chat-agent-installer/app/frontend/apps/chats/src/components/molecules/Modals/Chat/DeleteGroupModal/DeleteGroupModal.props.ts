import { ModalProps } from 'antd';

export interface DeleteGroupModalProps extends ModalProps {
  deleteId: string | null;
  setDeleteId: (value: string | null) => void;
}
