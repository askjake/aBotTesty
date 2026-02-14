import { GetProp, ModalProps } from 'antd';
import type { ConversationsProps } from '@ant-design/x';
import { ReactNode } from 'react';

export interface SearchModalProps extends ModalProps {
  onSearchChange: (value: string) => void;
  items: GetProp<ConversationsProps, 'items'>;
  onLoadMore: (value?: boolean) => void;
  customSearchPlaceholder?: string;
  customItemIcon?: ReactNode;
  hasMoreData: boolean;
  activeKey?: string;
  onActiveKeyChange?: (key: string) => void;
  menuConfig?: ConversationsProps['menu'];
}
