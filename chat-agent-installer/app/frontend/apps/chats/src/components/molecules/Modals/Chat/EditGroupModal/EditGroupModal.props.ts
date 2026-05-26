import { ModalProps } from 'antd';
import { EditGroupType } from '@/types/common.types';

export interface EditGroupModalProps extends ModalProps {
  group: EditGroupType | null;
  setGroup: (value: EditGroupType | null) => void;
}
