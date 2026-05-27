import { RefObject } from 'react';
import { BubbleListProps } from '@ant-design/x';

export type MessagesBlockRef = {
  scrollBottom: () => void;
};

export interface MessagesBlockProps extends Omit<BubbleListProps, 'role'> {
  onLoadMore: (value?: boolean) => Promise<void>;
  customHeight?: string;
  isLoading: boolean;
  componentRef: RefObject<MessagesBlockRef | null>;
}
