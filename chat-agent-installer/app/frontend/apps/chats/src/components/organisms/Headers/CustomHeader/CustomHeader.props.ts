import { HTMLProps } from 'react';

export interface CustomHeaderProps extends HTMLProps<HTMLDivElement> {
  showChats?: boolean;
}
