import { HTMLProps } from 'react';

export interface CustomSidebarChatsProps extends HTMLProps<HTMLDivElement> {
  onLoadMore: (value?: boolean) => void;
}
